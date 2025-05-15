# 학습 분석 서비스
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from app.database.database import get_db
from app.models import LearningAnalytics, LearningInsights, PerformanceTrend

logger = logging.getLogger(__name__)

class AnalyticsService:
    """학습 분석 서비스"""
    
    def __init__(self):
        self.performance_metrics = [
            'accuracy',           # 정확도
            'completion_time',    # 완료 시간
            'difficulty_progression',  # 난이도 진행
            'topic_mastery',      # 주제 숙달도
            'consistency',        # 일관성
            'improvement_rate'    # 향상률
        ]
    
    def record_performance(self, user_id: int, mission_id: int, problem_id: int, 
                         score: int, time_spent: int, topic: str):
        """성과 데이터 기록"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # 정확도 기록
                cursor.execute("""
                    INSERT INTO learning_analytics (
                        user_id, mission_id, metric_type, metric_value, topic
                    ) VALUES (?, ?, 'accuracy', ?, ?)
                """, (user_id, mission_id, score, topic))
                
                # 시간 효율성 기록 (점수/시간)
                if time_spent > 0:
                    efficiency = score / (time_spent / 60)  # 분당 점수
                    cursor.execute("""
                        INSERT INTO learning_analytics (
                            user_id, mission_id, metric_type, metric_value, topic
                        ) VALUES (?, ?, 'time_efficiency', ?, ?)
                    """, (user_id, mission_id, efficiency, topic))
                
                conn.commit()
                logger.info(f"성과 데이터 기록 완료: 사용자 {user_id}, 점수 {score}")
                
        except Exception as e:
            logger.error(f"성과 데이터 기록 실패: {e}")
    
    def record_mission_completion(self, user_id: int, mission_id: int, final_score: int):
        """미션 완료 기록"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # 미션 완료율 기록
                cursor.execute("""
                    INSERT INTO learning_analytics (
                        user_id, mission_id, metric_type, metric_value, topic
                    ) VALUES (?, ?, 'mission_completion', ?, 'general')
                """, (user_id, mission_id, 100))
                
                # 미션 평균 점수 기록
                cursor.execute("""
                    INSERT INTO learning_analytics (
                        user_id, mission_id, metric_type, metric_value, topic
                    ) VALUES (?, ?, 'mission_average', ?, 'general')
                """, (user_id, mission_id, final_score))
                
                conn.commit()
                logger.info(f"미션 완료 기록: 사용자 {user_id}, 최종점수 {final_score}")
                
        except Exception as e:
            logger.error(f"미션 완료 기록 실패: {e}")
    
    def calculate_difficulty_adjustment(self, user_id: int, topic: str) -> float:
        """난이도 조정 계산"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # 최근 1주일간의 성과 조회
                cursor.execute("""
                    SELECT AVG(metric_value) as avg_score
                    FROM learning_analytics
                    WHERE user_id = ? AND topic = ? AND metric_type = 'accuracy'
                    AND recorded_at > datetime('now', '-7 days')
                """, (user_id, topic))
                
                result = cursor.fetchone()
                avg_score = result['avg_score'] if result and result['avg_score'] else 70
                
                # 점수에 따른 난이도 조정 계수 계산
                if avg_score >= 90:
                    adjustment = 1.5    # 난이도 상승
                elif avg_score >= 80:
                    adjustment = 1.2    # 약간 상승
                elif avg_score >= 70:
                    adjustment = 1.0    # 유지
                elif avg_score >= 60:
                    adjustment = 0.8    # 약간 하락
                else:
                    adjustment = 0.6    # 난이도 하락
                
                logger.info(f"난이도 조정 계산: {topic}, 평균 {avg_score}점, 조정 {adjustment}")
                return adjustment
                
        except Exception as e:
            logger.error(f"난이도 조정 계산 실패: {e}")
            return 1.0
    
    def generate_learning_insights(self, user_id: int, period_days: int = 7) -> LearningInsights:
        """학습 인사이트 생성"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # 기간 설정
                cutoff_date = datetime.now() - timedelta(days=period_days)
                
                # 총 문제 수 및 평균 점수
                cursor.execute("""
                    SELECT COUNT(*) as total_problems, AVG(metric_value) as avg_score
                    FROM learning_analytics
                    WHERE user_id = ? AND metric_type = 'accuracy'
                    AND recorded_at > ?
                """, (user_id, cutoff_date))
                
                basic_stats = cursor.fetchone()
                total_problems = basic_stats['total_problems'] or 0
                average_score = basic_stats['avg_score'] or 0
                
                # 향상률 계산
                improvement_rate = self._calculate_improvement_rate(user_id, period_days)
                
                # 강점/약점 주제 분석
                strong_topics, weak_topics = self._analyze_topic_performance(user_id, period_days)
                
                # 시간 효율성 분석
                time_efficiency = self._analyze_time_efficiency(user_id, period_days)
                
                # 개선 권장사항 생성
                recommendations = self._generate_recommendations(
                    user_id, average_score, weak_topics, time_efficiency
                )
                
                insights = LearningInsights(
                    user_id=user_id,
                    period_days=period_days,
                    total_problems_solved=total_problems,
                    average_score=round(average_score, 2),
                    improvement_rate=improvement_rate,
                    strong_topics=strong_topics,
                    weak_topics=weak_topics,
                    recommendations=recommendations,
                    time_efficiency=time_efficiency
                )
                
                logger.info(f"학습 인사이트 생성 완료: 사용자 {user_id}")
                return insights
                
        except Exception as e:
            logger.error(f"학습 인사이트 생성 실패: {e}")
            # 기본값 반환
            return LearningInsights(
                user_id=user_id,
                period_days=period_days,
                total_problems_solved=0,
                average_score=0.0,
                improvement_rate=0.0,
                strong_topics=[],
                weak_topics=[],
                recommendations=["더 많은 문제를 풀어보세요."],
                time_efficiency={}
            )
    
    def get_performance_trend(self, user_id: int, period_days: int = 30) -> PerformanceTrend:
        """성과 추세 분석"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # 일별 성과 데이터 조회
                cursor.execute("""
                    SELECT 
                        DATE(recorded_at) as date,
                        AVG(metric_value) as avg_score,
                        topic
                    FROM learning_analytics
                    WHERE user_id = ? AND metric_type = 'accuracy'
                    AND recorded_at > datetime('now', '-{} days')
                    GROUP BY DATE(recorded_at), topic
                    ORDER BY date, topic
                """.format(period_days), (user_id,))
                
                rows = cursor.fetchall()
                
                # 데이터 구성
                dates = []
                scores = []
                topics = []
                
                daily_data = {}
                for row in rows:
                    date = row['date']
                    if date not in daily_data:
                        daily_data[date] = []
                    daily_data[date].append({
                        'score': row['avg_score'],
                        'topic': row['topic']
                    })
                
                # 일별 평균 계산
                for date in sorted(daily_data.keys()):
                    dates.append(date)
                    day_scores = [item['score'] for item in daily_data[date]]
                    scores.append(sum(day_scores) / len(day_scores))
                    topics.append([item['topic'] for item in daily_data[date]])
                
                # 난이도 추세 (임시 데이터)
                difficulty_levels = [5] * len(dates)  # 실제로는 DB에서 조회
                
                return PerformanceTrend(
                    dates=dates,
                    scores=scores,
                    topics=topics,
                    difficulty_levels=difficulty_levels
                )
                
        except Exception as e:
            logger.error(f"성과 추세 분석 실패: {e}")
            return PerformanceTrend(
                dates=[],
                scores=[],
                topics=[],
                difficulty_levels=[]
            )
    
    def _calculate_improvement_rate(self, user_id: int, period_days: int) -> float:
        """향상률 계산"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # 초기와 최근 성과 비교
                cursor.execute("""
                    SELECT 
                        AVG(CASE WHEN recorded_at < datetime('now', '-{} days') 
                            THEN metric_value END) as initial_score,
                        AVG(CASE WHEN recorded_at >= datetime('now', '-3 days') 
                            THEN metric_value END) as recent_score
                    FROM learning_analytics
                    WHERE user_id = ? AND metric_type = 'accuracy'
                    AND recorded_at > datetime('now', '-{} days')
                """.format(period_days // 2, period_days), (user_id,))
                
                result = cursor.fetchone()
                initial_score = result['initial_score'] or 70
                recent_score = result['recent_score'] or 70
                
                if initial_score > 0:
                    improvement_rate = ((recent_score - initial_score) / initial_score) * 100
                    return round(improvement_rate, 2)
                
                return 0.0
                
        except Exception as e:
            logger.error(f"향상률 계산 실패: {e}")
            return 0.0
    
    def _analyze_topic_performance(self, user_id: int, period_days: int) -> Tuple[List[str], List[str]]:
        """주제별 성과 분석 (강점/약점 주제)"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT topic, AVG(metric_value) as avg_score, COUNT(*) as problem_count
                    FROM learning_analytics
                    WHERE user_id = ? AND metric_type = 'accuracy'
                    AND recorded_at > datetime('now', '-{} days')
                    AND topic != 'general'
                    GROUP BY topic
                    HAVING problem_count >= 3
                    ORDER BY avg_score DESC
                """.format(period_days), (user_id,))
                
                rows = cursor.fetchall()
                
                strong_topics = []
                weak_topics = []
                
                for row in rows:
                    topic = row['topic']
                    avg_score = row['avg_score']
                    
                    if avg_score >= 80:
                        strong_topics.append(topic)
                    elif avg_score < 65:
                        weak_topics.append(topic)
                
                return strong_topics[:3], weak_topics[:3]
                
        except Exception as e:
            logger.error(f"주제별 성과 분석 실패: {e}")
            return [], []
    
    def _analyze_time_efficiency(self, user_id: int, period_days: int) -> Dict[str, float]:
        """시간 효율성 분석"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT topic, AVG(metric_value) as avg_efficiency
                    FROM learning_analytics
                    WHERE user_id = ? AND metric_type = 'time_efficiency'
                    AND recorded_at > datetime('now', '-{} days')
                    AND topic != 'general'
                    GROUP BY topic
                """.format(period_days), (user_id,))
                
                rows = cursor.fetchall()
                return {row['topic']: round(row['avg_efficiency'], 2) for row in rows}
                
        except Exception as e:
            logger.error(f"시간 효율성 분석 실패: {e}")
            return {}
    
    def _generate_recommendations(self, user_id: int, avg_score: float, 
                                weak_topics: List[str], time_efficiency: Dict[str, float]) -> List[str]:
        """학습 권장사항 생성"""
        recommendations = []
        
        try:
            # 점수 기반 권장사항
            if avg_score < 60:
                recommendations.append("기초 개념 복습에 더 많은 시간을 투자하세요.")
                recommendations.append("하루 30분씩 꾸준히 학습하는 것이 중요합니다.")
            elif avg_score < 80:
                recommendations.append("현재 수준을 유지하며 응용 문제에 도전해보세요.")
                recommendations.append("약한 주제 영역에 집중적으로 학습하세요.")
            else:
                recommendations.append("어려운 문제에 도전하여 실력을 한 단계 끌어올리세요.")
                recommendations.append("다른 주제와의 융합 문제도 연습해보세요.")
            
            # 약한 주제 기반 권장사항
            if weak_topics:
                topic_names = ', '.join(weak_topics)
                recommendations.append(f"{topic_names} 영역의 기초 개념을 다시 학습하세요.")
            
            # 시간 효율성 기반 권장사항
            if time_efficiency:
                avg_efficiency = sum(time_efficiency.values()) / len(time_efficiency)
                if avg_efficiency < 1.0:
                    recommendations.append("문제 해결 속도를 높이기 위해 공식 암기를 강화하세요.")
                    recommendations.append("시간 제한을 두고 문제를 풀어보세요.")
            
            # 일반적인 권장사항
            if len(recommendations) < 3:
                recommendations.extend([
                    "매일 일정한 시간에 학습하는 습관을 만들어보세요.",
                    "틀린 문제는 반드시 다시 풀어보세요.",
                    "학습한 내용을 정리하고 복습하는 시간을 가지세요."
                ])
            
            return recommendations[:5]  # 최대 5개까지
            
        except Exception as e:
            logger.error(f"권장사항 생성 실패: {e}")
            return ["꾸준한 학습을 계속하세요."]

# 싱글톤 분석 서비스 인스턴스
analytics_service = AnalyticsService()