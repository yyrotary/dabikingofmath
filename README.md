# 수학 도우미

개인화된 AI 기반 수학 학습 시스템

## 프로젝트 개요

- **대상**: 
- **목표**: 6월말까지 수능 수준 문제 해결 능력 달성
- **현재 성적**: 50-60점 → 목표 90점+
- **주요 단원**: 수열 (등차수열, 등비수열, 수학적 귀납법)

## 기술 스택

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (개발), PostgreSQL (프로덕션)
- **AI Engine**: Gemini 2.0 Flash API
- **Authentication**: JWT
- **File Upload**: Python Multipart

### Frontend
- **Framework**: React 18 + TypeScript
- **State Management**: Zustand
- **Styling**: TailwindCSS
- **Build Tool**: Create React App
- **PWA**: Service Worker

### Infrastructure
- **Development**: Replit
- **File Storage**: Local filesystem → S3 compatible
- **Deployment**: Docker ready

## 주요 기능

### 1. 개인화 학습
- 사용자 맞춤형 미션 생성
- 적응형 난이도 조정
- 학습 패턴 분석

### 2. AI 기반 채점
- 필기 답안 이미지 분석
- 실시간 피드백 제공
- 개념 이해도 평가

### 3. 게이미피케이션
- 미션 시스템
- 진행률 추적
- 성취 배지

### 4. 학습 분석
- 실시간 성과 모니터링
- 약점 분석
- 개선 제안

## 프로젝트 구조

```
suhakssem/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── database/
│   │   └── utils/
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── store/
│   │   ├── types/
│   │   └── utils/
│   ├── public/
│   └── package.json
├── data/
│   └── problems_sequences.json
└── shared/
    └── types.ts
```

## 설치 및 실행

### Backend 실행
```bash
cd backend
pip install -r requirements.txt
python run.py
```

### Frontend 실행
```bash
cd frontend
npm install
npm start
```

### 환경 변수 설정
```bash
# backend/.env
DEBUG=true
JWT_SECRET=your-secret-key
GEMINI_API_KEY=your-gemini-api-key
```

## API 문서

- **Swagger UI**: http://localhost:5000/api/docs
- **ReDoc**: http://localhost:5000/api/redoc

## 개발 가이드

### Backend 개발
1. FastAPI 자동 타입 검증 활용
2. Pydantic 모델 사용
3. 의존성 주입 패턴 적용
4. 모듈화된 서비스 구조

### Frontend 개발
1. TypeScript 엄격 모드 사용
2. Zustand로 상태 관리
3. API 응답 타입 정의
4. PWA 가이드라인 준수

## 배포

### Docker 배포
```bash
# Backend
docker build -t suhakssem-backend ./backend
docker run -p 5000:5000 suhakssem-backend

# Frontend
docker build -t suhakssem-frontend ./frontend
docker run -p 3000:3000 suhakssem-frontend
```

## 라이선스

이 프로젝트는 영양여고 다비님을 위한 개인 학습용 프로젝트입니다.

## 기여

현재 개인 프로젝트로 운영 중입니다.

## 문의

개발 관련 문의는 이슈를 통해 남겨주세요.
