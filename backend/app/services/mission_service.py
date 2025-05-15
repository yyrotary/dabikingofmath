# 미션 서비스
import json
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import logging

from app.database.database import get_db
from app.models import Mission, Problem, MissionCreate, MissionStatus, MissionType
from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class MissionService:
    """미션 관리 서비스"""
    
    def __init__(self):
        self.min_problems = 3
        self.max_problems = 10
        self.default_problems = 5
    
    def create_daily_mission(self, user_id: int, mission_type: MissionType = MissionType.DAILY) -> Mission:
        """일일 미션 생성"""
        logger.info(f"사용자 {user_id}의 일일 미션 생성 시작")
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 오늘 이미 생성된 미션이 있는지 확인
            today = datetime.now().date()
            cursor.execute("""
                SELECT id FROM missions
                WHERE user_id = ? AND DATE(created_at) = ? AND status != 'completed'
            """, (user_id, today))
            
            existing_mission = cursor.fetchone()
            if existing_mission:
                return self.get_mission_by_id(existing_mission['id'])
            
            # 사용자의 학습 레벨 분석
            difficulty_range = self._calculate_user_difficulty_range(user_id)
            
            # 문제 선별
            selected_problems = self.select_problems_for_mission(
                user_id=user_id,
                difficulty_range=difficulty_range,
                count=self.default_problems,
                topics=['등차수열', '등비수열', '수열의합', '수학적귀납법']
            )
            
            if not selected_problems:
                raise ValueError("미션에 포함할 문제를 찾을 수 없습니다")
            
            # 미션 생성
            mission_name = self._generate_mission_name(mission_type, difficulty_range)
            
            cursor.execute("""
                INSERT INTO missions (
                    user_id, name, description, total_problems, target_score
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                mission_name,
                f"{len(selected_problems)}개의 {mission_type.value} 문제",
                len(selected_problems),
                self._calculate_target_score(difficulty_range)
            ))
            
            mission_id = cursor.lastrowid
            
            # 미션-문제 연결
            for i, problem in enumerate(selected_problems):
                cursor.execute("""
                    INSERT INTO mission_problems (
                        mission_id, problem_id, sequence_order
                    ) VALUES (?, ?, ?)
                """, (mission_id, problem.id, i + 1))
            
            conn.commit()
            logger.info(f"미션 생성 완료: ID {mission_id}")
            
            return self.get_mission_by_id(mission_id)
    
    def select_problems_for_mission(self,
                                  user_id: int,
                                  difficulty_range: Tuple[int, int],
                                  count: int = 5,
                                  topics: Optional[List[str]] = None) -> List[Problem]:
        """미션용 문제 선별"""
        logger.info(f"문제 선별 시작: 난이도 {difficulty_range}, 개수 {count}")
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 최근 풀었던 문제들 조회 (중복 방지)
            cursor.execute("""
                SELECT DISTINCT problem_id FROM answers 
                WHERE user_id = ? AND submitted_at > datetime('now', '-7 days')
            """, (user_id,))
            recent_problem_ids = [row['problem_id'] for row in cursor.fetchall()]
            
            # 문제 조회 쿼리 구성
            where_conditions = []
            params = []
            
            # 난이도 범위
            where_conditions.append("difficulty_level BETWEEN ? AND ?")
            params.extend([difficulty_range[0], difficulty_range[1]])
            
            # 주제 필터
            if topics:
                topic_placeholders = ','.join(['?' for _ in topics])
                where_conditions.append(f"topic IN ({topic_placeholders})")
                params.extend(topics)
            
            # 최근 풀지 않은 문제들
            if recent_problem_ids:
                problem_placeholders = ','.join(['?' for _ in recent_problem_ids])
                where_conditions.append(f"id NOT IN ({problem_placeholders})")
                params.extend(recent_problem_ids)
            
            # 쿼리 실행
            query = f"""
                SELECT * FROM problems
                WHERE {' AND '.join(where_conditions)}
                ORDER BY RANDOM()
                LIMIT ?
            """
            params.append(count * 2)  # 여유있게 조회 후 선별
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Problem 객체 변환
            problems = [Problem.from_db_row(row) for row in rows]
            
            # 적응형 알고리즘 적용하여 최종 선별
            selected_problems = self._apply_adaptive_selection(user_id, problems, count)
            
            logger.info(f"문제 선별 완료: {len(selected_problems)}개")
            return selected_problems
    
    def get_current_mission(self, user_id: int) -> Optional[Mission]:
        """사용자의 현재 진행 중인 미션 조회"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM missions
                WHERE user_id = ? AND status IN ('pending', 'in_progress')
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            mission = Mission.from_db_row(row)
            
            # 미션의 문제들 로드
            cursor.execute("""
                SELECT p.* FROM problems p
                JOIN mission_problems mp ON p.id = mp.problem_id
                WHERE mp.mission_id = ?
                ORDER BY mp.sequence_order
            """, (mission.id,))
            
            problem_rows = cursor.fetchall()
            mission.problems = [Problem.from_db_row(row) for row in problem_rows]
            
            return mission
    
    def get_mission_by_id(self, mission_id: int) -> Optional[Mission]:
        """미션 ID로 조회"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            mission = Mission.from_db_row(row)
            
            # 미션의 문제들 로드
            cursor.execute("""
                SELECT p.* FROM problems p
                JOIN mission_problems mp ON p.id = mp.problem_id
                WHERE mp.mission_id = ?
                ORDER BY mp.sequence_order
            """, (mission_id,))
            
            problem_rows = cursor.fetchall()
            mission.problems = [Problem.from_db_row(row) for row in problem_rows]
            
            return mission
    
    def start_mission(self, mission_id: int) -> bool:
        """미션 시작"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE missions
                SET status = 'in_progress', start_time = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
            """, (mission_id,))
            
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"미션 시작: ID {mission_id}")
            
            return success
    
    def update_mission_progress(self, mission_id: int, completed_problem_id: int) -> bool:
        """미션 진행 상황 업데이트"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 문제 완료 표시
            cursor.execute("""
                UPDATE mission_problems
                SET is_completed = TRUE, completed_at = CURRENT_TIMESTAMP
                WHERE mission_id = ? AND problem_id = ?
            """, (mission_id, completed_problem_id))
            
            # 미션 진행 상황 업데이트
            cursor.execute("""
                UPDATE missions
                SET completed_problems = (
                    SELECT COUNT(*) FROM mission_problems
                    WHERE mission_id = ? AND is_completed = TRUE
                )
                WHERE id = ?
            """, (mission_id, mission_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def check_mission_completion(self, mission_id: int) -> bool:
        """미션 완료 여부 확인 및 처리"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 미션 정보 조회
            cursor.execute("""
                SELECT total_problems, completed_problems, user_id
                FROM missions WHERE id = ?
            """, (mission_id,))
            
            mission_info = cursor.fetchone()
            if not mission_info:
                return False
            
            # 미션 완료 확인
            if mission_info['completed_problems'] >= mission_info['total_problems']:
                # 실제 점수 계산
                actual_score = self._calculate_mission_score(mission_id)
                
                # 미션 완료 처리
                cursor.execute("""
                    UPDATE missions
                    SET status = 'completed', 
                        end_time = CURRENT_TIMESTAMP,
                        actual_score = ?
                    WHERE id = ?
                """, (actual_score, mission_id))
                
                conn.commit()
                
                # 분석 데이터 기록
                analytics_service.record_mission_completion(
                    mission_info['user_id'],
                    mission_id,
                    actual_score
                )
                
                logger.info(f"미션 완료: ID {mission_id}, 점수 {actual_score}")
                return True
        
        return False
    
    def get_next_problem(self, mission_id: int) -> Optional[Problem]:
        """미션의 다음 문제 조회"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.* FROM problems p
                JOIN mission_problems mp ON p.id = mp.problem_id
                WHERE mp.mission_id = ? AND mp.is_completed = FALSE
                ORDER BY mp.sequence_order
                LIMIT 1
            """, (mission_id,))
            
            row = cursor.fetchone()
            if row:
                return Problem.from_db_row(row)
            return None
    
    def _calculate_user_difficulty_range(self, user_id: int) -> Tuple[int, int]:
        """사용자의 적절한 난이도 범위 계산"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 최근 답안들의 성과 분석
            cursor.execute("""
                SELECT AVG(score) as avg_score, COUNT(*) as problem_count
                FROM answers a
                JOIN problems p ON a.problem_id = p.id
                WHERE a.user_id = ? AND a.submitted_at > datetime('now', '-7 days')
                AND a.score IS NOT NULL
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if not result or result['problem_count'] < 3:
                # 데이터가 부족한 경우 기본 난이도
                return (2, 4)
            
            avg_score = result['avg_score']
            
            # 점수에 따른 난이도 조정
            if avg_score >= 90:
                return (4, 7)
            elif avg_score >= 75:
                return (3, 6)
            elif avg_score >= 60:
                return (2, 5)
            else:
                return (1, 4)
    
    def _apply_adaptive_selection(self, user_id: int, problems: List[Problem], count: int) -> List[Problem]:
        """적응형 알고리즘으로 문제 선별"""
        if len(problems) <= count:
            return problems
        
        # 사용자의 주제별 성과 분석
        topic_performance = self._analyze_topic_performance(user_id)
        
        # 문제에 가중치 부여
        weighted_problems = []
        for problem in problems:
            weight = 1.0
            
            # 약한 주제의 문제일수록 가중치 증가
            if problem.topic in topic_performance:
                performance = topic_performance[problem.topic]
                if performance < 70:  # 70% 미만인 주제
                    weight += (70 - performance) / 100
            
            weighted_problems.append((problem, weight))
        
        # 가중치에 따라 정렬
        weighted_problems.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 문제들 선택하되 다양성 고려
        selected = []
        topic_count = {}
        
        for problem, weight in weighted_problems:
            if len(selected) >= count:
                break
            
            # 같은 주제의 문제가 너무 많지 않도록 제한
            topic_count[problem.topic] = topic_count.get(problem.topic, 0)
            if topic_count[problem.topic] >= 2:
                continue
            
            selected.append(problem)
            topic_count[problem.topic] += 1
        
        # 부족한 경우 랜덤으로 추가
        remaining = [p for p, w in weighted_problems if p not in selected]
        while len(selected) < count and remaining:
            selected.append(remaining.pop(0))
        
        return selected[:count]
    
    def _analyze_topic_performance(self, user_id: int) -> Dict[str, float]:
        """주제별 성과 분석"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.topic, AVG(a.score) as avg_score
                FROM answers a
                JOIN problems p ON a.problem_id = p.id
                WHERE a.user_id = ? AND a.submitted_at > datetime('now', '-14 days')
                AND a.score IS NOT NULL
                GROUP BY p.topic
            """, (user_id,))
            
            return {row['topic']: row['avg_score'] for row in cursor.fetchall()}
    
    def _generate_mission_name(self, mission_type: MissionType, difficulty_range: Tuple[int, int]) -> str:
        """미션 이름 생성"""
        difficulty_names = {
            (1, 3): "기초",
            (2, 4): "기본",
            (3, 5): "표준",
            (4, 6): "심화",
            (5, 7): "고급",
            (6, 10): "최고급"
        }
        
        # 가장 가까운 난이도 범위 찾기
        difficulty_name = "기본"
        for range_key, name in difficulty_names.items():
            if (difficulty_range[0] >= range_key[0] and 
                difficulty_range[1] <= range_key[1]):
                difficulty_name = name
                break
        
        type_names = {
            MissionType.DAILY: "일일 학습",
            MissionType.REVIEW: "복습",
            MissionType.CHALLENGE: "도전",
            MissionType.ASSESSMENT: "평가"
        }
        
        today = datetime.now().strftime("%m월 %d일")
        return f"{today} {type_names[mission_type]} ({difficulty_name})"
    
    def _calculate_target_score(self, difficulty_range: Tuple[int, int]) -> int:
        """난이도에 따른 목표 점수 계산"""
        avg_difficulty = (difficulty_range[0] + difficulty_range[1]) / 2
        
        # 난이도에 반비례하여 목표 점수 설정
        if avg_difficulty <= 3:
            return 85
        elif avg_difficulty <= 5:
            return 80
        elif avg_difficulty <= 7:
            return 75
        else:
            return 70
    
    def _calculate_mission_score(self, mission_id: int) -> int:
        """미션의 실제 점수 계산"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(score) as avg_score
                FROM answers a
                JOIN mission_problems mp ON a.problem_id = mp.problem_id
                WHERE mp.mission_id = ? AND a.score IS NOT NULL
            """, (mission_id,))
            
            result = cursor.fetchone()
            return int(result['avg_score']) if result['avg_score'] else 0

# 싱글톤 미션 서비스 인스턴스
mission_service = MissionService()