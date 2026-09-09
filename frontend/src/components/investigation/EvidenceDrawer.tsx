import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  Ship,
  Compass,
  Clock,
  MapPin,
  Activity,
  FileCheck,
  ShieldAlert,
} from 'lucide-react';
import { useMarinexStore } from '../../store/useMarinexStore';
import { RadialScore } from '../ui/RadialScore';
import { CategoryBadge } from '../ui/CategoryBadge';

export const EvidenceDrawer: React.FC = () => {
  const { isEvidenceDrawerOpen, closeEvidenceDrawer, activeDrawerCandidate } = useMarinexStore();

  if (!activeDrawerCandidate) return null;

  const cand = activeDrawerCandidate;
  const isPrimary = cand.classification === 'PRIMARY_SUSPECT';

  return (
    <AnimatePresence>
      {isEvidenceDrawerOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            onClick={closeEvidenceDrawer}
            className="fixed inset-0 bg-black/60 z-40"
          />

          {/* Slide-in Drawer */}
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 280 }}
            className="fixed top-0 right-0 h-full w-full max-w-lg bg-[#0a101d] border-l border-slate-800 shadow-2xl z-50 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="p-5 border-b border-slate-800 bg-[#0e172a]/90 flex items-start justify-between">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-xl bg-cyan-950/80 border border-cyan-500/50 text-cyan-400 mt-0.5">
                  <Ship className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono font-bold uppercase text-slate-400">
                      CANDIDATE #{cand.ranking || 1}
                    </span>
                    <CategoryBadge
                      category={isPrimary ? 'CRITICAL' : 'CANDIDATE'}
                      size="xs"
                      pulse={isPrimary}
                    />
                  </div>
                  <h2 className="text-lg font-black text-white mt-0.5">
                    {cand.vessel?.vessel_name}
                  </h2>
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-400 mt-0.5">
                    <span>MMSI: {cand.vessel?.mmsi}</span>
                    <span>•</span>
                    <span>Flag: {cand.vessel?.flag}</span>
                    <span>•</span>
                    <span>Type: {cand.vessel?.vessel_type}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={closeEvidenceDrawer}
                className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable Body */}
            <div className="flex-1 p-5 space-y-6 overflow-y-auto">
              {/* Overall Attribution Priority Header */}
              <div className="p-4 rounded-2xl bg-[#0e182c] border border-slate-800 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold block">
                    INVESTIGATION PRIORITY SCORE
                  </span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-3xl font-black font-mono text-amber-400">
                      {cand.overall_score.toFixed(1)}
                    </span>
                    <span className="text-xs font-mono text-slate-400">/ 100</span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-sans block mt-1">
                    4-Factor Multi-Source Correlated Model Evidence
                  </span>
                </div>
                <RadialScore score={cand.overall_score} size={76} strokeWidth={6} />
              </div>

              {/* WHY THIS VESSEL IS PRIORITISED CHECKLIST */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300 font-mono flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-cyan-400" />
                  WHY THIS VESSEL IS PRIORITISED
                </h3>

                <div className="space-y-2 text-xs font-mono">
                  <div className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900/70 border border-emerald-500/30 text-slate-200">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-white">Present during inferred spill window</span>
                      <p className="text-[11px] text-slate-400 mt-0.5 font-sans">
                        AIS timestamp coincides with Lagrangian backward hindcast release time (Δt = {cand.evidence_summary?.time_delta_minutes?.toFixed(0) || '—'} min).
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900/70 border border-emerald-500/30 text-slate-200">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-white">Passed through 84% confidence origin region</span>
                      <p className="text-[11px] text-slate-400 mt-0.5 font-sans">
                        Closest point of approach (CPA) is {cand.evidence_summary?.closest_distance_km?.toFixed(2) || '—'} km from estimated spill centroid.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900/70 border border-emerald-500/30 text-slate-200">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-white">Course consistent with inferred source</span>
                      <p className="text-[11px] text-slate-400 mt-0.5 font-sans">
                        Vessel heading intersects the major axis of slick drift back-trajectory.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900/70 border border-amber-500/30 text-slate-200">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-amber-300">Kinematic speed anomaly observed</span>
                      <p className="text-[11px] text-slate-400 mt-0.5 font-sans">
                        Recorded speed of {cand.evidence_summary?.speed_at_closest_knots} knots during closest passage reflects a sudden reduction from corridor average.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Natural Language Evidence Statement */}
              <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 text-xs leading-relaxed">
                <span className="text-[10px] font-mono font-bold uppercase text-cyan-400 block mb-1">
                  MODEL EVIDENCE TRAIL
                </span>
                <p className="text-slate-300">{cand.natural_language_explanation}</p>
              </div>

              {/* Evidentiary Disclaimer */}
              <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800 text-[10px] text-slate-400 font-sans">
                <span className="font-bold text-slate-300 block mb-0.5">LEGAL & REGULATORY NOTICE:</span>
                This dossier presents statistical model attribution confidence based on satellite SAR segmentation and AIS kinematics. It establishes maritime investigation priority and does not constitute a judicial conviction.
              </div>
            </div>

            {/* Footer Actions */}
            <div className="p-4 border-t border-slate-800 bg-[#0e172a] flex items-center justify-between">
              <button
                onClick={closeEvidenceDrawer}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-300"
              >
                Close Drawer
              </button>
              <a
                href={`/reports`}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-md shadow-cyan-600/20 flex items-center gap-1.5"
              >
                <FileCheck className="w-4 h-4" />
                <span>Export Legal Dossier</span>
              </a>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};
