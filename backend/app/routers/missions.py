# 미션 라우터
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
import logging

from app.models import Mission, MissionCreate, MissionProgress, APIResponse, MissionType
from app.services.mission_service import mission_service
from app.routers.auth import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/current", response_model=APIResponse)
async def get_current_mission(user_id: int = Depends(get_current_user_id)):
    """현재 진행 중인 미션 조회"""
    try:
        mission = mission_service.get_current_mission(user_id)
        
        if not mission:
            return APIResponse(
                success=True,
                message="진행 중인 미션이 없습니다.",
                data=None
            )
        
        # 현재 문제 조회
        current_problem = mission_service.get_next_problem(mission.id)
        
        # 진행률 계산
        progress = MissionProgress.calculate_progress(mission, current_problem)
        
        return APIResponse(
            success=True,
            message="현재 미션 조회 성공",
            data={
                "mission": mission,
                "current_problem": current_problem,
                "progress": progress
            }
        )
        
    except Exception as e:
        logger.error(f"현재 미션 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="미션 조회 중 오류가 발생했습니다."
        )

@router.post("/start", response_model=APIResponse)
async def start_mission(
    mission_type: MissionType = MissionType.DAILY,
    user_id: int = Depends(get_current_user_id)
):
    """새 미션 시작"""
    try:
        logger.info(f"사용자 {user_id}의 새 미션 시작 요청")
        
        # 기존 진행 중인 미션 확인
        current_mission = mission_service.get_current_mission(user_id)
        if current_mission and current_mission.status == 'in_progress':
            return APIResponse(
                success=False,
                message="이미 진행 중인 미션이 있습니다.",
                data={"current_mission": current_mission}
            )
        
        # 새 미션 생성
        mission = mission_service.create_daily_mission(user_id, mission_type)
        
        # 미션 시작
        mission_service.start_mission(mission.id)
        
        # 업데이트된 미션 조회
        updated_mission = mission_service.get_mission_by_id(mission.id)
        
        # 첫 번째 문제 조회
        first_problem = mission_service.get_next_problem(mission.id)
        
        return APIResponse(
            success=True,
            message="새 미션이 시작되었습니다.",
            data={
                "mission": updated_mission,
                "first_problem": first_problem
            }
        )
        
    except ValueError as e:
        logger.warning(f"미션 시작 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"미션 시작 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="미션 시작 중 오류가 발생했습니다."
        )

@router.get("/{mission_id}", response_model=APIResponse)
async def get_mission(
    mission_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """특정 미션 조회"""
    try:
        mission = mission_service.get_mission_by_id(mission_id)
        
        if not mission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="미션을 찾을 수 없습니다."
            )
        
        # 소유자 확인
        if mission.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="접근 권한이 없습니다."
            )
        
        # 현재 문제 조회
        current_problem = mission_service.get_next_problem(mission_id)
        
        # 진행률 계산
        progress = MissionProgress.calculate_progress(mission, current_problem)
        
        return APIResponse(
            success=True,
            message="미션 조회 성공",
            data={
                "mission": mission,
                "current_problem": current_problem,
                "progress": progress
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"미션 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="미션 조회 중 오류가 발생했습니다."
        )

@router.get("/{mission_id}/progress", response_model=APIResponse)
async def get_mission_progress(
    mission_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """미션 진행률 조회"""
    try:
        mission = mission_service.get_mission_by_id(mission_id)
        
        if not mission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="미션을 찾을 수 없습니다."
            )
        
        if mission.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="접근 권한이 없습니다."
            )
        
        # 현재 문제 조회
        current_problem = mission_service.get_next_problem(mission_id)
        
        # 진행률 계산
        progress = MissionProgress.calculate_progress(mission, current_problem)
        
        return APIResponse(
            success=True,
            message="진행률 조회 성공",
            data=progress
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"진행률 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="진행률 조회 중 오류가 발생했습니다."
        )

@router.post("/{mission_id}/complete", response_model=APIResponse)
async def complete_mission(
    mission_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """미션 완료 처리"""
    try:
        # 미션 소유자 확인
        mission = mission_service.get_mission_by_id(mission_id)
        if not mission or mission.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="미션을 찾을 수 없습니다."
            )
        
        # 미션 완료 확인
        is_completed = mission_service.check_mission_completion(mission_id)
        
        if is_completed:
            # 완료된 미션 정보 조회
            completed_mission = mission_service.get_mission_by_id(mission_id)
            
            return APIResponse(
                success=True,
                message="미션이 완료되었습니다!",
                data={
                    "mission": completed_mission,
                    "completed": True
                }
            )
        else:
            return APIResponse(
                success=False,
                message="아직 완료되지 않은 문제가 있습니다.",
                data={"completed": False}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"미션 완료 처리 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="미션 완료 처리 중 오류가 발생했습니다."
        )

@router.get("/{mission_id}/next-problem", response_model=APIResponse)
async def get_next_problem(
    mission_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """미션의 다음 문제 조회"""
    try:
        # 미션 소유자 확인
        mission = mission_service.get_mission_by_id(mission_id)
        if not mission or mission.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="미션을 찾을 수 없습니다."
            )
        
        # 다음 문제 조회
        next_problem = mission_service.get_next_problem(mission_id)
        
        if not next_problem:
            return APIResponse(
                success=True,
                message="모든 문제를 완료했습니다.",
                data=None
            )
        
        return APIResponse(
            success=True,
            message="다음 문제 조회 성공",
            data=next_problem
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"다음 문제 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="다음 문제 조회 중 오류가 발생했습니다."
        )