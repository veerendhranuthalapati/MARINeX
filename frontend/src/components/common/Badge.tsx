import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'danger' | 'warning' | 'success' | 'info' | 'neutral';
  size?: 'sm' | 'md';
  pulse?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  pulse = false,
}) => {
  const variantStyles = {
    primary: 'bg-cyan-950/80 text-cyan-300 border-cyan-500/40',
    danger: 'bg-red-950/80 text-red-300 border-red-500/40',
    warning: 'bg-amber-950/80 text-amber-300 border-amber-500/40',
    success: 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40',
    info: 'bg-blue-950/80 text-blue-300 border-blue-500/40',
    neutral: 'bg-slate-800 text-slate-300 border-slate-700',
  };

  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${variantStyles[variant]} ${sizeStyles[size]}`}
    >
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-current"></span>
        </span>
      )}
      {children}
    </span>
  );
};
