// API 서비스 클래스
import { 
  APIResponse, 
  Mission, 
  Problem, 
  Answer, 
  AnswerResult,
  MissionProgress,
  LearningInsights,
  PerformanceTrend
} from '../types';

class ApiService {
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    const token = localStorage.getItem('authToken');

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  private async uploadRequest<T>(
    endpoint: string,
    formData: FormData
  ): Promise<APIResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    const token = localStorage.getItem('authToken');

    const config: RequestInit = {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Upload request failed:', error);
      throw error;
    }
  }

  // 인증 관련 API
  async login(username: string, password: string) {
    return this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async verifyToken() {
    return this.request('/api/auth/verify');
  }

  async logout() {
    return this.request('/api/auth/logout', {
      method: 'POST',
    });
  }

  async getCurrentUser() {
    return this.request('/api/auth/me');
  }

  // 미션 관련 API
  async getCurrentMission(): Promise<APIResponse<{
    mission: Mission;
    current_problem: Problem;
    progress: MissionProgress;
  }>> {
    return this.request('/api/missions/current');
  }

  async startMission(missionType: string = 'daily'): Promise<APIResponse<{
    mission: Mission;
    first_problem: Problem;
  }>> {
    return this.request('/api/missions/start', {
      method: 'POST',
      body: JSON.stringify({ mission_type: missionType }),
    });
  }

  async getMission(missionId: number): Promise<APIResponse<{
    mission: Mission;
    current_problem: Problem;
    progress: MissionProgress;
  }>> {
    return this.request(`/api/missions/${missionId}`);
  }

  async getMissionProgress(missionId: number): Promise<APIResponse<MissionProgress>> {
    return this.request(`/api/missions/${missionId}/progress`);
  }

  async completeMission(missionId: number): Promise<APIResponse<{
    mission: Mission;
    completed: boolean;
  }>> {
    return this.request(`/api/missions/${missionId}/complete`, {
      method: 'POST',
    });
  }

  async getNextProblem(missionId: number): Promise<APIResponse<Problem>> {
    return this.request(`/api/missions/${missionId}/next-problem`);
  }

  // 문제 관련 API
  async getProblem(problemId: number): Promise<APIResponse<Problem>> {
    return this.request(`/api/problems/${problemId}`);
  }

  async getProblemsByTopic(
    topic: string,
    difficultyMin: number = 1,
    difficultyMax: number = 10,
    limit: number = 10
  ): Promise<APIResponse<{
    problems: Problem[];
    count: number;
    topic: string;
    difficulty_range: [number, number];
  }>> {
    const params = new URLSearchParams({
      difficulty_min: difficultyMin.toString(),
      difficulty_max: difficultyMax.toString(),
      limit: limit.toString(),
    });
    return this.request(`/api/problems/by-topic/${topic}?${params}`);
  }

  async getProblemsByMission(missionId: number): Promise<APIResponse<{
    mission_id: number;
    problems: Array<{
      problem: Problem;
      sequence_order: number;
      is_completed: boolean;
    }>;
    total_count: number;
  }>> {
    return this.request(`/api/problems/by-mission/${missionId}`);
  }

  // 답안 관련 API
  async submitAnswer(
    missionId: number,
    problemId: number,
    images: File[],
    timeSpent?: number
  ): Promise<APIResponse<{
    answer_id: number;
    status: string;
    image_count: number;
  }>> {
    const formData = new FormData();
    formData.append('mission_id', missionId.toString());
    formData.append('problem_id', problemId.toString());
    
    if (timeSpent !== undefined) {
      formData.append('time_spent', timeSpent.toString());
    }

    images.forEach((image, index) => {
      formData.append('images', image);
    });

    return this.uploadRequest('/api/answers/submit', formData);
  }

  async processAnswer(answerId: number): Promise<APIResponse<any>> {
    return this.request(`/api/answers/${answerId}/process`, {
      method: 'POST',
    });
  }

  async getAnswerResult(answerId: number): Promise<APIResponse<{
    result: AnswerResult;
    answer: Answer;
    problem_info: {
      title: string;
      topic: string;
    };
  }>> {
    return this.request(`/api/answers/${answerId}/result`);
  }

  async addAnswerImages(
    answerId: number,
    images: File[]
  ): Promise<APIResponse<{
    answer_id: number;
    total_images: number;
    added_images: number;
  }>> {
    const formData = new FormData();
    images.forEach((image) => {
      formData.append('images', image);
    });

    return this.uploadRequest(`/api/answers/${answerId}/images`, formData);
  }

  // 학습 분석 관련 API (추후 구현)
  async getLearningInsights(periodDays: number = 7): Promise<APIResponse<LearningInsights>> {
    return this.request(`/api/analytics/insights?period_days=${periodDays}`);
  }

  async getPerformanceTrend(periodDays: number = 30): Promise<APIResponse<PerformanceTrend>> {
    return this.request(`/api/analytics/trend?period_days=${periodDays}`);
  }

  // 헬스 체크
  async healthCheck(): Promise<APIResponse<any>> {
    return this.request('/health');
  }
}

export const apiService = new ApiService();