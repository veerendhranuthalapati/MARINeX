import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Printer,
  ShieldCheck,
  FileCheck,
  AlertTriangle,
  ArrowUpRight,
  Fingerprint,
  Anchor,
  Clock,
  MapPin,
  Ship,
  Wind,
} from 'lucide-react';
import { MarineXApi } from '../services/api';
import type { Investigation, InvestigationReport } from '../types';
import { CategoryBadge } from '../components/investigation/CategoryBadge';

export const ReportsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [selectedSlickId, setSelectedSlickId] = useState<string>('');
  const [report, setReport] = useState<InvestigationReport | null>(null);
  const [generating, setGenerating] = useState<boolean>(false);

  useEffect(() => {
    loadInvestigations();
  }, []);

  const loadInvestigations = async () => {
    try {
      const invs = await MarineXApi.getInvestigations();
      setInvestigations(invs);

      const querySlickId = searchParams.get('invId');
      if (querySlickId) {
        setSelectedSlickId(querySlickId);
        loadReport(querySlickId);
      } else if (invs.length > 0) {
        setSelectedSlickId(invs[0].slick_id);
        loadReport(invs[0].slick_id);
      }
    } catch (err) {
      console.error('Failed to load investigations:', err);
    }
  };

  const loadReport = async (slickId: string) => {
    setGenerating(true);
    try {
      const rep = await MarineXApi.generateReport(slickId);
      setReport(rep);
    } catch (err) {
      console.error('Failed to generate report:', err);
      setReport(null);
    } finally {
      setGenerating(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const suspectVessel = report?.candidate_vessels?.find((c) => c.rank === 1);

  return (
    <div className="space-y-12">
      {/* Editorial Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-8 border-b border-monochrome-800/80">
        <div className="space-y-3">
          <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
            COURT-ADMISSIBLE EVIDENCE DOSSIER
          </span>
          <CategoryBadge category="INFERRED" size="xs" />
          <h1 className="text-4xl sm:text-6xl font-display font-extrabold tracking-tighter text-monochrome-50">
            Legal Attribution Report
          </h1>
          <p className="text-sm sm:text-base font-heading text-monochrome-400 font-light max-w-3xl">
            Automated evidentiary synthesis documenting satellite observation metadata, calibrated
            segmentation parameters, hydrodynamic hindcast plume coordinates, and ranked vessel
            trajectories.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 text-xs font-heading font-bold uppercase tracking-wider transition-all cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Dossier</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Case Selector */}
      <div className="flex items-center gap-4 p-4 rounded-xl border border-monochrome-800/80 bg-monochrome-950/50">
        <span className="text-xs font-mono uppercase text-monochrome-400">Select Case:</span>
        <select
          value={selectedSlickId}
          onChange={(e) => {
            setSelectedSlickId(e.target.value);
            loadReport(e.target.value);
          }}
          className="px-3 py-1.5 rounded bg-monochrome-900 border border-monochrome-800 text-xs font-mono text-monochrome-200 focus:outline-none focus:border-cyan-400"
        >
          {investigations.map((inv) => (
            <option key={inv.slick_id} value={inv.slick_id}>
              {inv.name} ({inv.slick_id.slice(0, 8)})
            </option>
          ))}
          {investigations.length === 0 && (
            <option value="default">No investigations found</option>
          )}
        </select>
        {generating && (
          <span className="text-xs font-mono text-cyan-400 animate-pulse">
            Synthesizing evidentiary report...
          </span>
        )}
      </div>

      {/* Printable Legal Dossier Document */}
      {report && (
        <div
          id="legal-dossier"
          className="p-8 sm:p-12 rounded-2xl border border-monochrome-800/80 bg-monochrome-950/90 space-y-10 shadow-2xl relative overflow-hidden"
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[120px] font-display font-black text-monochrome-900/10 pointer-events-none select-none tracking-widest uppercase">
            MARINEX LEGAL
          </div>

          {/* Dossier Header */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-monochrome-800/80 pb-6 gap-4">
            <div className="space-y-1">
              <div className="text-[10px] font-mono tracking-widest text-monochrome-400 uppercase">
                MARITIME INCIDENT SPILL ATTRIBUTION DOSSIER
              </div>
              <h2 className="text-2xl font-display font-bold text-monochrome-100">
                Incident {report.incident_id}
              </h2>
              <div className="text-xs font-mono text-monochrome-500">
                Document Reference: {report.report_id}
              </div>
            </div>

            <div className="text-right space-y-1">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-rose-950/40 border border-rose-800/60 text-rose-400 text-xs font-mono font-bold uppercase">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>PRIORITY {report.priority_level}</span>
              </div>
              <div className="text-[11px] font-mono text-monochrome-500">
                Generated: {new Date(report.generated_at).toUTCString()}
              </div>
              <div className="text-[11px] font-mono text-monochrome-500">
                Analyst: {report.analyst}
              </div>
            </div>
          </div>

          {/* Executive Summary */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>Executive Summary</span>
            </div>
            <p className="text-sm font-heading text-monochrome-300 leading-relaxed font-light">
              {report.executive_summary}
            </p>
          </div>

          {/* Suspect Vessel & Slick */}
          {suspectVessel && (
            <div className="p-6 rounded-xl bg-monochrome-900/60 border border-monochrome-800/60 grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <span className="text-[10px] font-mono uppercase text-monochrome-500">PRIMARY SUSPECT VESSEL</span>
                <div className="text-xl font-heading font-bold text-monochrome-100 flex items-center gap-2">
                  <Anchor className="w-5 h-5 text-rose-400" />
                  {suspectVessel.vessel?.vessel_name || 'Unknown'}
                </div>
                <div className="text-xs font-mono text-monochrome-400">
                  MMSI: {suspectVessel.vessel?.mmsi} | IMO: {suspectVessel.vessel?.imo || 'N/A'}
                </div>
                <div className="text-xs font-mono text-monochrome-500">
                  Flag: {suspectVessel.vessel?.flag || 'Unknown'} • {suspectVessel.vessel?.vessel_type || 'Unknown'}
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[10px] font-mono uppercase text-monochrome-500">SPATIO-TEMPORAL INTERCEPT</span>
                <div className="text-xl font-heading font-bold text-monochrome-100">
                  {suspectVessel.metrics?.closest_distance_km?.toFixed(2) ?? 'N/A'} km
                </div>
                <div className="text-xs font-mono text-monochrome-400">
                  Time Delta: {suspectVessel.metrics?.time_delta_minutes ?? 'N/A'} min
                </div>
                <div className="text-xs font-mono text-monochrome-500">
                  Transit Speed: {suspectVessel.metrics?.transit_speed_knots?.toFixed(1) ?? 'N/A'} kts
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[10px] font-mono uppercase text-monochrome-500">ATTRIBUTION SCORE</span>
                <div className="text-3xl font-display font-extrabold text-cyan-400">
                  {Math.round(suspectVessel.overall_score || 0)}%
                </div>
                <div className="text-xs font-mono text-emerald-400 flex items-center gap-1">
                  <FileCheck className="w-3.5 h-3.5" />
                  <span>Confidence: {suspectVessel.confidence}</span>
                </div>
              </div>
            </div>
          )}

          {/* Observed Facts */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
              <MapPin className="w-4 h-4 text-cyan-400" />
              <span>Observed Facts</span>
            </div>
            <ul className="space-y-2 text-xs font-mono text-monochrome-300">
              {report.observed_facts.map((f, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-cyan-400">▸</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Model Predictions & Drift Analysis */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
                <Wind className="w-4 h-4 text-cyan-400" />
                <span>Model Predictions</span>
              </div>
              <ul className="space-y-2 text-xs font-mono text-monochrome-300">
                {report.model_predictions.map((m, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-cyan-400">▸</span>
                    <span>{m}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Assumptions & Limitations</span>
              </div>
              <ul className="space-y-2 text-xs font-mono text-monochrome-300">
                {report.assumptions_and_limitations.map((a, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-amber-400">▸</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Drift Analysis */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <span>Hydrodynamic Hindcast Parameters</span>
            </div>
            <div className="p-5 rounded-lg bg-monochrome-900/40 border border-monochrome-800/40 space-y-3 text-xs font-mono">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <span className="text-monochrome-500 block text-[10px]">MODEL</span>
                  <span className="text-monochrome-200">{report.drift_analysis?.model_name || 'LAGRANGIAN_MONTE_CARLO_DRIFT_v1'}</span>
                </div>
                <div>
                  <span className="text-monochrome-500 block text-[10px]">DIRECTION</span>
                  <span className="text-monochrome-200">{report.drift_analysis?.direction || 'HINDCAST'}</span>
                </div>
                <div>
                  <span className="text-monochrome-500 block text-[10px]">DURATION</span>
                  <span className="text-monochrome-200">
                    {report.drift_analysis?.parameters?.duration_hours ?? '6'} hrs
                  </span>
                </div>
                <div>
                  <span className="text-monochrome-500 block text-[10px]">WIND DRIFT FACTOR</span>
                  <span className="text-monochrome-200">
                    {Math.round((report.drift_analysis?.parameters?.wind_drift_factor ?? 0.032) * 100)}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Recommended Actions */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
              <Ship className="w-4 h-4 text-cyan-400" />
              <span>Recommended Actions</span>
            </div>
            <ul className="space-y-2 text-xs font-mono text-monochrome-300">
              {report.recommended_actions.map((r, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-cyan-400">{(i + 1).toString().padStart(2, '0')}.</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal Disclaimer & Chain of Custody */}
          <div className="space-y-4 pt-4 border-t border-monochrome-800/80">
            <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider">
              <Fingerprint className="w-4 h-4 text-cyan-400" />
              <span>Admissibility Guarantee</span>
            </div>
            <div className="p-4 rounded-lg bg-monochrome-900/30 border border-monochrome-800/30 text-[11px] font-mono text-monochrome-400 leading-relaxed">
              {report.legal_disclaimer}
            </div>
          </div>
        </div>
      )}

      {!report && !generating && investigations.length > 0 && (
        <div className="p-8 text-center text-xs font-mono text-monochrome-500 bg-monochrome-950/40 rounded-xl border border-monochrome-800">
          Report unavailable. Select a case above or re-run generation.
        </div>
      )}
    </div>
  );
};