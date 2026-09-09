import React, { useEffect } from 'react';
import { motion } from 'motion/react';
import { Play, Pause, RotateCcw, FastForward, Clock } from 'lucide-react';
import { useMarinexStore } from '../../store/useMarinexStore';

interface TimelineScrubberProps {
  maxHours?: number;
  step?: number;
}

export const TimelineScrubber: React.FC<TimelineScrubberProps> = ({
  maxHours = 6.0,
  step = 0.5,
}) => {
  const { timelineHours, isTimelinePlaying, setTimelineHours, toggleTimelinePlay } =
    useMarinexStore();

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isTimelinePlaying) {
      interval = setInterval(() => {
        setTimelineHours(timelineHours <= 0 ? maxHours : Math.max(0, timelineHours - 0.25));
      }, 500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isTimelinePlaying, timelineHours, maxHours, setTimelineHours]);

  return (
    <div className="w-full bg-[#080e1a]/95 border border-slate-800 rounded-xl p-3 shadow-xl backdrop-blur-md select-none">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold text-white tracking-wide uppercase">
            Lagrangian Drift Hindcast Timeline
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
            SIMULATED
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-xs font-mono font-bold text-cyan-300">
              {timelineHours === 0
                ? 'T0 (SAR Acquisition)'
                : `T - ${timelineHours.toFixed(1)} hrs`}
            </span>
            <span className="text-[10px] text-slate-400 font-mono block">
              {timelineHours === 0
                ? 'Current Observed Slick'
                : `Reconstructed Source at -${timelineHours}h`}
            </span>
          </div>
        </div>
      </div>

      <div className="relative w-full flex items-center gap-3 py-1">
        <button
          onClick={toggleTimelinePlay}
          className="w-8 h-8 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white flex items-center justify-center transition-all shadow-md shadow-cyan-600/30 shrink-0"
          title={isTimelinePlaying ? 'Pause Replay' : 'Play Drift Hindcast'}
        >
          {isTimelinePlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>

        <button
          onClick={() => setTimelineHours(0)}
          className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors shrink-0"
          title="Jump to Observation Time (T0)"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        <div className="relative flex-1 flex items-center">
          <input
            type="range"
            min="0"
            max={maxHours}
            step={step}
            value={timelineHours}
            onChange={(e) => setTimelineHours(parseFloat(e.target.value))}
            className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 focus:outline-none"
          />
        </div>

        <button
          onClick={() => setTimelineHours(maxHours)}
          className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors shrink-0"
          title="Jump to Max Hindcast Window (T - 6h)"
        >
          <FastForward className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex justify-between text-[10px] font-mono text-slate-500 pt-1 px-14">
        <span>T0 (0h)</span>
        <span>-1.5h</span>
        <span>-3.0h (Mean Origin)</span>
        <span>-4.5h</span>
        <span>-6.0h (Max Release)</span>
      </div>
    </div>
  );
};
