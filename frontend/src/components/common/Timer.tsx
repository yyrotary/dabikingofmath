// 타이머 컴포넌트
import React, { useEffect, useState } from 'react';

interface TimerProps {
  timeSpent: number;
  isRunning?: boolean;
  showIcon?: boolean;
  className?: string;
}

const Timer: React.FC<TimerProps> = ({
  timeSpent,
  isRunning = false,
  showIcon = true,
  className = ''
}) => {
  const [displayTime, setDisplayTime] = useState(timeSpent);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isRunning) {
      interval = setInterval(() => {
        setDisplayTime(prev => prev + 1);
      }, 1000);
    } else {
      setDisplayTime(timeSpent);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isRunning, timeSpent]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getTimeColor = (seconds: number): string => {
    if (seconds < 180) return 'text-green-400'; // 3분 미만 - 녹색
    if (seconds < 300) return 'text-yellow-400'; // 5분 미만 - 노란색
    return 'text-red-400'; // 5분 이상 - 빨간색
  };

  return (
    <div className={`flex items-center ${className}`}>
      {showIcon && (
        <svg
          className={`w-5 h-5 mr-2 ${isRunning ? 'animate-pulse' : ''} ${getTimeColor(displayTime)}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      )}
      <span className={`font-mono font-semibold text-lg ${getTimeColor(displayTime)}`}>
        {formatTime(displayTime)}
      </span>
    </div>
  );
};

export default Timer;