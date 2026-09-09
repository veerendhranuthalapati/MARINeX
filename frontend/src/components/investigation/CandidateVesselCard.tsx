import React from 'react';
import { motion } from 'motion/react';
import { Ship, ChevronRight, AlertTriangle, ShieldCheck, MapPin, Gauge } from 'lucide-react';
import { VesselCandidate } from '../../types';
import { RadialScore } from '../ui/RadialScore';
import { CategoryBadge } from '../ui/CategoryBadge';
import { useMarinexStore } from '../../store/useMarinexStore';

interface CandidateVesselCardProps {
  candidate: VesselCandidate;
  isTopRanked?: boolean;
  rank?: number;
  isSelected?: boolean;
  onSelect?: (candidate: VesselCandidate) => void;
}

export const CandidateVesselCard: React.FC<CandidateVesselCardProps> = ({
  candidate,
  isTopRanked = false,
  rank,
  isSelected: propIsSelected,
  onSelect,
}) => {
  const { selectedCandidateMmsi, openEvidenceDrawer } = useMarinexStore();
  const isSelected = propIsSelected !== undefined ? propIsSelected : selectedCandidateMmsi === candidate.vessel?.mmsi;
  const effectiveRank = rank !== undefined ? rank : candidate.ranking || 1;

  const handleClick = () => {
    if (onSelect) {
      onSelect(candidate);
    } else {
      openEvidenceDrawer(candidate);
    }
  };

  const scorePct = Math.round(candidate.overall_score || 0);

  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ duration: 0.15 }}
      onClick={handleClick}
      className={`relative p-3.5 rounded-xl border transition-all cursor-pointer select-none ${
        isSelected
          ? 'bg-[#0f1b2d] border-cyan-500/80 shadow-lg shadow-cyan-950/50 ring-1 ring-cyan-500/40'
          : isTopRanked
          ? 'bg-[#0a121e] border-amber-500/40 hover:border-amber-500/80 hover:bg-[#0c1626]'
          : 'bg-[#070d18] border-slate-800 hover:border-slate-700 hover:bg-[#091220]'
      }`}
    >
      {/* Top Banner Tag */}
      {isTopRanked && (
        <div className="flex items-center justify-between mb-2">
          <span className="text-[9px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-500/40 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            TOP ATTRIBUTION SUSPECT (RANK #{candidate.ranking || 1})
          </span>
          <CategoryBadge category="INFERRED" size="xs" />
        </div>
      )}

      <div className="flex items-start justify-between gap-3">
        {/* Left: Vessel Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <div
              className={`p-1.5 rounded-lg ${
                isTopRanked ? 'bg-amber-500/10 text-amber-400' : 'bg-slate-800 text-slate-300'
              }`}
            >
              <Ship className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-white tracking-wide truncate">
                {candidate.vessel?.vessel_name || 'UNKNOWN VESSEL'}
              </h4>
              <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                <span>MMSI: {candidate.vessel?.mmsi}</span>
                <span>•</span>
                <span>{candidate.vessel?.flag || 'PAN'}</span>
              </div>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 gap-2 mt-2.5 pt-2 border-t border-slate-800/80 text-[10px] font-mono">
            <div className="flex items-center gap-1.5 text-slate-400">
              <MapPin className="w-3 h-3 text-cyan-400" />
              <span>Dist: <b className="text-slate-200">{candidate.evidence_summary?.closest_distance_km ? candidate.evidence_summary.closest_distance_km.toFixed(1) : '1.2'} km</b></span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-400">
              <Gauge className="w-3 h-3 text-cyan-400" />
              <span>Speed: <b className="text-slate-200">{(candidate.evidence_summary?.speed_at_closest_knots || 12.4).toFixed(1)} kn</b></span>
            </div>
          </div>

          {/* Breakdown Factor Bars */}
          <div className="mt-2.5 space-y-1 text-[9px] font-mono">
            <div className="flex items-center justify-between text-slate-400">
              <span>Spatio-Temporal Prox:</span>
              <span className="text-cyan-300">{Math.round(candidate.spatial_proximity_score || 0)}%</span>
            </div>
            <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-cyan-400 rounded-full"
                style={{ width: `${Math.min(100, candidate.spatial_proximity_score || 0)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Right: Radial Score & Action */}
        <div className="flex flex-col items-center justify-between shrink-0 pl-1">
          <RadialScore
            score={scorePct}
            size={52}
            strokeWidth={4.5}
            color={
              scorePct > 80 ? '#f59e0b' : scorePct > 60 ? '#38bdf8' : '#94a3b8'
            }
          />
          <button
            className="mt-2 p-1 rounded-md bg-slate-900 border border-slate-800 hover:border-cyan-500/50 text-slate-400 hover:text-cyan-300 transition-colors"
            title="Inspect Dossier"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </motion.div>
  );
};
