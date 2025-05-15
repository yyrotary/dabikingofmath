// 답안 상태 관리 (Zustand)
import { create } from 'zustand';
import { apiService } from '../services/api';
import { Answer, AnswerResult, CapturedImage, AppError } from '../types';

interface AnswerState {
  // 상태
  currentAnswer: Answer | null;
  answerResult: AnswerResult | null;
  capturedImages: CapturedImage[];
  isSubmitting: boolean;
  isProcessing: boolean;
  error: AppError | null;

  // 액션
  addCapturedImage: (image: CapturedImage) => void;
  removeCapturedImage: (index: number) => void;
  clearCapturedImages: () => void;
  
  submitAnswer: (missionId: number, problemId: number, timeSpent?: number) => Promise<number>;
  processAnswer: (answerId: number) => Promise<void>;
  getAnswerResult: (answerId: number) => Promise<void>;
  addAnswerImages: (answerId: number, images: File[]) => Promise<void>;
  
  // 상태 초기화
  reset: () => void;
  clearError: () => void;
}

export const useAnswerStore = create<AnswerState>((set, get) => ({
  // 초기 상태
  currentAnswer: null,
  answerResult: null,
  capturedImages: [],
  isSubmitting: false,
  isProcessing: false,
  error: null,

  // 캡처된 이미지 추가
  addCapturedImage: (image: CapturedImage) => {
    set(state => ({
      capturedImages: [...state.capturedImages, image],
      error: null,
    }));
  },

  // 캡처된 이미지 제거
  removeCapturedImage: (index: number) => {
    set(state => ({
      capturedImages: state.capturedImages.filter((_, i) => i !== index),
    }));
  },

  // 모든 캡처된 이미지 클리어
  clearCapturedImages: () => {
    // 기존 이미지의 URL을 revoke하여 메모리 해제
    get().capturedImages.forEach(image => {
      URL.revokeObjectURL(image.preview);
    });
    
    set({ capturedImages: [] });
  },

  // 답안 제출
  submitAnswer: async (missionId: number, problemId: number, timeSpent?: number) => {
    const { capturedImages } = get();
    
    if (capturedImages.length === 0) {
      const error = { message: '답안 이미지가 필요합니다.' };
      set({ error });
      throw new Error(error.message);
    }

    set({ isSubmitting: true, error: null });
    
    try {
      const imageFiles = capturedImages.map(img => img.file);
      const response = await apiService.submitAnswer(
        missionId,
        problemId,
        imageFiles,
        timeSpent
      );

      if (response.success && response.data) {
        const answerId = response.data.answer_id;
        
        set({
          isSubmitting: false,
          // capturedImages는 여기서 클리어하지 않음 (결과 확인까지 보존)
        });
        
        return answerId;
      } else {
        throw new Error(response.message || '답안 제출에 실패했습니다.');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '답안 제출 중 오류가 발생했습니다.';
      set({
        isSubmitting: false,
        error: { message: errorMessage },
      });
      throw error;
    }
  },

  // 답안 AI 처리 요청
  processAnswer: async (answerId: number) => {
    set({ isProcessing: true, error: null });
    
    try {
      const response = await apiService.processAnswer(answerId);
      
      if (response.success) {
        set({ isProcessing: false });
        
        // 처리 완료 후 결과 조회
        await get().getAnswerResult(answerId);
      } else {
        throw new Error(response.message || 'AI 처리 요청에 실패했습니다.');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'AI 처리 중 오류가 발생했습니다.';
      set({
        isProcessing: false,
        error: { message: errorMessage },
      });
      throw error;
    }
  },

  // 답안 결과 조회
  getAnswerResult: async (answerId: number) => {
    set({ error: null });
    
    try {
      const response = await apiService.getAnswerResult(answerId);
      
      if (response.success && response.data) {
        const { result, answer } = response.data;
        
        set({
          currentAnswer: answer,
          answerResult: result,
          isProcessing: false,
        });
        
        // 채점이 완료되지 않은 경우
        if (answer.score === null) {
          set({ isProcessing: true });
          
          // 5초 후 다시 확인
          setTimeout(() => {
            get().getAnswerResult(answerId);
          }, 5000);
        }
      } else {
        throw new Error(response.message || '답안 결과 조회에 실패했습니다.');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '답안 결과 조회 중 오류가 발생했습니다.';
      set({
        error: { message: errorMessage },
        isProcessing: false,
      });
      throw error;
    }
  },

  // 답안에 추가 이미지 업로드
  addAnswerImages: async (answerId: number, images: File[]) => {
    set({ isSubmitting: true, error: null });
    
    try {
      const response = await apiService.addAnswerImages(answerId, images);
      
      if (response.success) {
        set({ isSubmitting: false });
        
        // 성공 후 답안 결과 다시 조회
        await get().getAnswerResult(answerId);
      } else {
        throw new Error(response.message || '이미지 추가에 실패했습니다.');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '이미지 추가 중 오류가 발생했습니다.';
      set({
        isSubmitting: false,
        error: { message: errorMessage },
      });
      throw error;
    }
  },

  // 상태 초기화
  reset: () => {
    // 캡처된 이미지 URL 해제
    get().capturedImages.forEach(image => {
      URL.revokeObjectURL(image.preview);
    });
    
    set({
      currentAnswer: null,
      answerResult: null,
      capturedImages: [],
      isSubmitting: false,
      isProcessing: false,
      error: null,
    });
  },

  // 에러 클리어
  clearError: () => {
    set({ error: null });
  },
}));

// 컴포넌트 언마운트시 이미지 URL 정리
window.addEventListener('beforeunload', () => {
  useAnswerStore.getState().clearCapturedImages();
});