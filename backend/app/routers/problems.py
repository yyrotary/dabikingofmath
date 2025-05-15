# 문제 라우터
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
import logging

from app.models import Problem, APIResponse
from app.database.database import get_db
from app.routers.auth import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{problem_id}", response_model=APIResponse)
async def get_problem(
    problem_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """특정 문제 조회"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="문제를 찾을 수 없습니다."
                )
            
            problem = Problem.from_db_row(row)
            
            return APIResponse(
                success=True,
                message="문제 조회 성공",
                data=problem
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문제 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문제 조회 중 오류가 발생했습니다."
        )

@router.get("/by-topic/{topic}", response_model=APIResponse)
async def get_problems_by_topic(
    topic: str,
    user_id: int = Depends(get_current_user_id),
    difficulty_min: int = Query(1, ge=1, le=10),
    difficulty_max: int = Query(10, ge=1, le=10),
    limit: int = Query(10, ge=1, le=50)
):
    """주제별 문제 조회"""
    try:
        if difficulty_min > difficulty_max:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="최소 난이도가 최대 난이도보다 클 수 없습니다."
            )
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM problems
                WHERE topic = ? 
                AND difficulty_level BETWEEN ? AND ?
                ORDER BY difficulty_level, id
                LIMIT ?
            """, (topic, difficulty_min, difficulty_max, limit))
            
            rows = cursor.fetchall()
            problems = [Problem.from_db_row(row) for row in rows]
            
            return APIResponse(
                success=True,
                message=f"{topic} 주제 문제 조회 성공",
                data={
                    "problems": problems,
                    "count": len(problems),
                    "topic": topic,
                    "difficulty_range": [difficulty_min, difficulty_max]
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주제별 문제 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문제 조회 중 오류가 발생했습니다."
        )

@router.get("/by-mission/{mission_id}", response_model=APIResponse)
async def get_problems_by_mission(
    mission_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """미션별 문제 목록 조회"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 미션 소유자 확인
            cursor.execute("SELECT user_id FROM missions WHERE id = ?", (mission_id,))
            mission_row = cursor.fetchone()
            
            if not mission_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="미션을 찾을 수 없습니다."
                )
            
            if mission_row['user_id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="접근 권한이 없습니다."
                )
            
            # 미션의 문제들 조회
            cursor.execute("""
                SELECT p.*, mp.sequence_order, mp.is_completed
                FROM problems p
                JOIN mission_problems mp ON p.id = mp.problem_id
                WHERE mp.mission_id = ?
                ORDER BY mp.sequence_order
            """, (mission_id,))
            
            rows = cursor.fetchall()
            problems_with_status = []
            
            for row in rows:
                problem = Problem.from_db_row(row)
                problems_with_status.append({
                    "problem": problem,
                    "sequence_order": row['sequence_order'],
                    "is_completed": bool(row['is_completed'])
                })
            
            return APIResponse(
                success=True,
                message="미션 문제 목록 조회 성공",
                data={
                    "mission_id": mission_id,
                    "problems": problems_with_status,
                    "total_count": len(problems_with_status)
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"미션별 문제 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문제 조회 중 오류가 발생했습니다."
        )

@router.get("/", response_model=APIResponse)
async def get_problems(
    user_id: int = Depends(get_current_user_id),
    topic: Optional[str] = Query(None),
    difficulty_min: int = Query(1, ge=1, le=10),
    difficulty_max: int = Query(10, ge=1, le=10),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """문제 목록 조회 (필터링 및 페이징 지원)"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 쿼리 조건 구성
            where_conditions = []
            params = []
            
            # 주제 필터
            if topic:
                where_conditions.append("topic = ?")
                params.append(topic)
            
            # 난이도 범위
            where_conditions.append("difficulty_level BETWEEN ? AND ?")
            params.extend([difficulty_min, difficulty_max])
            
            # 검색어 필터
            if search:
                where_conditions.append("(title LIKE ? OR content LIKE ?)")
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern])
            
            # WHERE 절 구성
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # 총 개수 조회
            count_query = f"SELECT COUNT(*) FROM problems {where_clause}"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # 문제 목록 조회
            query = f"""
                SELECT * FROM problems {where_clause}
                ORDER BY topic, difficulty_level, id
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            problems = [Problem.from_db_row(row) for row in rows]
            
            return APIResponse(
                success=True,
                message="문제 목록 조회 성공",
                data={
                    "problems": problems,
                    "pagination": {
                        "total_count": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_next": (offset + limit) < total_count
                    },
                    "filters": {
                        "topic": topic,
                        "difficulty_range": [difficulty_min, difficulty_max],
                        "search": search
                    }
                }
            )
            
    except Exception as e:
        logger.error(f"문제 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문제 목록 조회 중 오류가 발생했습니다."
        )

@router.get("/topics/list", response_model=APIResponse)
async def get_problem_topics(user_id: int = Depends(get_current_user_id)):
    """문제 주제 목록 조회"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT topic, COUNT(*) as problem_count
                FROM problems
                GROUP BY topic
                ORDER BY topic
            """)
            
            rows = cursor.fetchall()
            topics = [
                {
                    "topic": row['topic'],
                    "problem_count": row['problem_count']
                }
                for row in rows
            ]
            
            return APIResponse(
                success=True,
                message="주제 목록 조회 성공",
                data=topics
            )
            
    except Exception as e:
        logger.error(f"주제 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주제 목록 조회 중 오류가 발생했습니다."
        )

@router.get("/statistics/overview", response_model=APIResponse)
async def get_problem_statistics(user_id: int = Depends(get_current_user_id)):
    """문제 통계 개요"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 전체 통계
            cursor.execute("SELECT COUNT(*) as total FROM problems")
            total_count = cursor.fetchone()['total']
            
            # 주제별 통계
            cursor.execute("""
                SELECT topic, COUNT(*) as count
                FROM problems
                GROUP BY topic
                ORDER BY count DESC
            """)
            topic_stats = [
                {"topic": row['topic'], "count": row['count']}
                for row in cursor.fetchall()
            ]
            
            # 난이도별 통계
            cursor.execute("""
                SELECT difficulty_level, COUNT(*) as count
                FROM problems
                GROUP BY difficulty_level
                ORDER BY difficulty_level
            """)
            difficulty_stats = [
                {"level": row['difficulty_level'], "count": row['count']}
                for row in cursor.fetchall()
            ]
            
            return APIResponse(
                success=True,
                message="문제 통계 조회 성공",
                data={
                    "total_problems": total_count,
                    "by_topic": topic_stats,
                    "by_difficulty": difficulty_stats
                }
            )
            
    except Exception as e:
        logger.error(f"문제 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문제 통계 조회 중 오류가 발생했습니다."
        )