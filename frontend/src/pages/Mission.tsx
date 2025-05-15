// 미션 수행 페이지
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMissionStore } from '../store/missionStore';
import { useAnswerStore } from '../store/answerStore';

// Components
import ProblemDisplay from '../components/problem/ProblemDisplay';
import AnswerCapture from '../components/answer/AnswerCapture';
import MissionProgress from '../components/mission/MissionProgress';
import Timer from '../components/common/Timer';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Button from '../components/common/Button';
import ConfirmModal from '../components/common/ConfirmModal';

const Mission: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const {
    currentMission,
    currentProblem,
    missionProgress,
    timeSpent,
    startTimer,
    stopTimer,
    resetTimer,
    getTimeSpent,
    fetchCurrentMission,
    getCurrentProblem,
    updateProgress,
    completeMission,
    isLoading,
    error,
    clearError
  } = useMissionStore();

  const {
    capturedImages,
    submitAnswer,
    reset: resetAnswer,
    isSubmitting,
    error: answerError,
    clearError: clearAnswerError
  } = useAnswerStore();

  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);

  // 미션 로드
  useEffect(() => {
    if (id) {
      fetchCurrentMission();
    }
  }, [id, fetchCurrentMission]);

  // 미션 로드 후 현재 문제 가져오기
  useEffect(() => {
    if (currentMission && !currentProblem) {
      getCurrentProblem();
    }
  }, [currentMission, currentProblem, getCurrentProblem]);

  // 문제가 변경될 때마다 타이머 리셋
  useEffect(() => {
    if (currentProblem) {
      resetTimer();
      startTimer();
      resetAnswer(); // 답안 상태도 초기화
    }
    
    return () => {
      stopTimer();
    };
  }, [currentProblem?.id, resetTimer, startTimer, stopTimer, resetAnswer]);

  // 답안 제출
  const handleSubmitAnswer = async () => {
    if (!currentMission || !currentProblem || capturedImages.length === 0) {
      return;
    }

    setIsSubmittingAnswer(true);
    stopTimer();
    
    try {
      const answerId = await submitAnswer(
        currentMission.id,
        currentProblem.id,
        getTimeSpent()
      );
      
      // 미션 진행 상황 업데이트
      await updateProgress();
      
      // 결과 페이지로 이동
      navigate(`/results/${answerId}`);
    } catch (error) {
      console.error('Failed to submit answer:', error);
      startTimer(); // 실패시 타이머 재시작
    } finally {
      setIsSubmittingAnswer(false);
      setShowSubmitConfirm(false);
    }
  };

  // 미션 완료 확인
  const handleCompleteMission = async () => {
    if (!currentMission) return;
    
    try {
      await completeMission();
      navigate('/dashboard');
    } catch (error) {
      console.error('Failed to complete mission:', error);
    }
  };

  // 미션 종료
  const handleQuitMission = () => {
    stopTimer();
    navigate('/dashboard');
  };

  if (isLoading || !currentMission) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  // 모든 문제 완료
  if (!currentProblem && missionProgress?.progress_percentage === 100) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20">
          <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-white mb-4">미션 완료! 🎉</h2>
          <p className="text-blue-200 mb-6">모든 문제를 해결했습니다. 수고하셨어요!</p>
          <div className="space-y-3">
            <Button onClick={handleCompleteMission} className="w-full">
              미션 완료하기
            </Button>
            <Button onClick={handleQuitMission} variant="outline">
              대시보드로 돌아가기
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!currentProblem) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center">
          <p className="text-white mb-4">문제를 불러오는 중입니다...</p>
          <LoadingSpinner />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 에러 메시지 */}
      {(error || answerError) && (
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-200">
          <div className="flex items-center justify-between">
            <span>{error?.message || answerError?.message}</span>
            <button
              onClick={() => {
                clearError();
                clearAnswerError();
              }}
              className="text-red-200 hover:text-white ml-4"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* 미션 헤더 */}
      <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-4 border border-white/20">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">{currentMission.name}</h1>
            <p className="text-blue-200 text-sm">{currentMission.description}</p>
          </div>
          <div className="flex items-center space-x-4">
            <Timer 
              timeSpent={timeSpent}
              isRunning={true}
            />
            <Button
              onClick={handleQuitMission}
              variant="outline"
              size="sm"
            >
              나가기
            </Button>
          </div>
        </div>
      </div>

      {/* 진행률 */}
      {missionProgress && (
        <MissionProgress
          progress={missionProgress}
          showDetails={true}
        />
      )}

      {/* 메인 컨텐츠 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 문제 표시 */}
        <ProblemDisplay
          problem={currentProblem}
          showSolution={false}
        />

        {/* 답안 작성 */}
        <div className="space-y-4">
          <AnswerCapture />
          
          {/* 제출 버튼 */}
          <div className="space-y-3">
            <Button
              onClick={() => setShowSubmitConfirm(true)}
              disabled={capturedImages.length === 0 || isSubmittingAnswer}
              loading={isSubmittingAnswer}
              className="w-full"
              size="lg"
            >
              {capturedImages.length === 0 
                ? '답안을 작성해주세요' 
                : `답안 제출 (${capturedImages.length}장)`}
            </Button>
            
            <p className="text-sm text-blue-200 text-center">
              답안을 사진으로 찍어 업로드해주세요
            </p>
          </div>
        </div>
      </div>

      {/* 제출 확인 모달 */}
      <ConfirmModal
        isOpen={showSubmitConfirm}
        onClose={() => setShowSubmitConfirm(false)}
        onConfirm={handleSubmitAnswer}
        title="답안 제출"
        message={`${capturedImages.length}장의 답안을 제출하시겠습니까?`}
        confirmText="제출"
        cancelText="취소"
      />
    </div>
  );
};

export default Mission;