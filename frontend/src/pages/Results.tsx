// 결과 페이지
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAnswerStore } from '../store/answerStore';
import { useMissionStore } from '../store/missionStore';

// Components
import ScoreDisplay from '../components/result/ScoreDisplay';
import FeedbackDisplay from '../components/result/FeedbackDisplay';
import ConceptsLearned from '../components/result/ConceptsLearned';
import MistakesAnalysis from '../components/result/MistakesAnalysis';
import NextSteps from '../components/result/NextSteps';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Button from '../components/common/Button';

const Results: React.FC = () => {
  const { answerId } = useParams<{ answerId: string }>();
  const navigate = useNavigate();
  
  const {
    currentAnswer,
    answerResult,
    getAnswerResult,
    isProcessing,
    error,
    clearError
  } = useAnswerStore();

  const {
    currentMission,
    getCurrentProblem,
    updateProgress,
    completeMission
  } = useMissionStore();

  const [hasNextProblem, setHasNextProblem] = useState<boolean | null>(null);

  // 답안 결과 로드
  useEffect(() => {
    if (answerId) {
      getAnswerResult(parseInt(answerId));
    }
  }, [answerId, getAnswerResult]);

  // 다음 문제 확인
  useEffect(() => {
    const checkNextProblem = async () => {
      if (currentMission) {
        try {
          await updateProgress();
          await getCurrentProblem();
          // mission store의 currentProblem 상태를 확인
          setHasNextProblem(true); // 임시로 true 설정
        } catch {
          setHasNextProblem(false);
        }
      }
    };

    if (currentAnswer && answerResult) {
      checkNextProblem();
    }
  }, [currentAnswer, answerResult, currentMission, updateProgress, getCurrentProblem]);

  const handleNextProblem = () => {
    if (currentMission) {
      navigate(`/mission/${currentMission.id}`);
    }
  };

  const handleCompleteMission = async () => {
    if (currentMission) {
      try {
        await completeMission();
        navigate('/dashboard');
      } catch (error) {
        console.error('Failed to complete mission:', error);
      }
    }
  };

  const handleBackToDashboard = () => {
    navigate('/dashboard');
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-400';
    if (score >= 70) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreMessage = (score: number) => {
    if (score >= 90) return '훌륭해요! 🎉';
    if (score >= 70) return '잘했어요! 👍';
    if (score >= 50) return '좋은 시도예요! 💪';
    return '다시 한번 도전해봐요! 📚';
  };

  if (!answerId) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center">
          <p className="text-white">잘못된 접근입니다.</p>
          <Button onClick={handleBackToDashboard} className="mt-4">
            대시보드로 돌아가기
          </Button>
        </div>
      </div>
    );
  }

  if (isProcessing || !answerResult) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20">
          <LoadingSpinner size="large" />
          <h2 className="text-xl font-bold text-white mt-4 mb-2">AI가 답안을 채점하고 있어요</h2>
          <p className="text-blue-200">잠시만 기다려주세요... ⏰</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20">
          <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">채점 중 오류가 발생했어요</h2>
          <p className="text-red-200 mb-6">{error.message}</p>
          <div className="space-y-3">
            <Button onClick={() => getAnswerResult(parseInt(answerId))} className="w-full">
              다시 시도
            </Button>
            <Button onClick={handleBackToDashboard} variant="outline">
              대시보드로 돌아가기
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 점수 표시 */}
      <div className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white mb-2">채점 완료!</h1>
          <div className={`text-6xl font-bold mb-2 ${getScoreColor(answerResult.score)}`}>
            {answerResult.score}점
          </div>
          <p className="text-xl text-blue-200">{getScoreMessage(answerResult.score)}</p>
        </div>
      </div>

      {/* 상세 결과 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 점수 상세 */}
        <ScoreDisplay
          score={answerResult.score}
          feedback={answerResult.feedback}
        />

        {/* AI 피드백 */}
        <FeedbackDisplay
          feedback={answerResult.feedback}
        />
      </div>

      {/* 학습 분석 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 이해한 개념 */}
        {answerResult.concepts_learned.length > 0 && (
          <ConceptsLearned
            concepts={answerResult.concepts_learned}
          />
        )}

        {/* 실수 분석 */}
        {answerResult.areas_for_improvement.length > 0 && (
          <MistakesAnalysis
            mistakes={answerResult.areas_for_improvement}
          />
        )}
      </div>

      {/* 다음 단계 */}
      <NextSteps
        recommendations={answerResult.next_recommendations}
        hasNextProblem={hasNextProblem}
        onNextProblem={handleNextProblem}
        onCompleteMission={handleCompleteMission}
        onBackToDashboard={handleBackToDashboard}
      />

      {/* 답안 이미지 (선택사항) */}
      {currentAnswer?.answer_images && currentAnswer.answer_images.length > 0 && (
        <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
          <h3 className="text-lg font-semibold text-white mb-4">제출한 답안</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {currentAnswer.answer_images.map((imagePath, index) => (
              <div key={index} className="relative group">
                <img
                  src={`${process.env.REACT_APP_API_URL}/${imagePath}`}
                  alt={`답안 ${index + 1}`}
                  className="w-full h-48 object-cover rounded-lg border border-white/20"
                />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center">
                  <span className="text-white font-semibold">답안 {index + 1}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Results;