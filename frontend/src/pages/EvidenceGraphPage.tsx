import React, { useEffect, useState, useCallback } from 'react';
import {
  GitBranch,
  Play,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  MapPin,
  Clock,
  Camera,
  Anchor,
  Ship,
  Wind,
  FileText,
} from 'lucide-react';
import { MarineXApi } from '../services/api';

const TYPE_COLORS: Record<string, { bg: string; border: string; text: string; icon: React.FC<any> }> = {
  DETECTION: { bg: 'bg-cyan-950/40', border: 'border-cyan-800/60', text: 'text-cyan-400', icon: Camera },
  SLICK: { bg: 'bg-rose-950/40', border: 'border-rose-800/60', text: 'text-rose-400', icon: AlertTriangle },
  ENVIRONMENT: { bg: 'bg-emerald-950/40', border: 'border-emerald-800/60', text: 'text-emerald-400', icon: Wind },
  DRIFT: { bg: 'bg-amber-950/40', border: 'border-amber-800/60', text: 'text-amber-400', icon: GitBranch },
  AIS: { bg: 'bg-purple-950/40', border: 'border-purple-800/60', text: 'text-purple-400', icon: Ship },
  CANDIDATE: { bg: 'bg-orange-950/40', border: 'border-orange-800/60', text: 'text-orange-400', icon: Anchor },
  REPORT: { bg: 'bg-monochrome-900/60', border: 'border-monochrome-700/60', text: 'text-monochrome-300', icon: FileText },
};

const STATUS_COLORS: Record<string, string> = {
  OBSERVED: 'bg-cyan-950/60 border-cyan-800/60 text-cyan-400',
  ML_SEGMENTED: 'bg-emerald-950/60 border-emerald-800/60 text-emerald-400',
  INFERRED: 'bg-amber-950/60 border-amber-800/60 text-amber-400',
  SIMULATED: 'bg-purple-950/60 border-purple-800/60 text-purple-400',
  TRACKED: 'bg-blue-950/60 border-blue-800/60 text-blue-400',
  CANDIDATE: 'bg-orange-950/60 border-orange-800/60 text-orange-400',
  DEMO_DATA: 'bg-monochrome-800/60 border-monochrome-700/60 text-monochrome-300',
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const cls = STATUS_COLORS[status] || 'bg-monochrome-900/60 border-monochrome-800/60 text-monochrome-400';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-mono font-bold uppercase ${cls}`}>
      {status}
    </span>
  );
};

export const EvidenceGraphPage: React.FC = () => {
  const [incident, setIncident] = useState<any>(null);
  const [evidenceRecords, setEvidenceRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demoResult, setDemoResult] = useState<any>(null);
  const [runningDemo, setRunningDemo] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const incidents = await MarineXApi.getIncidents();
      const list = Array.isArray(incidents) ? incidents : (incidents as any).incidents ?? [];
      const first = list.length > 0 ? list[0] : null;
      if (!first?.id) {
        setError('No incidents available');
        setLoading(false);
        return;
      }
      const detail = await MarineXApi.getIncidentDetail(first.id);
      setIncident(detail);
      setEvidenceRecords(detail.evidence_records || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load incident data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunDemo = async () => {
    setRunningDemo(true);
    try {
      const result = await MarineXApi.runDemoCase('incident_complete');
      setDemoResult(result);
      await loadData();
    } catch (err: any) {
      setDemoResult({ error: err?.message || 'Demo case failed' });
    } finally {
      setRunningDemo(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <span className="text-xs font-mono text-monochrome-500 animate-pulse">
          Loading evidence graph...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 rounded-xl border border-rose-800/60 bg-rose-950/20 text-xs font-mono text-rose-400">
        {error}
      </div>
    );
  }

  // Group evidence by type
  const grouped: Record<string, any[]> = {};
  evidenceRecords.forEach((rec) => {
    const t = rec.evidence_type || 'UNKNOWN';
    if (!grouped[t]) grouped[t] = [];
    grouped[t].push(rec);
  });

  const typeOrder = ['DETECTION', 'SLICK', 'ENVIRONMENT', 'DRIFT', 'AIS', 'CANDIDATE', 'REPORT'];
  const orderedTypes = typeOrder.filter((t) => grouped[t]?.length > 0);
  const uniqueTypes = Object.keys(grouped).filter((t) => !orderedTypes.includes(t));
  orderedTypes.push(...uniqueTypes);

  const typeCount = Object.keys(grouped).length;

  return (
    <div className="space-y-12">
      {/* Editorial Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-8 border-b border-monochrome-800/80">
        <div className="space-y-3">
          <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
            PROVENANCE CHAIN
          </span>
          <h1 className="text-4xl sm:text-6xl font-display font-extrabold tracking-tighter text-monochrome-50">
            Evidence Graph
          </h1>
          <p className="text-sm sm:text-base font-heading text-monochrome-400 font-light max-w-3xl">
            A chronological provenance chain of every evidence record — detection, segmentation,
            environmental context, drift hindcast, AIS attribution, and candidate ranking —
            linked to the source incident.
          </p>
        </div>
      </div>

      {/* Summary Strip */}
      {incident && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
            <span className="text-[10px] text-monochrome-500 block uppercase">Incident</span>
            <span className="text-sm font-bold text-monochrome-100">{incident.id}</span>
          </div>
          <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
            <span className="text-[10px] text-monochrome-500 block uppercase">Scenes</span>
            <span className="text-lg font-bold text-monochrome-100">
              {incident.scenes?.length ?? incident.scene_count ?? 0}
            </span>
          </div>
          <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
            <span className="text-[10px] text-monochrome-500 block uppercase">Slicks</span>
            <span className="text-lg font-bold text-monochrome-100">
              {incident.slicks?.length ?? incident.slick_count ?? 0}
            </span>
          </div>
          <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
            <span className="text-[10px] text-monochrome-500 block uppercase">Evidence Types</span>
            <span className="text-lg font-bold text-monochrome-100">{typeCount}</span>
          </div>
        </div>
      )}

      {/* Run Demo Control */}
      <div className="flex items-center gap-4 p-4 rounded-xl border border-monochrome-800/80 bg-monochrome-950/50">
        <button
          onClick={handleRunDemo}
          disabled={runningDemo}
          className="inline-flex items-center gap-2 px-4 py-2 rounded bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 text-xs font-heading font-bold uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50"
        >
          {runningDemo ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5" />
          )}
          <span>{runningDemo ? 'Running...' : 'Complete Demo Incident'}</span>
        </button>

        {demoResult && !demoResult.error && (
          <div className="flex items-center gap-3 text-xs font-mono">
            {demoResult.conclusion && (
              <span className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 font-bold">
                {demoResult.conclusion}
              </span>
            )}
            {demoResult.data_quality?.overall && (
              <span className="px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/60 text-cyan-400 font-bold">
                Quality: {demoResult.data_quality.overall}
              </span>
            )}
          </div>
        )}
        {demoResult?.error && (
          <span className="text-xs font-mono text-rose-400">{demoResult.error}</span>
        )}
      </div>

      {/* Evidence Timeline */}
      {orderedTypes.length > 0 && (
        <div className="space-y-0">
          {orderedTypes.map((type, typeIdx) => {
            const records = grouped[type];
            const style = TYPE_COLORS[type] || TYPE_COLORS.REPORT;
            const Icon = style.icon;
            return (
              <div key={type} className="relative">
                {/* Connector line */}
                {typeIdx < orderedTypes.length - 1 && (
                  <div className="absolute left-[19px] top-[40px] bottom-0 w-px bg-monochrome-800/60" />
                )}

                <div className="flex items-start gap-4 pb-8">
                  {/* Node icon */}
                  <div className={`relative z-10 w-10 h-10 rounded-lg ${style.bg} border ${style.border} flex items-center justify-center shrink-0`}>
                    <Icon className={`w-4 h-4 ${style.text}`} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-3">
                      <span className={`text-xs font-mono font-bold uppercase tracking-wider ${style.text}`}>
                        {type}
                      </span>
                      <span className="text-[10px] font-mono text-monochrome-500">
                        {records.length} record{records.length !== 1 ? 's' : ''}
                      </span>
                    </div>

                    <div className="space-y-3">
                      {records.map((rec, ri) => (
                        <div
                          key={ri}
                          className="p-4 rounded-xl border border-monochrome-800/60 bg-monochrome-950/60 space-y-2"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-xs font-mono font-bold text-monochrome-200">{rec.title}</span>
                            <StatusBadge status={rec.status_label || 'UNKNOWN'} />
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px] font-mono">
                            {rec.confidence != null && (
                              <div>
                                <span className="text-monochrome-500 block text-[10px]">CONFIDENCE</span>
                                <span className="text-monochrome-100 font-bold">
                                  {(rec.confidence * 100).toFixed(1)}%
                                </span>
                              </div>
                            )}
                            <div>
                              <span className="text-monochrome-500 block text-[10px]">SOURCE</span>
                              <span className="text-monochrome-300">{rec.source || 'N/A'}</span>
                            </div>
                            {rec.timestamp && (
                              <div>
                                <span className="text-monochrome-500 block text-[10px]">TIMESTAMP</span>
                                <span className="text-monochrome-300">
                                  {new Date(rec.timestamp).toUTCString().slice(0, 25)}
                                </span>
                              </div>
                            )}
                            <div>
                              <span className="text-monochrome-500 block text-[10px]">SUMMARY</span>
                              <span className="text-monochrome-400 line-clamp-2">{rec.summary || 'N/A'}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {evidenceRecords.length === 0 && (
        <div className="p-8 text-center text-xs font-mono text-monochrome-500 bg-monochrome-950/40 rounded-xl border border-monochrome-800">
          No evidence records available for this incident.
        </div>
      )}

      {/* Honesty Footer */}
      <div className="pt-6 border-t border-monochrome-800/80">
        <p className="text-[11px] font-mono text-monochrome-500 italic max-w-3xl">
          This provenance chain is constructed from immutable evidence records stored in the incident ledger.
          Each entry carries its own source, confidence, and temporal metadata — no evidence is fabricated or post-hoc inserted.
        </p>
      </div>
    </div>
  );
};
