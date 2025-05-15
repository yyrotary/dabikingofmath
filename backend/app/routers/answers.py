# 답안 라우터
import json
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status, File, UploadFile, Form
import logging
from datetime import datetime

from app.models import Answer, APIResponse, AnswerSubmission, AnswerResult
from app.database.database import get_db
from app.routers.auth import get_current_user_id
from app.services.ai_service import ai_service
from app.services.mission_service import mission_service
from app.utils.image_utils import save_uploaded_images, validate_uploaded_file

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/submit", response_model=APIResponse)
async def submit_answer(
    mission_id: int = Form(...),
    problem_id: int = Form(...),
    time_spent: int = Form(None),
    images: List[UploadFile] = File(...),
    user_id: int = Depends(get_current_user_id)
):
    """답안 제출"""
    try:
        logger.info(f"답안 제출 시작: 미션 {mission_id}, 문제 {problem_id}")
        
        # 이미지 파일 검증
        if not images or len(images) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="답안 이미지가 필요합니다."
            )
        
        if len(images) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="최대 5개의 이미지만 업로드할 수 있습니다."
            )
        
        # 각 이미지 파일 검증
        for image in images:
            is_valid, message = validate_uploaded_file(image)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"이미지 검증 실패: {message}"
                )
        
        # 미션 소유자 확인
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM missions WHERE id = ?",
                (mission_id,)
            )
            mission_row = cursor.fetchone()
            
            if not mission_row or mission_row['user_id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="미션을 찾을 수 없습니다."
                )
        
        # 이미지 저장
        saved_image_paths = save_uploaded_images(images)
        if not saved_image_paths:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이미지 저장에 실패했습니다."
            )
        
        # 답안 데이터베이스 저장
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO answers (
                    user_id, mission_id, problem_id, answer_images, time_spent
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                mission_id,
                problem_id,
                json.dumps(saved_image_paths),
                time_spent
            ))
            
            answer_id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"답안 저장 완료: ID {answer_id}")
        
        return APIResponse(
            success=True,
            message="답안이 제출되었습니다. AI 채점을 진행합니다.",
            data={
                "answer_id": answer_id,
                "status": "processing",
                "image_count": len(saved_image_paths)
            }
        )
        
        # 백그라운드에서 AI 채점 수행 (실제로는 Celery 등 사용 권장)
        # 여기서는 동기 처리로 구현
        # asyncio.create_task(process_answer_async(answer_id))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"답안 제출 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="답안 제출 중 오류가 발생했습니다."
        )

@router.post("/{answer_id}/process", response_model=APIResponse)
async def process_answer(
    answer_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """답안 AI 처리 시작 (수동 실행)"""
    try:
        # 답안 소유자 확인
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, mission_id, problem_id, answer_images FROM answers WHERE id = ?",
                (answer_id,)
            )
            answer_row = cursor.fetchone()
            
            if not answer_row or answer_row['user_id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="답안을 찾을 수 없습니다."
                )
        
        # AI 처리 실행
        result = await process_answer_with_ai(answer_id)
        
        return APIResponse(
            success=True,
            message="AI 채점이 완료되었습니다.",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"답안 처리 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="답안 처리 중 오류가 발생했습니다."
        )

@router.get("/{answer_id}/result", response_model=APIResponse)
async def get_answer_result(
    answer_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """답안 결과 조회"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, p.title, p.topic
                FROM answers a
                JOIN problems p ON a.problem_id = p.id
                WHERE a.id = ? AND a.user_id = ?
            """, (answer_id, user_id))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="답안을 찾을 수 없습니다."
                )
            
            answer = Answer.from_db_row(row)
            
            # 채점 완료 여부 확인
            if answer.score is None:
                return APIResponse(
                    success=True,
                    message="아직 채점이 완료되지 않았습니다.",
                    data={
                        "answer_id": answer_id,
                        "status": "processing",
                        "answer": answer
                    }
                )
            
            # 결과 데이터 구성
            result_data = AnswerResult(
                answer_id=answer.id,
                score=answer.score,
                feedback=answer.ai_feedback or "",
                concepts_learned=answer.key_concepts_identified,
                areas_for_improvement=answer.mistakes_detected,
                next_recommendations=[]  # 추후 구현
            )
            
            return APIResponse(
                success=True,
                message="답안 결과 조회 성공",
                data={
                    "result": result_data,
                    "answer": answer,
                    "problem_info": {
                        "title": row['title'],
                        "topic": row['topic']
                    }
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"답안 결과 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="답안 결과 조회 중 오류가 발생했습니다."
        )

@router.post("/{answer_id}/images", response_model=APIResponse)
async def add_answer_images(
    answer_id: int,
    images: List[UploadFile] = File(...),
    user_id: int = Depends(get_current_user_id)
):
    """답안에 추가 이미지 업로드"""
    try:
        # 답안 소유자 확인
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, answer_images FROM answers WHERE id = ?",
                (answer_id,)
            )
            answer_row = cursor.fetchone()
            
            if not answer_row or answer_row['user_id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="답안을 찾을 수 없습니다."
                )
        
        # 기존 이미지 개수 확인
        existing_images = json.loads(answer_row['answer_images'] or '[]')
        total_images = len(existing_images) + len(images)
        
        if total_images > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"총 이미지 개수가 5개를 초과할 수 없습니다. (현재: {len(existing_images)}개)"
            )
        
        # 이미지 검증 및 저장
        for image in images:
            is_valid, message = validate_uploaded_file(image)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"이미지 검증 실패: {message}"
                )
        
        saved_paths = save_uploaded_images(images)
        all_images = existing_images + saved_paths
        
        # 데이터베이스 업데이트
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE answers
                SET answer_images = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(all_images), answer_id))
            conn.commit()
        
        return APIResponse(
            success=True,
            message=f"{len(saved_paths)}개의 이미지가 추가되었습니다.",
            data={
                "answer_id": answer_id,
                "total_images": len(all_images),
                "added_images": len(saved_paths)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 추가 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 추가 중 오류가 발생했습니다."
        )

# Helper function for AI processing
async def process_answer_with_ai(answer_id: int) -> dict:
    """답안을 AI로 처리하는 함수"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 답안 및 문제 정보 조회
            cursor.execute("""
                SELECT a.*, p.title, p.content, p.solution, p.topic, p.difficulty_level
                FROM answers a
                JOIN problems p ON a.problem_id = p.id
                WHERE a.id = ?
            """, (answer_id,))
            
            row = cursor.fetchone()
            if not row:
                raise ValueError("답안을 찾을 수 없습니다.")
            
            answer = Answer.from_db_row(row)
            problem_data = {
                'id': row['problem_id'],
                'title': row['title'],
                'content': row['content'],
                'solution': row['solution'],
                'topic': row['topic'],
                'difficulty_level': row['difficulty_level']
            }
            
            # 1. 이미지에서 텍스트 추출
            logger.info(f"이미지 텍스트 추출 시작: {len(answer.answer_images)}개")
            extracted_text = await ai_service.extract_text_from_images(answer.answer_images)
            
            # 2. 답안 채점
            logger.info("답안 채점 시작")
            score_result = await ai_service.score_answer(
                Problem(**problem_data),
                extracted_text
            )
            
            # 3. 개인화된 피드백 생성
            logger.info("피드백 생성 시작")
            feedback = await ai_service.generate_feedback(
                score_result,
                Problem(**problem_data)
            )
            
            # 4. 결과 저장
            cursor.execute("""
                UPDATE answers
                SET extracted_text = ?,
                    extracted_markdown = ?,
                    score = ?,
                    ai_feedback = ?,
                    key_concepts_identified = ?,
                    mistakes_detected = ?,
                    scored_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                extracted_text,
                extracted_text,  # 마크다운 버전 (현재는 동일)
                score_result['score'],
                feedback,
                json.dumps(score_result.get('concept_understanding', [])),
                json.dumps(score_result.get('mistakes_detected', [])),
                answer_id
            ))
            conn.commit()
            
            # 5. 미션 진행 상황 업데이트
            mission_service.update_mission_progress(
                answer.mission_id,
                answer.problem_id
            )
            
            # 6. 미션 완료 확인
            mission_service.check_mission_completion(answer.mission_id)
            
            logger.info(f"답안 처리 완료: {answer_id}, 점수: {score_result['score']}")
            
            return {
                "answer_id": answer_id,
                "score": score_result['score'],
                "feedback": feedback,
                "concepts": score_result.get('concept_understanding', []),
                "mistakes": score_result.get('mistakes_detected', [])
            }
            
    except Exception as e:
        logger.error(f"AI 답안 처리 실패: {e}")
        # 실패한 경우에도 기본 점수 저장
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE answers
                SET score = 0,
                    ai_feedback = ?,
                    scored_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (f"처리 중 오류가 발생했습니다: {str(e)}", answer_id))
            conn.commit()
        raise