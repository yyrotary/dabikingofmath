# 애플리케이션 설정
import os
from functools import lru_cache
from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    APP_NAME: str = "수학 학습 앱"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    VERSION: str = "1.0.0"
    
    # 데이터베이스
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///mathapp.db")
    
    # JWT 설정
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
    
    # AI 서비스 설정
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # 파일 업로드 설정
    UPLOAD_PATH: str = os.getenv("UPLOAD_PATH", "./uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "5242880"))  # 5MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/jpg"]
    
    # CORS 설정
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://*.replit.dev"
    ]
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 사용자 설정 (단일 사용자 앱)
    DEFAULT_USER_NAME: str = "다비"
    DEFAULT_USER_PASSWORD: str = os.getenv("USER_PASSWORD", "dabi123!")  # 실제 환경에서는 변경 필요
    
    # 학습 설정
    DEFAULT_DAILY_PROBLEMS: int = 5
    MIN_PROBLEMS_PER_MISSION: int = 3
    MAX_PROBLEMS_PER_MISSION: int = 10
    
    # AI 처리 설정
    AI_TIMEOUT_SECONDS: int = 30
    IMAGE_PROCESSING_TIMEOUT: int = 15
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    """설정 인스턴스를 반환 (싱글톤 패턴)"""
    return Settings()

# 환경별 설정
def get_database_url() -> str:
    """환경에 따른 데이터베이스 URL 반환"""
    settings = get_settings()
    
    if settings.DEBUG:
        # 개발 환경: SQLite
        return "sqlite:///./mathapp.db"
    else:
        # 프로덕션 환경: 설정된 URL 사용
        return settings.DATABASE_URL

def is_production() -> bool:
    """프로덕션 환경 여부 확인"""
    return not get_settings().DEBUG

def get_cors_origins() -> List[str]:
    """CORS 허용 오리진 반환"""
    settings = get_settings()
    
    if settings.DEBUG:
        # 개발 환경에서는 모든 오리진 허용
        return ["*"]
    else:
        # 프로덕션에서는 특정 오리진만 허용
        return settings.ALLOWED_ORIGINS