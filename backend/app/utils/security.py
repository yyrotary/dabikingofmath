# 보안 관련 유틸리티
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 비밀번호 해시 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """비밀번호를 해시화"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    
    # 만료 시간 설정
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    
    # JWT 토큰 생성
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # 토큰 만료 확인
        exp = payload.get("exp")
        if exp is None:
            logger.warning("토큰에 만료 시간이 없습니다")
            return None
        
        if datetime.utcnow() > datetime.fromtimestamp(exp):
            logger.warning("토큰이 만료되었습니다")
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("만료된 토큰입니다")
        return None
    except jwt.JWTError as e:
        logger.warning(f"JWT 검증 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"토큰 검증 중 오류 발생: {e}")
        return None

def decode_token(token: str) -> dict:
    """토큰 디코딩 (검증 없이)"""
    try:
        return jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": False}
        )
    except Exception as e:
        logger.error(f"토큰 디코딩 실패: {e}")
        return {}

# 사용자 인증 도우미 함수
def authenticate_user(username: str, password: str) -> Optional[dict]:
    """사용자 인증"""
    from app.database.database import get_db
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, password_hash FROM users WHERE name = ?",
            (username,)
        )
        user = cursor.fetchone()
        
        if not user:
            logger.warning(f"사용자를 찾을 수 없습니다: {username}")
            return None
        
        if not verify_password(password, user['password_hash']):
            logger.warning(f"잘못된 비밀번호: {username}")
            return None
        
        return {
            "id": user['id'],
            "name": user['name']
        }

def get_current_user_from_token(token: str) -> Optional[dict]:
    """토큰에서 현재 사용자 정보 조회"""
    payload = verify_token(token)
    if not payload:
        return None
    
    user_id = payload.get("user_id")
    if not user_id:
        return None
    
    from app.database.database import get_db
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, grade FROM users WHERE id = ?",
            (user_id,)
        )
        user = cursor.fetchone()
        
        if user:
            return {
                "id": user['id'],
                "name": user['name'],
                "grade": user['grade']
            }
    
    return None

# 권한 검증 데코레이터
def require_auth(func):
    """인증 필요 데코레이터"""
    def wrapper(*args, **kwargs):
        # FastAPI에서는 Depends를 사용하므로 데코레이터 방식은 참고용
        pass
    return wrapper

# 보안 헤더 추가
def add_security_headers(response):
    """보안 헤더 추가"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# 입력 검증 및 새니타이제이션
def sanitize_input(text: str) -> str:
    """입력 텍스트 새니타이제이션"""
    if not text:
        return ""
    
    # 기본적인 HTML 태그 제거
    import re
    text = re.sub(r'<[^>]*>', '', text)
    
    # 특수 문자 처리
    text = text.strip()
    
    return text

def validate_file_type(filename: str, allowed_types: list) -> bool:
    """파일 타입 검증"""
    if not filename:
        return False
    
    file_ext = filename.lower().split('.')[-1]
    return f".{file_ext}" in [t.lower() for t in allowed_types]

# 레이트 리미팅 (간단한 구현)
class RateLimiter:
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """레이트 리미팅 체크"""
        now = datetime.utcnow()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # 윈도우 밖의 요청 제거
        cutoff = now - timedelta(seconds=window_seconds)
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > cutoff
        ]
        
        # 현재 요청 수 확인
        if len(self.requests[key]) >= limit:
            return False
        
        # 요청 기록
        self.requests[key].append(now)
        return True

# 전역 레이트 리미터 인스턴스
rate_limiter = RateLimiter()

# API 키 검증 (필요시)
def verify_api_key(api_key: str) -> bool:
    """API 키 검증"""
    # 현재는 단일 사용자 앱이므로 사용하지 않음
    # 필요시 구현
    return True