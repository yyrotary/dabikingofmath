// 메인 App 컴포넌트
import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { useMissionStore } from './store/missionStore';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Mission from './pages/Mission';
import Results from './pages/Results';

// Components
import LoadingSpinner from './components/common/LoadingSpinner';
import ErrorBoundary from './components/common/ErrorBoundary';
import Layout from './components/common/Layout';

// Styles
import './App.css';

function App() {
  const { isAuthenticated, isLoading, verifyToken } = useAuthStore();
  const { reset: resetMission } = useMissionStore();

  useEffect(() => {
    // 앱 시작시 토큰 검증
    const token = localStorage.getItem('authToken');
    if (token && !isAuthenticated) {
      verifyToken();
    }
  }, [verifyToken, isAuthenticated]);

  // 로그아웃시 모든 스토어 리셋
  useEffect(() => {
    if (!isAuthenticated) {
      resetMission();
    }
  }, [isAuthenticated, resetMission]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-cyan-900 flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="App min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-cyan-900">
        <Router>
          <Routes>
            <Route 
              path="/login" 
              element={
                !isAuthenticated ? <Login /> : <Navigate to="/dashboard" replace />
              } 
            />
            
            <Route
              path="/dashboard"
              element={
                isAuthenticated ? (
                  <Layout>
                    <Dashboard />
                  </Layout>
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            
            <Route
              path="/mission/:id"
              element={
                isAuthenticated ? (
                  <Layout>
                    <Mission />
                  </Layout>
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            
            <Route
              path="/results/:answerId"
              element={
                isAuthenticated ? (
                  <Layout>
                    <Results />
                  </Layout>
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            
            <Route
              path="/"
              element={
                <Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />
              }
            />
            
            {/* 404 페이지 */}
            <Route
              path="*"
              element={
                <div className="min-h-screen flex items-center justify-center text-white">
                  <div className="text-center">
                    <h1 className="text-4xl font-bold mb-4">404</h1>
                    <p className="text-xl mb-8">페이지를 찾을 수 없습니다.</p>
                    <button
                      onClick={() => window.history.back()}
                      className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg font-semibold"
                    >
                      돌아가기
                    </button>
                  </div>
                </div>
              }
            />
          </Routes>
        </Router>
      </div>
    </ErrorBoundary>
  );
}

export default App;