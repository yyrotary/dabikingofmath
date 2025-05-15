// 인증 상태 관리 (Zustand)
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiService } from '../services/api';
import { User, LoginRequest, AppError } from '../types';

interface AuthState {
  // 상태
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: AppError | null;

  // 액션
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  verifyToken: () => Promise<void>;
  clearError: () => void;
  updateUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // 초기 상태
      isAuthenticated: false,
      user: null,
      token: null,
      isLoading: false,
      error: null,

      // 로그인
      login: async (credentials: LoginRequest) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await apiService.login(
            credentials.username,
            credentials.password
          );

          if (response.success && response.data) {
            const { access_token, user } = response.data;
            
            // 토큰을 localStorage에 저장
            localStorage.setItem('authToken', access_token);
            
            set({
              isAuthenticated: true,
              user,
              token: access_token,
              isLoading: false,
              error: null,
            });
          } else {
            throw new Error(response.message || '로그인에 실패했습니다.');
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : '로그인 중 오류가 발생했습니다.';
          set({
            isLoading: false,
            error: { message: errorMessage },
            isAuthenticated: false,
            user: null,
            token: null,
          });
          // localStorage에서 토큰 제거
          localStorage.removeItem('authToken');
          throw error;
        }
      },

      // 로그아웃
      logout: () => {
        // localStorage에서 토큰 제거
        localStorage.removeItem('authToken');
        
        // 서버에 로그아웃 요청 (백그라운드에서 실행)
        apiService.logout().catch(console.error);
        
        set({
          isAuthenticated: false,
          user: null,
          token: null,
          error: null,
        });
      },

      // 토큰 검증
      verifyToken: async () => {
        const token = localStorage.getItem('authToken');
        
        if (!token) {
          set({ isAuthenticated: false, user: null, token: null });
          return;
        }

        set({ isLoading: true });
        
        try {
          const response = await apiService.verifyToken();
          
          if (response.success && response.data?.user) {
            set({
              isAuthenticated: true,
              user: response.data.user,
              token,
              isLoading: false,
              error: null,
            });
          } else {
            throw new Error('토큰 검증에 실패했습니다.');
          }
        } catch (error) {
          console.error('Token verification failed:', error);
          localStorage.removeItem('authToken');
          set({
            isAuthenticated: false,
            user: null,
            token: null,
            isLoading: false,
            error: null, // 토큰 검증 실패는 에러로 표시하지 않음
          });
        }
      },

      // 에러 클리어
      clearError: () => {
        set({ error: null });
      },

      // 사용자 정보 업데이트
      updateUser: (user: User) => {
        set({ user });
      },
    }),
    {
      name: 'auth-storage',
      // 토큰만 persist하고 나머지는 재로드시 다시 검증
      partialize: (state) => ({ token: state.token }),
    }
  )
);

// 토큰이 있으면 앱 시작시 자동으로 검증
const token = localStorage.getItem('authToken');
if (token) {
  useAuthStore.getState().verifyToken();
}