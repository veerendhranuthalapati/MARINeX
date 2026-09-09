import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { MarineXApi } from '../services/api';
import { SatelliteScene, OilSlick, DetectionRunResult } from '../types';
import { CategoryBadge } from '../components/investigation/CategoryBadge';
import { ComparisonSlider } from '../components/investigation/ComparisonSlider';
import {
  Scan,
  Cpu,
  Sliders,
  Play,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Droplet,
  Maximize2,
  Zap,
  ArrowUpRight,
} from 'lucide-react';

export const DetectionPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [scenes, setScenes] = useState<SatelliteScene[]>([]);
  const [selectedSceneId, setSelectedSceneId] = useState<string>('');
  const [detectorType, setDetectorType] = useState<string>('segformer');
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.35);
  const [detecting, setDetecting] = useState<boolean>(false);
  const [detectionResult, setDetectionResult] = useState<DetectionRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadScenes();
  }, []);

  const loadScenes = async () => {
    try {
      const data = await MarineXApi.getScenes();
      setScenes(data);
      const querySceneId = searchParams.get('sceneId');
      if (querySceneId && data.find((s) => s.id === querySceneId)) {
        setSelectedSceneId(querySceneId);
      } else if (data.length > 0) {
        setSelectedSceneId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load scenes:', err);
    }
  };

  const handleRunDetection = async () => {
    if (!selectedSceneId) return;
    setDetecting(true);
    setError(null);
    try {
      const result = await MarineXApi.runDetection(
        selectedSceneId,
        detectorType,
        confidenceThreshold
      );
      setDetectionResult(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setDetecting(false);
    }
  };

  const selectedScene = scenes.find((s) => s.id === selectedSceneId);

  return (
    <div className="space-y-12">
      {/* Editorial Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-8 border-b border-monochrome-800/80">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
              SEGMENTATION BENCHMARK & INFERENCE
            </span>
            <CategoryBadge category="INFERRED" size="xs" />
          </div>

          <h1 className="text-4xl sm:text-6xl font-display font-extrabold tracking-tighter text-monochrome-50">
            SAR Oil Slick Segmentation
          </h1>

          <p className="text-sm sm:text-base font-heading text-monochrome-400 font-light max-w-3xl">
            Execute pixel-level neural inference on calibrated Sentinel-1 C-band Synthetic Aperture Radar scenes to identify damped oil slicks while discriminating low-wind look-alikes.
          </p>
        </div>

        <button
          onClick={handleRunDetection}
          disabled={detecting || !selectedSceneId}
          className="inline-flex items-center gap-2.5 px-6 py-3 rounded bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 text-xs font-heading font-bold uppercase tracking-wider transition-all disabled:opacity-50 cursor-pointer shrink-0"
        >
          <Play className={`w-3.5 h-3.5 fill-current ${detecting ? 'animate-pulse' : ''}`} />
          <span>{detecting ? 'Segmenting Scene...' : 'Run Segmentation'}</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Two Column Layout: Controls on Left, Visual Comparator on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Model & Scene Selector (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/60 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-monochrome-900">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-monochrome-300">
                Inference Configuration
              </span>
              <span className="text-[10px] font-mono text-cyan-400">SENTINEL-1 C-BAND</span>
            </div>

            {/* Target Scene Selector */}
            <div className="space-y-2">
              <label className="text-[11px] font-mono uppercase text-monochrome-400 block">
                Target SAR Swath
              </label>
              <select
                value={selectedSceneId}
                onChange={(e) => setSelectedSceneId(e.target.value)}
                className="w-full px-3 py-2 rounded bg-monochrome-900 border border-monochrome-800 text-xs font-mono text-monochrome-200 focus:outline-none focus:border-cyan-400"
              >
                {scenes.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.source} — {s.id.split('_').pop()}
                  </option>
                ))}
              </select>
            </div>

            {/* Model Architecture Selector */}
            <div className="space-y-2">
              <label className="text-[11px] font-mono uppercase text-monochrome-400 block">
                Neural Architecture
              </label>
              <div className="space-y-2">
                {[
                  {
                    id: 'segformer',
                    name: 'SegFormer (Hierarchical Transformer)',
                    detail: 'MiT-B0 Encoder • IoU 0.8940 • Dice 0.9440',
                    badge: 'PRIMARY',
                  },
                  {
                    id: 'unetpp',
                    name: 'U-Net++ (Nested Dense Skips)',
                    detail: 'ResNet34 Backbone • IoU 0.9340 • Dice 0.9659',
                    badge: 'ADVANCED',
                  },
                  {
                    id: 'unet',
                    name: 'U-Net Baseline (BCE+Dice)',
                    detail: 'Standard ConvNet • IoU 0.9476 • Dice 0.9731',
                    badge: 'BASELINE',
                  },
                  {
                    id: 'classical',
                    name: 'Adaptive Otsu + Dark Spot Filter',
                    detail: 'Classical Vision • IoU 0.3652 • False Alarm 63%',
                    badge: 'LEGACY',
                  },
                ].map((m) => (
                  <div
                    key={m.id}
                    onClick={() => setDetectorType(m.id)}
                    className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                      detectorType === m.id
                        ? 'border-cyan-500/50 bg-cyan-950/20 text-monochrome-100'
                        : 'border-monochrome-850 bg-monochrome-900/30 text-monochrome-400 hover:border-monochrome-700'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs font-heading font-medium">
                      <span>{m.name}</span>
                      <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-monochrome-800 text-monochrome-300">
                        {m.badge}
                      </span>
                    </div>
                    <p className="text-[10px] font-mono text-monochrome-500 mt-1">{m.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Probability Threshold Slider */}
            <div className="space-y-2 pt-2 border-t border-monochrome-900">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-monochrome-400">Calibrated Decision Threshold</span>
                <span className="text-cyan-400 font-bold">{confidenceThreshold.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.90"
                step="0.05"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-monochrome-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              />
              <span className="text-[10px] font-mono text-monochrome-500 block">
                Empirical optimal F1 threshold: 0.35 (ECE: 0.042)
              </span>
            </div>
          </div>

          {/* Quick Scene Telemetry Card */}
          {selectedScene && (
            <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/60 space-y-4 font-mono text-xs">
              <span className="text-[10px] text-monochrome-500 uppercase block tracking-wider">
                Scene Telemetry
              </span>
              <div className="space-y-2">
                <div className="flex justify-between py-1 border-b border-monochrome-900">
                  <span className="text-monochrome-500">Acquisition Time</span>
                  <span className="text-monochrome-200">{new Date(selectedScene.acquisition_time).toUTCString()}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-monochrome-900">
                  <span className="text-monochrome-500">Ground Resolution</span>
                  <span className="text-monochrome-200">{selectedScene.resolution}m per pixel</span>
                </div>
                <div className="flex justify-between py-1 border-b border-monochrome-900">
                  <span className="text-monochrome-500">Coverage Sector</span>
                  <span className="text-monochrome-200">{selectedScene.id}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-monochrome-500">Calibration</span>
                  <span className="text-monochrome-200">Sigma0 Radiometric dB</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Comparison Visualizer (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/50 space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-monochrome-900">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500 block mb-0.5">
                  VISUAL GROUND TRUTH COMPARATOR
                </span>
                <h3 className="text-lg font-heading font-bold text-monochrome-100">
                  Sentinel-1 SAR vs. Neural Slick Segmentation
                </h3>
              </div>
              <span className="text-xs font-mono text-cyan-400">
                {detectionResult ? `${detectionResult.slicks_detected} slicks segmented` : 'Interactive Slider'}
              </span>
            </div>

            {/* Visual Comparison Slider */}
            <div className="relative rounded-xl overflow-hidden border border-monochrome-800/80 bg-[#070c14] shadow-2xl">
              <ComparisonSlider
                leftImageSrc="/samples/sar_sample.png"
                rightImageSrc="/samples/mask_sample.png"
                leftLabel="Level-1 C-Band SAR (VV)"
                rightLabel="SegFormer Output (Calibrated)"
              />
            </div>
          </div>

          {/* Model Evaluation Metrics Summary Table */}
          <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/60 space-y-4">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-monochrome-300 block pb-2 border-b border-monochrome-900">
              Strict Zero-Leakage Test Set Evaluation
            </span>

            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="text-monochrome-500 border-b border-monochrome-900 text-left">
                    <th className="py-2 pr-4 font-normal">MODEL</th>
                    <th className="py-2 px-3 font-normal">IOU</th>
                    <th className="py-2 px-3 font-normal">DICE</th>
                    <th className="py-2 px-3 font-normal">PRECISION</th>
                    <th className="py-2 px-3 font-normal">RECALL</th>
                    <th className="py-2 pl-3 font-normal">FALSE ALARM</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-monochrome-900">
                  <tr className="text-monochrome-400">
                    <td className="py-2.5 pr-4 text-monochrome-300">Classical Otsu Baseline</td>
                    <td className="py-2.5 px-3">0.3652</td>
                    <td className="py-2.5 px-3">0.5350</td>
                    <td className="py-2.5 px-3">0.3654</td>
                    <td className="py-2.5 px-3">0.9981</td>
                    <td className="py-2.5 pl-3 text-rose-400">63.4%</td>
                  </tr>
                  <tr className="text-monochrome-400">
                    <td className="py-2.5 pr-4 text-monochrome-300">U-Net Baseline (BCE+Dice)</td>
                    <td className="py-2.5 px-3">0.9476</td>
                    <td className="py-2.5 px-3">0.9731</td>
                    <td className="py-2.5 px-3">0.9487</td>
                    <td className="py-2.5 px-3">0.9988</td>
                    <td className="py-2.5 pl-3 text-emerald-400">5.1%</td>
                  </tr>
                  <tr className="text-monochrome-400">
                    <td className="py-2.5 pr-4 text-monochrome-300">U-Net++ (Nested Skips)</td>
                    <td className="py-2.5 px-3">0.9340</td>
                    <td className="py-2.5 px-3">0.9659</td>
                    <td className="py-2.5 px-3">0.9668</td>
                    <td className="py-2.5 px-3">0.9650</td>
                    <td className="py-2.5 pl-3 text-emerald-400">3.3%</td>
                  </tr>
                  <tr className="text-cyan-300 bg-cyan-950/10 font-bold">
                    <td className="py-2.5 pr-4">SegFormer (Primary Model)</td>
                    <td className="py-2.5 px-3">0.8940</td>
                    <td className="py-2.5 px-3">0.9440</td>
                    <td className="py-2.5 px-3">0.9749</td>
                    <td className="py-2.5 px-3">0.9151</td>
                    <td className="py-2.5 pl-3 text-emerald-400">2.5%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
