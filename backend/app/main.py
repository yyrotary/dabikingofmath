# 백엔드 메인 애플리케이션
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import os
from pathlib import Path

# 로컬 imports
from app.config import get_settings
from app.database.database import init_db, get_db
from app.routers import auth, missions, problems, answers
from app.utils.security import verify_token

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="수학 학습 앱 API",
    description="영양여고 다비님을 위한 개인화 수학 학습 시스템",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 설정 로드
settings = get_settings()

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.replit.dev",
        "*"  # 개발 단계에서는 모든 origin 허용
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 인증 보안 스키마
security = HTTPBearer()

# JWT 토큰 검증 의존성
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """JWT 토큰을 검증하고 현재 사용자 정보를 반환"""
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return payload.get("user_id")

# API 라우터 등록
app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    missions.router,
    prefix="/api/missions",
    tags=["Missions"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    problems.router,
    prefix="/api/problems",
    tags=["Problems"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    answers.router,
    prefix="/api/answers",
    tags=["Answers"],
    dependencies=[Depends(get_current_user)]
)

# 정적 파일 서빙 (업로드된 이미지)
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작시 실행"""
    logger.info("애플리케이션 시작 중...")
    
    # 데이터베이스 초기화
    try:
        init_db()
        logger.info("데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise
    
    # 업로드 디렉토리 생성
    uploads_dir.mkdir(exist_ok=True)
    logger.info("업로드 디렉토리 준비 완료")
    
    logger.info("애플리케이션 시작 완료!")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료시 실행"""
    logger.info("애플리케이션 종료 중...")

# 헬스 체크 엔드포인트
@app.get("/")
async def root():
    """기본 엔드포인트"""
    return {
        "message": "수학 학습 앱 API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # 데이터베이스 연결 확인
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return {
            "status": "healthy",
            "database": "connected",
            "uploads_dir": uploads_dir.exists()
        }
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# 글로벌 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """글로벌 예외 처리"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return HTTPException(
        status_code=500,
        detail="Internal server error"
    )

if __name__ == "__main__":
    import uvicorn
    
    # 개발 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        reload=settings.DEBUG,
        log_level="info"
    )