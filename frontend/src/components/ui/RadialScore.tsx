import React from 'react';
import { motion } from 'motion/react';
import { cn } from '../../utils/cn';

interface RadialScoreProps {
  score: number; // 0 to 100
  size?: number; // pixel diameter
  strokeWidth?: number;
  color?: string;
  label?: string;
  className?: string;
}

export const RadialScore: React.FC<RadialScoreProps> = ({
  score,
  size = 64,
  strokeWidth = 5,
  color,
  label,
  className,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedScore = Math.max(0, Math.min(100, score));
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference;

  // Color gradient based on priority severity
  const getColor = (s: number) => {
    if (s >= 75) return '#ef4444'; // High Priority (Red)
    if (s >= 50) return '#f59e0b'; // Moderate (Amber)
    return '#38bdf8'; // Low/Analytical (Cyan)
  };

  const strokeColor = color || getColor(clampedScore);

  return (
    <div className={cn('flex flex-col items-center justify-center', className)}>
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="rotate-[-90deg]">
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#1e293b"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Animated Value Arc */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-xs font-black tracking-tight text-white">
            {clampedScore.toFixed(0)}
          </span>
          <span className="text-[8px] font-mono text-slate-500 uppercase -mt-0.5">%</span>
        </div>
      </div>
      {label && (
        <span className="mt-1 text-[9px] font-mono font-semibold uppercase text-slate-400 tracking-wider text-center">
          {label}
        </span>
      )}
    </div>
  );
};
