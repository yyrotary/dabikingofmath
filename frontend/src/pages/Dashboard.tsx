// 대시보드 페이지
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useMissionStore } from '../store/missionStore';
import { MissionType } from '../types';

// Components
import MissionCard from '../components/mission/MissionCard';
import ProgressOverview from '../components/dashboard/ProgressOverview';
import StudyStreak from '../components/dashboard/StudyStreak';
import AchievementBadges from '../components/dashboard/AchievementBadges';
import QuickStats from '../components/dashboard/QuickStats';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Button from '../components/common/Button';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { 
    currentMission, 
    missionProgress, 
    fetchCurrentMission, 
    startNewMission,
    isLoading,
    error,
    clearError 
  } = useMissionStore();

  const [isStartingMission, setIsStartingMission] = useState(false);

  useEffect(() => {
    fetchCurrentMission();
  }, [fetchCurrentMission]);

  const handleStartMission = async (missionType: MissionType = MissionType.DAILY) => {
    setIsStartingMission(true);
    try {
      await startNewMission(missionType);
      if (currentMission) {
        navigate(`/mission/${currentMission.id}`);
      }
    } catch (error) {
      console.error('Failed to start mission:', error);
    } finally {
      setIsStartingMission(false);
    }
  };

  const handleContinueMission = () => {
    if (currentMission) {
      navigate(`/mission/${currentMission.id}`);
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return '좋은 아침이에요';
    if (hour < 18) return '안녕하세요';
    return '좋은 저녁이에요';
  };

  if (isLoading && !currentMission) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 환영 메시지 */}
      <div className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
        <h1 className="text-3xl font-bold text-white mb-2">
          {getGreeting()}, {user?.name}님! 👋
        </h1>
        <p className="text-blue-200">
          오늘도 수학 실력 향상을 위해 함께 노력해봐요!
        </p>
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-200">
          <div className="flex items-center justify-between">
            <span>{error.message}</span>
            <button
              onClick={clearError}
              className="text-red-200 hover:text-white ml-4"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* 현재 미션 또는 시작 버튼 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          {currentMission && currentMission.status !== 'completed' ? (
            <MissionCard
              mission={currentMission}
              progress={missionProgress}
              onContinue={handleContinueMission}
              onStartNew={() => handleStartMission()}
            />
          ) : (
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
              <h2 className="text-xl font-bold text-white mb-4">새로운 학습 시작</h2>
              <p className="text-blue-200 mb-6">
                오늘의 수학 학습을 시작해보세요!
              </p>
              
              <div className="space-y-3">
                <Button
                  onClick={() => handleStartMission(MissionType.DAILY)}
                  loading={isStartingMission}
                  className="w-full"
                  size="lg"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  일일 학습 시작
                </Button>
                
                <div className="grid grid-cols-2 gap-3">
                  <Button
                    onClick={() => handleStartMission(MissionType.REVIEW)}
                    loading={isStartingMission}
                    variant="outline"
                    size="sm"
                  >
                    복습하기
                  </Button>
                  <Button
                    onClick={() => handleStartMission(MissionType.CHALLENGE)}
                    loading={isStartingMission}
                    variant="outline"
                    size="sm"
                  >
                    도전하기
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 진행 상황 개요 */}
        <ProgressOverview />
      </div>

      {/* 통계 & 성취 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <QuickStats />
        <StudyStreak />
        <AchievementBadges />
      </div>

      {/* 추천 학습 */}
      <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
        <h2 className="text-xl font-bold text-white mb-4">추천 학습</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-lg p-4">
            <h3 className="font-semibold text-white mb-2">등차수열 마스터</h3>
            <p className="text-sm text-green-200 mb-3">기초부터 심화까지 완전 정복</p>
            <Button
              size="sm"
              onClick={() => handleStartMission(MissionType.DAILY)}
            >
              시작하기
            </Button>
          </div>
          
          <div className="bg-gradient-to-r from-orange-500/20 to-red-500/20 rounded-lg p-4">
            <h3 className="font-semibold text-white mb-2">약점 보강 특별 과정</h3>
            <p className="text-sm text-orange-200 mb-3">틀린 문제 유형 집중 연습</p>
            <Button
              size="sm"
              onClick={() => handleStartMission(MissionType.REVIEW)}
            >
              시작하기
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;