import React from 'react';
import { cn } from '../../utils/cn';

export type IntelligenceCategory =
  | 'OBSERVED'
  | 'SIMULATED'
  | 'INFERRED'
  | 'TRACKED'
  | 'CANDIDATE'
  | 'DEMO_DATA'
  | 'CRITICAL'
  | 'VERIFIED';

interface CategoryBadgeProps {
  category: IntelligenceCategory;
  label?: string;
  size?: 'xs' | 'sm' | 'md';
  pulse?: boolean;
  className?: string;
}

export const CategoryBadge: React.FC<CategoryBadgeProps> = ({
  category,
  label,
  size = 'sm',
  pulse = false,
  className,
}) => {
  const configs: Record<IntelligenceCategory, { text: string; styles: string; dot: string }> = {
    OBSERVED: {
      text: label || 'OBSERVED SLICK',
      styles: 'bg-red-950/80 text-red-300 border-red-500/50 shadow-red-950/50',
      dot: 'bg-red-400',
    },
    SIMULATED: {
      text: label || 'SIMULATED DRIFT',
      styles: 'bg-amber-950/80 text-amber-300 border-amber-500/50 shadow-amber-950/50',
      dot: 'bg-amber-400',
    },
    INFERRED: {
      text: label || 'INFERRED ORIGIN',
      styles: 'bg-yellow-950/80 text-yellow-300 border-yellow-500/50 shadow-yellow-950/50',
      dot: 'bg-yellow-400',
    },
    TRACKED: {
      text: label || 'TRACKED AIS',
      styles: 'bg-blue-950/80 text-blue-300 border-blue-500/50 shadow-blue-950/50',
      dot: 'bg-blue-400',
    },
    CANDIDATE: {
      text: label || 'CANDIDATE VESSEL',
      styles: 'bg-cyan-950/80 text-cyan-300 border-cyan-500/50 shadow-cyan-950/50',
      dot: 'bg-cyan-400',
    },
    DEMO_DATA: {
      text: label || 'DEMO DATA',
      styles: 'bg-slate-900 text-slate-400 border-slate-700/80 font-mono',
      dot: 'bg-slate-500',
    },
    CRITICAL: {
      text: label || 'CRITICAL SPILL',
      styles: 'bg-red-950 text-red-200 border-red-500 font-bold animate-pulse',
      dot: 'bg-red-400',
    },
    VERIFIED: {
      text: label || 'VERIFIED MODEL',
      styles: 'bg-emerald-950/80 text-emerald-300 border-emerald-500/50',
      dot: 'bg-emerald-400',
    },
  };

  const cfg = configs[category];

  const sizeStyles = {
    xs: 'text-[9px] px-1.5 py-0.5 tracking-wider',
    sm: 'text-[10px] px-2 py-0.5 tracking-wider',
    md: 'text-xs px-2.5 py-1 tracking-widest',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-mono font-bold uppercase rounded-md border shadow-sm transition-all',
        cfg.styles,
        sizeStyles[size],
        className
      )}
    >
      <span className="relative flex h-1.5 w-1.5">
        {pulse && (
          <span
            className={cn(
              'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
              cfg.dot
            )}
          />
        )}
        <span className={cn('relative inline-flex rounded-full h-1.5 w-1.5', cfg.dot)} />
      </span>
      <span>{cfg.text}</span>
    </span>
  );
};
