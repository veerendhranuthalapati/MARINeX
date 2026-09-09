import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Sliders } from 'lucide-react';

interface ComparisonSliderProps {
  leftImageSrc: string;
  rightImageSrc: string;
  leftLabel?: string;
  rightLabel?: string;
  aspectRatio?: string;
}

export const ComparisonSlider: React.FC<ComparisonSliderProps> = ({
  leftImageSrc,
  rightImageSrc,
  leftLabel = 'SAR Backscatter (VV/VH)',
  rightLabel = 'AI Slick Segmentation',
  aspectRatio = 'aspect-square',
}) => {
  const [sliderPos, setSliderPos] = useState(50);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    setSliderPos((x / rect.width) * 100);
  };

  const handleTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const touch = e.touches[0];
    const x = Math.max(0, Math.min(touch.clientX - rect.left, rect.width));
    setSliderPos((x / rect.width) * 100);
  };

  return (
    <div
      className={`relative w-full ${aspectRatio} rounded-xl overflow-hidden select-none border border-slate-800 bg-[#050911] shadow-2xl cursor-ew-resize`}
      onMouseDown={() => setIsDragging(true)}
      onMouseUp={() => setIsDragging(false)}
      onMouseLeave={() => setIsDragging(false)}
      onMouseMove={handleMouseMove}
      onTouchMove={handleTouchMove}
    >
      {/* Underlying Right Image (AI Segmentation) */}
      <img
        src={rightImageSrc}
        alt="Segmentation Mask"
        className="absolute inset-0 w-full h-full object-cover pointer-events-none"
      />
      <div className="absolute top-3 right-3 z-10 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/40 text-[10px] font-mono text-cyan-300 font-bold backdrop-blur-sm">
        {rightLabel}
      </div>

      {/* Clipped Left Image (SAR Raw) */}
      <div
        className="absolute inset-0 overflow-hidden pointer-events-none"
        style={{ width: `${sliderPos}%` }}
      >
        <img
          src={leftImageSrc}
          alt="Raw SAR Telemetry"
          className="absolute inset-0 w-full h-full object-cover max-w-none"
          style={{ width: '100%', height: '100%' }}
        />
        <div className="absolute top-3 left-3 z-10 px-2 py-0.5 rounded bg-slate-900/80 border border-slate-700 text-[10px] font-mono text-slate-300 font-bold backdrop-blur-sm">
          {leftLabel}
        </div>
      </div>

      {/* Divider Bar & Handle */}
      <div
        className="absolute inset-y-0 w-0.5 bg-cyan-400 shadow-[0_0_10px_#22d3ee] pointer-events-none"
        style={{ left: `${sliderPos}%` }}
      >
        <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-7 h-7 rounded-full bg-cyan-500 border-2 border-slate-950 flex items-center justify-center shadow-lg text-slate-950">
          <Sliders className="w-3.5 h-3.5" />
        </div>
      </div>
    </div>
  );
};
