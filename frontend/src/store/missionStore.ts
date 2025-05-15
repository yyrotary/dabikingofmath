// 미션 상태 관리 (Zustand)
import { create } from 'zustand';
import { apiService } from '../services/api';
import { Mission, Problem, MissionProgress, AppError, MissionType } from '../types';

interface MissionState {
  // 상태
  currentMission: Mission | null;
  currentProblem: Problem | null;
  missionProgress: MissionProgress | null;
  isLoading: boolean;
  error: AppError | null;
  
  // 문제 풀이 관련
  timeSpent: number;
  startTime: number | null;

  // 액션
  fetchCurrentMission: () => Promise<void>;
  startNewMission: (missionType?: MissionType) => Promise<void>;
  getCurrentProblem: () => Promise<void>;
  updateProgress: () => Promise<void>;
  completeMission: () => Promise<void>;
  
  // 문제 풀이 시간 관리
  startTimer: () => void;
  stopTimer: () => void;
  resetTimer: () => void;
  getTimeSpent: () => number;
  
  // 상태 초기화
  reset: () => void;
  clearError: () => void;
}

export const useMissionStore = create<MissionState>((set, get) => ({
  // 초기 상태
  currentMission: null,
  currentProblem: null,
  missionProgress: null,
  isLoading: false,
  error: null,
  timeSpent: 0,
  startTime: null,

  // 현재 미션 조회
  fetchCurrentMission: async () => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await apiService.getCurrentMission();
      
      if (response.success && response.data) {
        const { mission, current_problem, progress } = response.data;
        set({
          currentMission: mission,
          currentProblem: current_problem,
          missionProgress: progress,
          isLoading: false,
        });
      } else {
        // 진행 중인 미션이 없는 경우
        set({
          currentMission: null,
          currentProblem: null,
          missionProgress: null,
          isLoading: false,
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '미션 조회 중 오류가 발생했습니다.';
      set({
        isLoading: false,
        error: { message: errorMessage },
      });
      throw error;
    }
  },

  // 새 미션 시작
  startNewMission: async (missionType: MissionType = MissionType.DAILY) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await apiService.startMission(missionType);
      
      if (response.success && response.data) {
        const { mission, first_problem } = response.data;
        
        // 진행상황 계산
        const progress: MissionProgress = {
          mission_id: mission.id,
          total_problems: mission.total_problems,
          completed_problems: mission.completed_problems,
          current_problem: first_problem,
          progress_percentage: 0,
        };
        
        set({
          currentMission: mission,
          currentProblem: first_problem,
          missionProgress: progress,
          isLoading: false,
        });
      } else {
        throw new Error(response.message || '미션 시작에 실패했습니다.');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '미션 시작 중 오류가 발생했습니다.';
      set({
        isLoading: false,
        error: { message: errorMessage },
      });
      throw error;
    }
  },

  // 현재 문제 조회
  getCurrentProblem: async () => {
    const { currentMission } = get();
    if (!currentMission) return;

    try {
      const response = await apiService.getNextProblem(currentMission.id);
      
      if (response.success && response.data) {
        set({ currentProblem: response.data });
      } else {
        // 모든 문제 완료
        set({ currentProblem: null });
      }
    } catch (error) {
      console.error('다음 문제 조회 실패:', error);
      const errorMessage = error instanceof Error ? error.message : '문제 조회 중 오류가 발생했습니다.';
      set({ error: { message: errorMessage } });
    }
  },

  // 미션 진행 상황 업데이트
  updateProgress: async () => {
    const { currentMission } = get();
    if (!currentMission) return;

    try {
      const response = await apiService.getMissionProgress(currentMission.id);
      
      if (response.success && response.data) {
        set({ missionProgress: response.data });
        
        // 현재 문제도 업데이트
        if (response.data.current_problem) {
          set({ currentProblem: response.data.current_problem });
        } else {
          // 모든 문제 완료
          set({ currentProblem: null });
        }
      }
    } catch (error) {
      console.error('진행 상황 업데이트 실패:', error);
    }
  },

  // 미션 완료
  completeMission: async () => {
    const { currentMission } = get();
    if (!currentMission) return;

    set({ isLoading: true, error: null });
    
    try {
      const response = await apiService.completeMission(currentMission.id);
      
      if (response.success && response.data) {
        const { mission, completed } = response.data;
        
        if (completed) {
          set({
            currentMission: mission,
            currentProblem: null,
            isLoading: false,
          });
          
          // 미션 완료 후 진행 상황 업데이트
          await get().updateProgress();
        } else {
          set({ isLoading: false });
          throw new Error('아직 완료되지 않은 문제가 있습니다.');
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '미션 완료 처리 중 오류가 발생했습니다.';
      set({
        isLoading: false,
        error: { message: errorMessage },
      });
      throw error;
    }
  },

  // 타이머 시작
  startTimer: () => {
    const now = Date.now();
    set({ startTime: now });
  },

  // 타이머 중지
  stopTimer: () => {
    const { startTime } = get();
    if (startTime) {
      const now = Date.now();
      const elapsed = Math.floor((now - startTime) / 1000);
      set(state => ({ 
        timeSpent: state.timeSpent + elapsed,
        startTime: null 
      }));
    }
  },

  // 타이머 리셋
  resetTimer: () => {
    set({ timeSpent: 0, startTime: null });
  },

  // 현재까지 소요 시간 계산
  getTimeSpent: () => {
    const { timeSpent, startTime } = get();
    if (startTime) {
      const now = Date.now();
      const currentElapsed = Math.floor((now - startTime) / 1000);
      return timeSpent + currentElapsed;
    }
    return timeSpent;
  },

  // 상태 초기화
  reset: () => {
    set({
      currentMission: null,
      currentProblem: null,
      missionProgress: null,
      isLoading: false,
      error: null,
      timeSpent: 0,
      startTime: null,
    });
  },

  // 에러 클리어
  clearError: () => {
    set({ error: null });
  },
}));