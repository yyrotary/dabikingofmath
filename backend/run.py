# 개발 서버 실행 스크립트
import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    # 환경 변수 설정
    os.environ.setdefault("DEBUG", "true")
    
    # 업로드 디렉토리 생성
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # uvicorn으로 개발 서버 실행
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        reload=True,
        log_level="info"
    )