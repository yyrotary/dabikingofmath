# 데이터 모델 정의 (Pydantic)
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import json

# 열거형 정의
class MissionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class MissionType(str, Enum):
    DAILY = "daily"
    REVIEW = "review"
    CHALLENGE = "challenge"
    ASSESSMENT = "assessment"

# 기본 모델
class BaseEntity(BaseModel):
    """기본 엔티티 모델"""
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# 사용자 모델
class User(BaseEntity):
    """사용자 모델"""
    name: str = Field(..., description="사용자 이름")
    grade: str = Field(default="고2-1", description="학년")
    password_hash: Optional[str] = Field(None, description="비밀번호 해시")

class UserCreate(BaseModel):
    """사용자 생성 모델"""
    name: str
    password: str
    grade: str = "고2-1"

class UserResponse(BaseEntity):
    """사용자 응답 모델 (비밀번호 제외)"""
    name: str
    grade: str

# 인증 모델
class LoginRequest(BaseModel):
    """로그인 요청 모델"""
    username: str
    password: str

class LoginResponse(BaseModel):
    """로그인 응답 모델"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    """토큰 데이터 모델"""
    user_id: Optional[int] = None

# 문제 모델
class Problem(BaseEntity):
    """문제 모델"""
    title: str = Field(..., description="문제 제목")
    content: str = Field(..., description="문제 내용")
    solution: Optional[str] = Field(None, description="문제 해답")
    difficulty_level: int = Field(..., ge=1, le=10, description="난이도 레벨")
    topic: str = Field(..., description="주제 (등차수열, 등비수열 등)")
    subtopic: Optional[str] = Field(None, description="세부 주제")
    estimated_time: Optional[int] = Field(None, description="예상 풀이 시간(분)")
    keywords: Optional[List[str]] = Field(default_factory=list, description="키워드 목록")

    @classmethod
    def from_db_row(cls, row) -> "Problem":
        """DB 행에서 Problem 객체 생성"""
        keywords = []
        if row['keywords']:
            try:
                keywords = json.loads(row['keywords'])
            except:
                keywords = []
        
        return cls(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            solution=row['solution'],
            difficulty_level=row['difficulty_level'],
            topic=row['topic'],
            subtopic=row['subtopic'],
            estimated_time=row['estimated_time'],
            keywords=keywords,
            created_at=row['created_at']
        )

class ProblemCreate(BaseModel):
    """문제 생성 모델"""
    title: str
    content: str
    solution: Optional[str] = None
    difficulty_level: int = Field(..., ge=1, le=10)
    topic: str
    subtopic: Optional[str] = None
    estimated_time: Optional[int] = None
    keywords: Optional[List[str]] = None

# 미션 모델
class Mission(BaseEntity):
    """미션 모델"""
    user_id: int = Field(..., description="사용자 ID")
    name: str = Field(..., description="미션 이름")
    description: Optional[str] = Field(None, description="미션 설명")
    status: MissionStatus = Field(default=MissionStatus.PENDING, description="미션 상태")
    total_problems: int = Field(..., description="총 문제 수")
    completed_problems: int = Field(default=0, description="완료된 문제 수")
    target_score: Optional[int] = Field(None, description="목표 점수")
    actual_score: Optional[int] = Field(None, description="실제 점수")
    start_time: Optional[datetime] = Field(None, description="시작 시간")
    end_time: Optional[datetime] = Field(None, description="종료 시간")
    problems: Optional[List[Problem]] = Field(default_factory=list, description="미션 문제 목록")

    @classmethod
    def from_db_row(cls, row) -> "Mission":
        """DB 행에서 Mission 객체 생성"""
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            name=row['name'],
            description=row['description'],
            status=MissionStatus(row['status']),
            total_problems=row['total_problems'],
            completed_problems=row['completed_problems'],
            target_score=row['target_score'],
            actual_score=row['actual_score'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            created_at=row['created_at']
        )

class MissionCreate(BaseModel):
    """미션 생성 모델"""
    name: str
    description: Optional[str] = None
    mission_type: MissionType = MissionType.DAILY
    target_problems: int = Field(default=5, ge=1, le=10)
    difficulty_range: Optional[tuple[int, int]] = Field(default=(1, 5))
    topics: Optional[List[str]] = None

class MissionProgress(BaseModel):
    """미션 진행상황 모델"""
    mission_id: int
    total_problems: int
    completed_problems: int
    current_problem: Optional[Problem] = None
    progress_percentage: float
    estimated_remaining_time: Optional[int] = None

    @classmethod
    def calculate_progress(cls, mission: Mission, current_problem: Optional[Problem] = None) -> "MissionProgress":
        """미션 진행률 계산"""
        if mission.total_problems == 0:
            progress = 0.0
        else:
            progress = (mission.completed_problems / mission.total_problems) * 100
        
        return cls(
            mission_id=mission.id,
            total_problems=mission.total_problems,
            completed_problems=mission.completed_problems,
            current_problem=current_problem,
            progress_percentage=round(progress, 2)
        )

# 답안 모델
class Answer(BaseEntity):
    """답안 모델"""
    user_id: int = Field(..., description="사용자 ID")
    mission_id: int = Field(..., description="미션 ID")
    problem_id: int = Field(..., description="문제 ID")
    answer_images: List[str] = Field(default_factory=list, description="답안 이미지 경로 목록")
    extracted_text: Optional[str] = Field(None, description="AI가 추출한 텍스트")
    extracted_markdown: Optional[str] = Field(None, description="마크다운 형태의 답안")
    score: Optional[int] = Field(None, ge=0, le=100, description="점수")
    ai_feedback: Optional[str] = Field(None, description="AI 피드백")
    key_concepts_identified: List[str] = Field(default_factory=list, description="인식된 핵심 개념")
    mistakes_detected: List[str] = Field(default_factory=list, description="발견된 실수")
    time_spent: Optional[int] = Field(None, description="풀이 소요 시간(초)")
    submitted_at: Optional[datetime] = Field(None, description="제출 시간")
    scored_at: Optional[datetime] = Field(None, description="채점 시간")

    @classmethod
    def from_db_row(cls, row) -> "Answer":
        """DB 행에서 Answer 객체 생성"""
        answer_images = []
        key_concepts = []
        mistakes = []
        
        if row['answer_images']:
            try:
                answer_images = json.loads(row['answer_images'])
            except:
                answer_images = []
        
        if row['key_concepts_identified']:
            try:
                key_concepts = json.loads(row['key_concepts_identified'])
            except:
                key_concepts = []
        
        if row['mistakes_detected']:
            try:
                mistakes = json.loads(row['mistakes_detected'])
            except:
                mistakes = []
        
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            mission_id=row['mission_id'],
            problem_id=row['problem_id'],
            answer_images=answer_images,
            extracted_text=row['extracted_text'],
            extracted_markdown=row['extracted_markdown'],
            score=row['score'],
            ai_feedback=row['ai_feedback'],
            key_concepts_identified=key_concepts,
            mistakes_detected=mistakes,
            time_spent=row['time_spent'],
            submitted_at=row['submitted_at'],
            scored_at=row['scored_at'],
            created_at=row['created_at']
        )

class AnswerSubmission(BaseModel):
    """답안 제출 모델"""
    mission_id: int
    problem_id: int
    time_spent: Optional[int] = None

class AnswerResult(BaseModel):
    """답안 결과 모델"""
    answer_id: int
    score: int
    feedback: str
    concepts_learned: List[str]
    areas_for_improvement: List[str]
    next_recommendations: List[str]

# 학습 분석 모델
class LearningAnalytics(BaseEntity):
    """학습 분석 모델"""
    user_id: int = Field(..., description="사용자 ID")
    mission_id: Optional[int] = Field(None, description="미션 ID")
    metric_type: str = Field(..., description="메트릭 타입")
    metric_value: float = Field(..., description="메트릭 값")
    topic: Optional[str] = Field(None, description="주제")
    subtopic: Optional[str] = Field(None, description="세부 주제")
    analysis_data: Optional[Dict[str, Any]] = Field(None, description="상세 분석 데이터")
    recorded_at: Optional[datetime] = Field(None, description="기록 시간")

class LearningInsights(BaseModel):
    """학습 인사이트 모델"""
    user_id: int
    period_days: int
    total_problems_solved: int
    average_score: float
    improvement_rate: float
    strong_topics: List[str]
    weak_topics: List[str]
    recommendations: List[str]
    time_efficiency: Dict[str, float]

class PerformanceTrend(BaseModel):
    """성과 추세 모델"""
    dates: List[str]
    scores: List[float]
    topics: List[str]
    difficulty_levels: List[int]

# 응답 래퍼 모델
class APIResponse(BaseModel):
    """API 응답 래퍼"""
    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = False
    error: dict
    timestamp: datetime = Field(default_factory=datetime.now)

# 파일 업로드 관련
class FileUploadResponse(BaseModel):
    """파일 업로드 응답 모델"""
    filename: str
    file_path: str
    file_size: int
    content_type: str
    upload_time: datetime = Field(default_factory=datetime.now)