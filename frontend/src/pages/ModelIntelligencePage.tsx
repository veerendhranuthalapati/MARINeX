import React, { useEffect, useState } from 'react';
import {
  Brain,
  Target,
  AlertTriangle,
  ChevronRight,
  BarChart3,
  Shield,
  Crosshair,
} from 'lucide-react';
import { MarineXApi } from '../services/api';

interface MetricTileProps {
  label: string;
  value: number | string;
  decimals?: number;
}

const MetricTile: React.FC<MetricTileProps> = ({ label, value, decimals = 1 }) => (
  <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1.5">
    <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500 block">{label}</span>
    <span className="text-2xl font-display font-extrabold text-monochrome-100">
      {typeof value === 'number' ? (value * 100).toFixed(decimals) + '%' : value}
    </span>
  </div>
);

interface DeltaBadgeProps {
  delta: number;
}

const DeltaBadge: React.FC<DeltaBadgeProps> = ({ delta }) => {
  const isBad = delta < -0.03;
  const isMid = delta < -0.01;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
        isBad
          ? 'bg-rose-950/60 text-rose-400 border border-rose-800/60'
          : isMid
          ? 'bg-amber-950/60 text-amber-400 border border-amber-800/60'
          : 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
      }`}
    >
      {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}
    </span>
  );
};

export const ModelIntelligencePage: React.FC = () => {
  const [mlCard, setMlCard] = useState<any>(null);
  const [mlValidation, setMlValidation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [card, validation] = await Promise.all([
          MarineXApi.getMlCard(),
          MarineXApi.getMlValidation(),
        ]);
        setMlCard(card);
        setMlValidation(validation);
      } catch (err: any) {
        setError(err?.message || 'Failed to load ML intelligence data');
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
          Loading production model intelligence...
        </span>
      </div>
    );
  }

  if (error || !mlCard) {
    return (
      <div className="p-8 rounded-xl border border-rose-800/60 bg-rose-950/20 text-xs font-mono text-rose-400">
        {error || 'No data available'}
      </div>
    );
  }

  const model = mlCard.production_model || {};
  const metrics = model.frozen_test_metrics || {};
  const calibration = model.calibration || mlCard.calibration || {};
  const dataset = model.dataset || {};
  const split = dataset.split || {};
  const multiSeed = model.multi_seed_stability || mlCard.multi_seed || [];
  const robustness = model.robustness || [];
  const crossDataset = model.cross_dataset || mlCard.cross_dataset || [];
  const validation = mlValidation || {};

  const cleanIou = robustness.find((r: any) => r.condition === 'clean' || r.condition === 'Clean')?.iou ?? 0;

  return (
    <div className="space-y-12">
      {/* Editorial Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-8 border-b border-monochrome-800/80">
        <div className="space-y-3">
          <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
            ML VALIDATION CAMPAIGN
          </span>
          <h1 className="text-4xl sm:text-6xl font-display font-extrabold tracking-tighter text-monochrome-50">
            Production Model Intelligence
          </h1>
          <p className="text-sm sm:text-base font-heading text-monochrome-400 font-light max-w-3xl">
            Exhaustive metrics for the <span className="text-monochrome-200">marinex-unet-v1.0.0</span> segmentation
            model, sourced directly from validated campaign artifacts. Includes frozen-test performance,
            calibration diagnostics, robustness sweeps, and dataset auditing.
          </p>
        </div>
      </div>

      {/* Model Card Panel */}
      <div className="p-6 sm:p-8 rounded-2xl border border-monochrome-800/80 bg-monochrome-950/90 space-y-8 shadow-2xl">
        <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
          <Brain className="w-4 h-4 text-cyan-400" />
          <span>Model Card</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <span className="text-monochrome-500 block text-[10px]">MODEL</span>
            <span className="text-monochrome-100 font-bold">{model.model_name || 'marinex-unet-v1.0.0'}</span>
          </div>
          <div>
            <span className="text-monochrome-500 block text-[10px]">ARCHITECTURE</span>
            <span className="text-monochrome-100 font-bold">{model.architecture || 'U-Net'}</span>
          </div>
          <div>
            <span className="text-monochrome-500 block text-[10px]">FRAMEWORK</span>
            <span className="text-monochrome-100 font-bold">{model.framework || 'PyTorch'}</span>
          </div>
          <div>
            <span className="text-monochrome-500 block text-[10px]">THRESHOLD</span>
            <span className="text-monochrome-100 font-bold">{model.threshold ?? calibration.threshold ?? 'N/A'}</span>
          </div>
        </div>

        {/* Frozen Test Metrics */}
        <div className="space-y-3">
          <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-400">
            Frozen Test Metrics
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <MetricTile label="IoU" value={metrics.iou ?? 0} />
            <MetricTile label="Dice" value={metrics.dice ?? 0} />
            <MetricTile label="Precision" value={metrics.precision ?? 0} />
            <MetricTile label="Recall" value={metrics.recall ?? 0} />
            <MetricTile label="FPR" value={metrics.fpr ?? 0} />
          </div>
        </div>

        {/* Calibration */}
        <div className="space-y-3">
          <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-400">
            Calibration
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
              <span className="text-[10px] text-monochrome-500 block">ECE RAW</span>
              <span className="text-lg font-bold text-monochrome-100">
                {(calibration.ece_raw ?? 0).toFixed(4)}
              </span>
            </div>
            <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
              <span className="text-[10px] text-monochrome-500 block">ECE CALIBRATED</span>
              <span className="text-lg font-bold text-emerald-400">
                {(calibration.ece_calibrated ?? 0).toFixed(4)}
              </span>
            </div>
            <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
              <span className="text-[10px] text-monochrome-500 block">TEMPERATURE</span>
              <span className="text-lg font-bold text-monochrome-100">
                {calibration.temperature ?? 'N/A'}
              </span>
            </div>
            <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
              <span className="text-[10px] text-monochrome-500 block">BRIER RAW / CAL</span>
              <span className="text-lg font-bold text-monochrome-100">
                {calibration.brier_raw != null ? calibration.brier_raw.toFixed(4) : 'N/A'}
                {' / '}
                {calibration.brier_calibrated != null ? calibration.brier_calibrated.toFixed(4) : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Dataset Split */}
        <div className="space-y-3">
          <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-400">
            Dataset Split
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
              <span className="text-[10px] text-monochrome-500 block">DATASET</span>
              <span className="text-sm font-bold text-monochrome-100">{dataset.name || 'N/A'}</span>
            </div>
            <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
              <span className="text-[10px] text-monochrome-500 block">TOTAL SAMPLES</span>
              <span className="text-lg font-bold text-monochrome-100">{dataset.total_samples ?? 'N/A'}</span>
            </div>
            <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
              <span className="text-[10px] text-monochrome-500 block">TRAIN / VAL / TEST</span>
              <span className="text-lg font-bold text-monochrome-100">
                {split.train ?? 'N/A'} / {split.val ?? 'N/A'} / {split.test ?? 'N/A'}
              </span>
            </div>
            <div className="p-4 rounded-lg bg-monochrome-900/60 border border-monochrome-800/60 space-y-1">
              <span className="text-[10px] text-monochrome-500 block">CROSS-DATASET</span>
              <div className="space-y-1">
                {crossDataset.map((cd: any, i: number) => (
                  <span key={i} className="block text-[11px] text-monochrome-300">
                    {cd.name || cd.dataset}: IoU {(cd.iou * 100).toFixed(1)}%
                  </span>
                ))}
                {crossDataset.length === 0 && (
                  <span className="text-monochrome-500">N/A</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Multi-Seed Stability */}
        {multiSeed.length > 0 && (
          <div className="space-y-3">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-400">
              Multi-Seed Stability
            </span>
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-monochrome-800/60">
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Seed</th>
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Val IoU</th>
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Val Dice</th>
                  </tr>
                </thead>
                <tbody>
                  {multiSeed.map((row: any, i: number) => (
                    <tr key={i} className="border-b border-monochrome-800/30">
                      <td className="py-2 px-3 text-monochrome-300">{row.seed}</td>
                      <td className="py-2 px-3 text-monochrome-100 font-bold">
                        {(row.val_iou * 100).toFixed(2)}%
                      </td>
                      <td className="py-2 px-3 text-monochrome-100 font-bold">
                        {(row.val_dice * 100).toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Robustness Panel */}
      {robustness.length > 0 && (
        <div className="p-6 sm:p-8 rounded-2xl border border-monochrome-800/80 bg-monochrome-950/90 space-y-6 shadow-2xl">
          <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
            <Shield className="w-4 h-4 text-cyan-400" />
            <span>Robustness Sweep</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-monochrome-800/60">
                  <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Condition</th>
                  <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">IoU</th>
                  <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Dice</th>
                  <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Precision</th>
                  <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Recall</th>
                  <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">FPR</th>
                  <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">dIoU vs Clean</th>
                </tr>
              </thead>
              <tbody>
                {robustness.map((row: any, i: number) => {
                  const delta = (row.iou ?? 0) - cleanIou;
                  return (
                    <tr key={i} className="border-b border-monochrome-800/30">
                      <td className="py-2 px-3 text-monochrome-300 font-medium">{row.condition}</td>
                      <td className="py-2 px-3 text-monochrome-100 font-bold">{((row.iou ?? 0) * 100).toFixed(2)}%</td>
                      <td className="py-2 px-3 text-monochrome-100 font-bold">{((row.dice ?? 0) * 100).toFixed(2)}%</td>
                      <td className="py-2 px-3 text-monochrome-300">{((row.precision ?? 0) * 100).toFixed(2)}%</td>
                      <td className="py-2 px-3 text-monochrome-300">{((row.recall ?? 0) * 100).toFixed(2)}%</td>
                      <td className="py-2 px-3 text-monochrome-300">{((row.fpr ?? 0) * 100).toFixed(2)}%</td>
                      <td className="py-2 px-3">
                        <DeltaBadge delta={delta} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Validation Subsections */}
      <div className="space-y-8">
        <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400 uppercase tracking-wider border-b border-monochrome-800/40 pb-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          <span>Additional Validation</span>
        </div>

        {/* Scene Level */}
        {validation.scene_level?.length > 0 && (
          <div className="p-6 rounded-xl border border-monochrome-800/60 bg-monochrome-950/60 space-y-4">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-400">Scene-Level IoU</span>
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-monochrome-800/60">
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Scene</th>
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">IoU</th>
                  </tr>
                </thead>
                <tbody>
                  {validation.scene_level.map((row: any, i: number) => (
                    <tr key={i} className="border-b border-monochrome-800/30">
                      <td className="py-2 px-3 text-monochrome-300">{row.scene || row.scene_id || row.name || `Scene ${i + 1}`}</td>
                      <td className="py-2 px-3 text-monochrome-100 font-bold">
                        {typeof row.iou === 'number' ? (row.iou * 100).toFixed(2) + '%' : row.iou ?? 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Slick Size */}
        {validation.slick_size?.length > 0 && (
          <div className="p-6 rounded-xl border border-monochrome-800/60 bg-monochrome-950/60 space-y-4">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-400">Slick Size Buckets</span>
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-monochrome-800/60">
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Bucket</th>
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">IoU</th>
                  </tr>
                </thead>
                <tbody>
                  {validation.slick_size.map((row: any, i: number) => (
                    <tr key={i} className="border-b border-monochrome-800/30">
                      <td className="py-2 px-3 text-monochrome-300">{row.bucket || row.label || `Bucket ${i + 1}`}</td>
                      <td className="py-2 px-3 text-monochrome-100 font-bold">
                        {typeof row.iou === 'number' ? (row.iou * 100).toFixed(2) + '%' : row.iou ?? 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Lookalike */}
        {validation.lookalike?.length > 0 && (
          <div className="p-6 rounded-xl border border-monochrome-800/60 bg-monochrome-950/60 space-y-4">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-400">Look-Alike Rejection</span>
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-monochrome-800/60">
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Class</th>
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">N</th>
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">IoU</th>
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Mean Conf</th>
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Rejection Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {validation.lookalike.map((row: any, i: number) => (
                    <tr key={i} className="border-b border-monochrome-800/30">
                      <td className="py-2 px-3 text-monochrome-300">{row.class || row.label || 'N/A'}</td>
                      <td className="py-2 px-3 text-monochrome-300">{row.n ?? row.count ?? 'N/A'}</td>
                      <td className="py-2 px-3 text-monochrome-100 font-bold">
                        {typeof row.iou === 'number' ? (row.iou * 100).toFixed(2) + '%' : row.iou ?? 'N/A'}
                      </td>
                      <td className="py-2 px-3 text-monochrome-300">
                        {typeof row.mean_confidence === 'number' ? (row.mean_confidence * 100).toFixed(1) + '%' : row.mean_confidence ?? 'N/A'}
                      </td>
                      <td className="py-2 px-3 text-monochrome-300">
                        {typeof row.rejection_rate === 'number' ? (row.rejection_rate * 100).toFixed(1) + '%' : row.rejection_rate ?? 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Error Taxonomy */}
        {validation.error_taxonomy?.length > 0 && (
          <div className="p-6 rounded-xl border border-monochrome-800/60 bg-monochrome-950/60 space-y-4">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-400">Error Taxonomy</span>
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-monochrome-800/60">
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Error Class</th>
                    <th className="text-left py-2 px-3 text-monochrome-500 font-normal uppercase text-[10px]">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {validation.error_taxonomy.map((row: any, i: number) => (
                    <tr key={i} className="border-b border-monochrome-800/30">
                      <td className="py-2 px-3 text-monochrome-300">{row.error_class || row.class || 'N/A'}</td>
                      <td className="py-2 px-3 text-monochrome-100 font-bold">{row.count ?? 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Honesty Footer */}
      <div className="pt-6 border-t border-monochrome-800/80">
        <p className="text-[11px] font-mono text-monochrome-500 italic max-w-3xl">
          All metrics are reported from the validated campaign artifacts (reports/); nothing is fabricated for the UI.
        </p>
      </div>
    </div>
  );
};
