# 인증 라우터
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import logging

from app.models import LoginRequest, LoginResponse, UserResponse, APIResponse
from app.utils.security import authenticate_user, create_access_token, get_current_user_from_token
from app.database.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# OAuth2 스키마
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

@router.post("/login", response_model=APIResponse)
async def login(login_data: LoginRequest):
    """사용자 로그인"""
    try:
        logger.info(f"로그인 시도: {login_data.username}")
        
        # 사용자 인증
        user = authenticate_user(login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="잘못된 사용자명 또는 비밀번호입니다.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # JWT 토큰 생성
        access_token = create_access_token(
            data={"user_id": user["id"], "username": user["name"]}
        )
        
        # 사용자 응답 객체 생성
        user_response = UserResponse(
            id=user["id"],
            name=user["name"],
            grade="고2-1"  # 기본값, 실제로는 DB에서 조회
        )
        
        # 로그인 응답 생성
        login_response = LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
        logger.info(f"로그인 성공: {user['name']}")
        
        return APIResponse(
            success=True,
            message="로그인 성공",
            data=login_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 처리 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다."
        )

@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 호환 토큰 발급 (Form 데이터)"""
    # LoginRequest 객체로 변환
    login_data = LoginRequest(username=form_data.username, password=form_data.password)
    
    # 기존 login 함수 재사용
    response = await login(login_data)
    return response.data

@router.get("/verify", response_model=APIResponse)
async def verify_token(token: str = Depends(oauth2_scheme)):
    """토큰 검증"""
    try:
        # 토큰에서 사용자 정보 추출
        user = get_current_user_from_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 사용자 응답 객체 생성
        user_response = UserResponse(
            id=user["id"],
            name=user["name"],
            grade=user.get("grade", "고2-1")
        )
        
        return APIResponse(
            success=True,
            message="토큰 검증 성공",
            data={"user": user_response}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"토큰 검증 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 검증에 실패했습니다.",
            headers={"WWW-Authenticate": "Bearer"}
        )

@router.post("/logout", response_model=APIResponse)
async def logout(token: str = Depends(oauth2_scheme)):
    """로그아웃 (클라이언트 측에서 토큰 삭제)"""
    try:
        # JWT는 stateless이므로 서버에서 할 일은 없음
        # 실제로는 클라이언트에서 토큰을 삭제해야 함
        
        # 로그 기록용으로 사용자 정보 확인
        user = get_current_user_from_token(token)
        if user:
            logger.info(f"로그아웃: {user['name']}")
        
        return APIResponse(
            success=True,
            message="로그아웃되었습니다. 클라이언트에서 토큰을 삭제해주세요."
        )
        
    except Exception as e:
        logger.error(f"로그아웃 처리 중 오류: {e}")
        # 로그아웃은 실패해도 OK 응답
        return APIResponse(
            success=True,
            message="로그아웃 처리됨"
        )

@router.get("/me", response_model=APIResponse)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """현재 사용자 정보 조회"""
    try:
        user = get_current_user_from_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 상세 사용자 정보 조회
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, grade, created_at FROM users WHERE id = ?",
                (user["id"],)
            )
            user_row = cursor.fetchone()
            
            if not user_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="사용자 정보를 찾을 수 없습니다."
                )
            
            user_response = UserResponse(
                id=user_row["id"],
                name=user_row["name"],
                grade=user_row["grade"],
                created_at=user_row["created_at"]
            )
            
            return APIResponse(
                success=True,
                message="사용자 정보 조회 성공",
                data=user_response
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 정보 조회 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 정보 조회 중 오류가 발생했습니다."
        )

# 현재 사용자 ID를 가져오는 의존성 함수
async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """현재 사용자 ID 반환 (다른 라우터에서 사용)"""
    user = get_current_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user["id"]