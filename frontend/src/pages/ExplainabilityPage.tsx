import React, { useEffect, useState } from 'react';
import { Eye, AlertTriangle, CheckCircle, Zap, FlaskConical } from 'lucide-react';
import { MarineXApi } from '../services/api';

const VerdictBadge: React.FC<{ verdict: string }> = ({ verdict }) => {
  const v = (verdict || '').toUpperCase();
  if (v === 'PASS' || v === 'STRONG') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 text-[10px] font-mono font-bold uppercase">
        <CheckCircle className="w-3 h-3" />
        {verdict}
      </span>
    );
  }
  if (v === 'WEAK') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800/60 text-amber-400 text-[10px] font-mono font-bold uppercase">
        <AlertTriangle className="w-3 h-3" />
        {verdict}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-monochrome-900/60 border border-monochrome-800/60 text-monochrome-400 text-[10px] font-mono font-bold uppercase">
      {verdict || 'UNKNOWN'}
    </span>
  );
};

const isSafeScalar = (v: any): boolean => {
  if (typeof v === 'number') return true;
  if (typeof v === 'string' && v.length < 120) return true;
  return false;
};

export const ExplainabilityPage: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const result = await MarineXApi.getExplainabilityValidation();
        setData(result);
      } catch (err: any) {
        setError(err?.message || 'Failed to load explainability data');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <span className="text-xs font-mono text-monochrome-500 animate-pulse">
          Loading explainability validation...
        </span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 rounded-xl border border-rose-800/60 bg-rose-950/20 text-xs font-mono text-rose-400">
        {error || 'No data available'}
      </div>
    );
  }

  const sanity = data.sanity || {};
  const examples = data.examples || [];
  const energyBefore = sanity.energy_before || {};
  const energyAfter = sanity.energy_after || {};

  return (
    <div className="space-y-12">
      {/* Editorial Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-8 border-b border-monochrome-800/80">
        <div className="space-y-3">
          <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
            ATTRIBUTION VALIDATION
          </span>
          <h1 className="text-4xl sm:text-6xl font-display font-extrabold tracking-tighter text-monochrome-50">
            Explainability Validation
          </h1>
          <p className="text-sm sm:text-base font-heading text-monochrome-400 font-light max-w-3xl">
            Sanity checks and example attributions for the production segmentation model.
            Verifies that saliency maps are non-trivial and degrade meaningfully under controlled perturbations.
          </p>
        </div>
      </div>

      {/* Sanity Panel */}
      <div className="p-6 sm:p-8 rounded-2xl border border-monochrome-800/80 bg-monochrome-950/90 space-y-6 shadow-2xl">
        <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
          <FlaskConical className="w-4 h-4 text-cyan-400" />
          <span>Sanity Checks</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* Randomization Test */}
          <div className="p-5 rounded-xl bg-monochrome-900/60 border border-monochrome-800/60 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500">
                Randomization Test
              </span>
              <VerdictBadge verdict={sanity.randomization_test?.result || sanity.randomization_test || ''} />
            </div>
            <p className="text-[11px] font-mono text-monochrome-400 leading-relaxed">
              When model weights are randomized, the attribution map should lose structure. A <strong className="text-monochrome-200">WEAK</strong> verdict
              means the map degraded as expected; <strong className="text-monochrome-200">PASS</strong> or <strong className="text-monochrome-200">STRONG</strong> indicates the
              map still carried signal despite randomization — a potential concern.
            </p>
          </div>

          {/* Perturbation Test */}
          <div className="p-5 rounded-xl bg-monochrome-900/60 border border-monochrome-800/60 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500">
                Perturbation Test
              </span>
              <VerdictBadge verdict={sanity.perturbation_test?.result || sanity.perturbation_test || ''} />
            </div>
            <p className="text-[11px] font-mono text-monochrome-400 leading-relaxed">
              Masking high-attribution pixels should reduce model confidence. A <strong className="text-monochrome-200">PASS</strong> verdict
              confirms the attribution map identifies pixels the model genuinely relies upon.
            </p>
          </div>
        </div>

        {/* Energy Before / After */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="p-5 rounded-xl bg-monochrome-900/40 border border-monochrome-800/40 space-y-2">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500">
              Energy Before Randomization
            </span>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(energyBefore).map(([k, v]) =>
                isSafeScalar(v) ? (
                  <div key={k} className="text-xs font-mono">
                    <span className="text-monochrome-500 block">{k.toUpperCase()}</span>
                    <span className="text-monochrome-100 font-bold">{typeof v === 'number' ? v.toFixed(6) : String(v)}</span>
                  </div>
                ) : null
              )}
              {Object.keys(energyBefore).length === 0 && (
                <span className="text-xs font-mono text-monochrome-500">No data</span>
              )}
            </div>
          </div>

          <div className="p-5 rounded-xl bg-monochrome-900/40 border border-monochrome-800/40 space-y-2">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500">
              Energy After Randomization
            </span>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(energyAfter).map(([k, v]) =>
                isSafeScalar(v) ? (
                  <div key={k} className="text-xs font-mono">
                    <span className="text-monochrome-500 block">{k.toUpperCase()}</span>
                    <span className="text-monochrome-100 font-bold">{typeof v === 'number' ? v.toFixed(6) : String(v)}</span>
                  </div>
                ) : null
              )}
              {Object.keys(energyAfter).length === 0 && (
                <span className="text-xs font-mono text-monochrome-500">No data</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Examples Panel */}
      {examples.length > 0 && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
            <Eye className="w-4 h-4 text-cyan-400" />
            <span>Attribution Examples</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {examples.map((ex: any, i: number) => (
              <div
                key={i}
                className="p-6 rounded-xl border border-monochrome-800/60 bg-monochrome-950/60 space-y-4"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-monochrome-200">
                    Run {ex.run_id || ex.id || `#${i + 1}`}
                  </span>
                  {ex.prediction_confidence != null && (
                    <span className="text-[10px] font-mono text-cyan-400">
                      Confidence: {(ex.prediction_confidence * 100).toFixed(1)}%
                    </span>
                  )}
                </div>

                {ex.method && (
                  <div className="flex flex-wrap gap-1.5">
                    {(Array.isArray(ex.method) ? ex.method : [ex.method]).map((m: string, j: number) => (
                      <span
                        key={j}
                        className="px-2 py-0.5 rounded bg-monochrome-900 border border-monochrome-800 text-[10px] font-mono text-monochrome-300"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                )}

                {ex.value && typeof ex.value === 'object' && (
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    {Object.entries(ex.value).map(([k, v]) =>
                      isSafeScalar(v) ? (
                        <div key={k}>
                          <span className="text-monochrome-500 block text-[10px]">{k.toUpperCase()}</span>
                          <span className="text-monochrome-200 font-bold">
                            {typeof v === 'number' ? v.toFixed(6) : String(v)}
                          </span>
                        </div>
                      ) : null
                    )}
                  </div>
                )}

                {ex.report_path && (
                  <div className="text-[10px] font-mono text-monochrome-500 truncate">
                    Report: {ex.report_path}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Honesty Footer */}
      <div className="pt-6 border-t border-monochrome-800/80">
        <p className="text-[11px] font-mono text-monochrome-500 italic max-w-3xl">
          Attribution maps indicate where the model looked; they confer no causal claim.
        </p>
      </div>
    </div>
  );
};
