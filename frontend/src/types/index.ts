// 공통 타입 정의
export interface User {
  id: number;
  name: string;
  grade: string;
  created_at?: string;
}

export interface Problem {
  id: number;
  title: string;
  content: string;
  solution?: string;
  difficulty_level: number;
  topic: string;
  subtopic?: string;
  estimated_time?: number;
  keywords?: string[];
}

export interface Mission {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed';
  total_problems: number;
  completed_problems: number;
  target_score?: number;
  actual_score?: number;
  start_time?: string;
  end_time?: string;
  problems?: Problem[];
}

export interface MissionProgress {
  mission_id: number;
  total_problems: number;
  completed_problems: number;
  current_problem?: Problem;
  progress_percentage: number;
  estimated_remaining_time?: number;
}

export interface Answer {
  id: number;
  user_id: number;
  mission_id: number;
  problem_id: number;
  answer_images: string[];
  extracted_text?: string;
  extracted_markdown?: string;
  score?: number;
  ai_feedback?: string;
  key_concepts_identified: string[];
  mistakes_detected: string[];
  time_spent?: number;
  submitted_at?: string;
  scored_at?: string;
}

export interface AnswerResult {
  answer_id: number;
  score: number;
  feedback: string;
  concepts_learned: string[];
  areas_for_improvement: string[];
  next_recommendations: string[];
}

export interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  timestamp: string;
}

export interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// 앱 상태 타입
export interface AppError {
  message: string;
  code?: string;
  details?: any;
}

// UI 관련 타입
export interface LoadingState {
  [key: string]: boolean;
}

// 카메라 캡처 관련
export interface CapturedImage {
  file: File;
  preview: string;
  timestamp: number;
}

// 학습 분석 관련
export interface LearningInsights {
  user_id: number;
  period_days: number;
  total_problems_solved: number;
  average_score: number;
  improvement_rate: number;
  strong_topics: string[];
  weak_topics: string[];
  recommendations: string[];
  time_efficiency: { [topic: string]: number };
}

export interface PerformanceTrend {
  dates: string[];
  scores: number[];
  topics: string[][];
  difficulty_levels: number[];
}

// 미션 타입
export enum MissionType {
  DAILY = 'daily',
  REVIEW = 'review',
  CHALLENGE = 'challenge',
  ASSESSMENT = 'assessment'
}

// 미션 상태
export enum MissionStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed'
}

// 파일 업로드 관련
export interface FileUploadResponse {
  filename: string;
  file_path: string;
  file_size: number;
  content_type: string;
  upload_time: string;
}