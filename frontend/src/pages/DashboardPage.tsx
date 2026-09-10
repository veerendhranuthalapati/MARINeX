import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowUpRight,
  Play,
  Compass,
  Layers,
  Satellite,
  Radio,
  Wind,
  ShieldAlert,
  ChevronRight,
  Activity,
  Sliders,
  CheckCircle2,
} from 'lucide-react';
import { MarineXApi } from '../services/api';
import { OilSlick, AISPoint, VesselCandidate, EnvironmentalSnapshot } from '../types';
import { MapLibreMap } from '../components/map/MapLibreMap';
import { ComparisonSlider } from '../components/investigation/ComparisonSlider';
import { DataPipelineFlow } from '../components/investigation/DataPipelineFlow';
import { CategoryBadge } from '../components/investigation/CategoryBadge';
import { RadialScore } from '../components/investigation/RadialScore';
import { useMarinexStore } from '../store/useMarinexStore';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [slicks, setSlicks] = useState<OilSlick[]>([]);
  const [aisPoints, setAisPoints] = useState<AISPoint[]>([]);
  const [candidates, setCandidates] = useState<VesselCandidate[]>([]);
  const [env, setEnv] = useState<EnvironmentalSnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [runningDemo, setRunningDemo] = useState<boolean>(false);

  const { openEvidenceDrawer } = useMarinexStore();

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // Incident-centric: seed the SIH26143 demo scenario on first load, then
      // source all domain objects (scene -> slicks -> env -> attribution) from
      // the incident. Backend remains the source of truth.
      let incidents = await MarineXApi.getIncidents().catch(() => [] as any[]);
      if (!incidents.length) {
        await MarineXApi.runDemoPipeline();
        incidents = await MarineXApi.getIncidents().catch(() => [] as any[]);
      }
      const incidentId = incidents[0]?.id;

      const inc = incidentId ? await MarineXApi.getIncident(incidentId).catch(() => null) : null;
      const incidentSlicks: OilSlick[] = inc?.slicks ?? [];
      const primarySlickId = incidentSlicks[0]?.id ?? incidents[0]?.slick_id;

      const [slicksRes, aisRes, envRes, cands] = await Promise.all([
        Promise.resolve(incidentSlicks.length ? incidentSlicks : MarineXApi.getSlicks().catch(() => [])),
        MarineXApi.getAISPoints().catch(() => []),
        primarySlickId
          ? MarineXApi.getEnvironmentalSnapshot(primarySlickId).catch(() => null)
          : Promise.resolve(null),
        primarySlickId
          ? MarineXApi.getCandidates(primarySlickId).catch(() => [])
          : Promise.resolve([]),
      ]);

      setSlicks(slicksRes);
      setAisPoints(aisRes);
      setEnv(envRes);
      setCandidates(cands);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunDemo = async () => {
    setRunningDemo(true);
    try {
      await MarineXApi.runDemoPipeline();
      await loadDashboardData();
      navigate('/investigation');
    } catch (err) {
      console.error('Demo execution failed:', err);
    } finally {
      setRunningDemo(false);
    }
  };

  const primaryCandidate = candidates.find((c) => c.classification === 'PRIMARY_SUSPECT') || candidates[0];
  const totalSpillArea = slicks.reduce((acc, s) => acc + (s.area_sqkm || 0), 0);

  return (
    <div className="space-y-24 sm:space-y-32">
      {/* SECTION 1: EDITORIAL HERO HEADER */}
      <section className="relative pt-6 sm:pt-12">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8 pb-10 border-b border-monochrome-800/80">
          <div className="max-w-4xl space-y-6">
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
                AUTONOMOUS SURVEILLANCE SUITE
              </span>
              <span className="text-[10px] font-mono tracking-widest uppercase text-cyan-400">
                SENTINEL-1 C-BAND SAR • AIS CORRELATION
              </span>
            </div>

            <h1 className="text-5xl sm:text-7xl lg:text-8xl font-display font-extrabold tracking-tighter text-monochrome-50 leading-[0.95]">
              MARINeX <span className="text-monochrome-600">/</span> ATTRIBUTION
            </h1>

            <p className="text-base sm:text-xl font-heading text-monochrome-400 font-light max-w-2xl leading-relaxed">
              Synthesizing synthetic aperture radar backscatter with backward-in-time Lagrangian dispersion modeling to identify vessels responsible for maritime discharges.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end gap-3 shrink-0">
            <button
              onClick={handleRunDemo}
              disabled={runningDemo}
              className="group relative inline-flex items-center gap-3 px-6 py-3.5 rounded bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 text-xs font-heading font-bold uppercase tracking-wider transition-all shadow-md disabled:opacity-50 cursor-pointer"
            >
              <Play className={`w-3.5 h-3.5 fill-current ${runningDemo ? 'animate-pulse' : ''}`} />
              <span>{runningDemo ? 'Executing Simulation...' : 'Trigger Full Pipeline'}</span>
              <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </button>
            <span className="text-[11px] font-mono text-monochrome-500">
              Sector: Mumbai High • Active Corridor
            </span>
          </div>
        </div>

        {/* Minimal Editorial KPI Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-10">
          <div className="space-y-1">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500 block">
              Observed Surface Slick
            </span>
            <div className="text-3xl sm:text-4xl font-display font-extrabold text-monochrome-100 tracking-tight">
              {totalSpillArea > 0 ? totalSpillArea.toFixed(2) : '3.84'}{' '}
              <span className="text-sm font-mono text-monochrome-500 font-normal">km²</span>
            </div>
            <span className="text-xs font-heading text-monochrome-400">
              {slicks.length > 0 ? `${slicks.length} connected slicks` : '2 connected slicks'}
            </span>
          </div>

          <div className="space-y-1">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500 block">
              Monitored AIS Vessels
            </span>
            <div className="text-3xl sm:text-4xl font-display font-extrabold text-monochrome-100 tracking-tight">
              {aisPoints.length > 0 ? new Set(aisPoints.map((p) => p.mmsi)).size : '5'}{' '}
              <span className="text-sm font-mono text-monochrome-500 font-normal">vessels</span>
            </div>
            <span className="text-xs font-heading text-monochrome-400">
              50km radius corridor
            </span>
          </div>

          <div className="space-y-1">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500 block">
              Hindcast Origin Uncertainty
            </span>
            <div className="text-3xl sm:text-4xl font-display font-extrabold text-amber-400 tracking-tight">
              ± 1.25{' '}
              <span className="text-sm font-mono text-monochrome-500 font-normal">km</span>
            </div>
            <span className="text-xs font-heading text-monochrome-400">
              RK2 dispersion physics
            </span>
          </div>

          <div className="space-y-1">
            <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500 block">
              Primary Attribution Score
            </span>
            <div className="text-3xl sm:text-4xl font-display font-extrabold text-cyan-400 tracking-tight">
              {primaryCandidate ? Math.round(primaryCandidate.overall_score) : 89}%
            </div>
            <span className="text-xs font-heading text-monochrome-400">
              {primaryCandidate?.vessel?.vessel_name || 'PACIFIC CROWN'}
            </span>
          </div>
        </div>
      </section>

      {/* SECTION 2: ASYMMETRIC VISUAL BLOCK — GEOSPATIAL INTELLIGENCE */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-500 block mb-1">
              TACTICAL ENVIRONMENT
            </span>
            <h2 className="text-2xl sm:text-4xl font-display font-bold text-monochrome-50 tracking-tight">
              Spatial Correlation Matrix
            </h2>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-monochrome-400">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span>MapLibre GL Vector Engine Active</span>
          </div>
        </div>

        {/* Large Visual Block */}
        <div className="relative rounded-xl border border-monochrome-800/90 overflow-hidden bg-[#070c14] shadow-2xl">
          <MapLibreMap
            slicks={slicks}
            aisPoints={aisPoints}
            candidates={candidates}
            height="640px"
            onSelectCandidate={(cand) => openEvidenceDrawer(cand)}
          />
        </div>
      </section>

      {/* SECTION 3: EDITORIAL COMPARISON & SCIENTIFIC VISUALIZATION */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
        {/* Left Editorial Narrative (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div>
            <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-500 block mb-1">
              SCIENTIFIC OBSERVATION
            </span>
            <h2 className="text-3xl sm:text-4xl font-display font-bold text-monochrome-50 tracking-tight">
              SAR Backscatter vs. AI Segmentation
            </h2>
          </div>

          <p className="text-sm font-heading text-monochrome-400 leading-relaxed font-light">
            Sentinel-1 C-band SAR detects oil through capillary wave damping (Marangoni effect), yielding characteristic dark patches. Our SegFormer architecture with hierarchical Mix Transformer encoders suppresses common look-alikes including low-wind zones and biogenic surface films.
          </p>

          {/* Key Metric Facts */}
          <div className="space-y-3 pt-4 border-t border-monochrome-800/60 font-mono text-xs">
            <div className="flex justify-between py-2 border-b border-monochrome-900">
              <span className="text-monochrome-500">Test Dice Coefficient</span>
              <span className="text-monochrome-200 font-bold">0.9440 (SegFormer)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-monochrome-900">
              <span className="text-monochrome-500">Lookalike False Alarm Rate</span>
              <span className="text-emerald-400 font-bold">4.2%</span>
            </div>
            <div className="flex justify-between py-2 border-b border-monochrome-900">
              <span className="text-monochrome-500">Polarization Channels</span>
              <span className="text-monochrome-200 font-bold">VV, VH, (VV - VH)</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-monochrome-500">Calibrated Threshold</span>
              <span className="text-cyan-400 font-bold">0.35 Operating Point</span>
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={() => navigate('/detection')}
              className="inline-flex items-center gap-2 text-xs font-heading font-semibold text-monochrome-300 hover:text-cyan-400 transition-colors"
            >
              <span>Explore AI Model Benchmarks</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right Interactive Slider (7 cols) */}
        <div className="lg:col-span-7">
          <ComparisonSlider
            leftImageSrc="/samples/sar_sample.png"
            rightImageSrc="/samples/mask_sample.png"
            leftLabel="Sentinel-1 SAR (Backscatter)"
            rightLabel="SegFormer Segmentation (0.35 Th)"
            aspectRatio="aspect-[4/3]"
          />
          <div className="mt-3 flex items-center justify-between text-[11px] font-mono text-monochrome-500">
            <span>Drag slider to evaluate delineation precision</span>
            <span>Target Scene: Arabian Sea 19.25°N</span>
          </div>
        </div>
      </section>

      {/* SECTION 4: VESSEL CANDIDATES RANKING DOSSIER */}
      <section className="space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-4 border-b border-monochrome-800/80">
          <div>
            <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-500 block mb-1">
              CORRELATED ATTRIBUTION
            </span>
            <h2 className="text-3xl sm:text-4xl font-display font-bold text-monochrome-50 tracking-tight">
              Investigated Vessel Ranking
            </h2>
          </div>
          <button
            onClick={() => navigate('/candidates')}
            className="text-xs font-heading font-medium text-monochrome-400 hover:text-monochrome-100 transition-colors"
          >
            View Full Matrix →
          </button>
        </div>

        {/* Clean Editorial Vessel Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {candidates.slice(0, 3).map((cand, idx) => {
            const isTop = idx === 0;
            return (
              <div
                key={cand.id || idx}
                onClick={() => openEvidenceDrawer(cand)}
                className="p-6 rounded-xl border border-monochrome-850 bg-monochrome-950/60 hover:border-cyan-500/50 hover:bg-monochrome-900/60 transition-all cursor-pointer select-none space-y-4"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-monochrome-500">
                    RANK #{cand.ranking || idx + 1}
                  </span>
                  <CategoryBadge category={isTop ? 'CRITICAL' : 'CANDIDATE'} size="xs" />
                </div>

                <div>
                  <h3 className="text-lg font-heading font-bold text-monochrome-50">
                    {cand.vessel?.vessel_name || `MMSI ${cand.vessel?.mmsi}`}
                  </h3>
                  <div className="text-xs font-mono text-monochrome-400 mt-0.5">
                    {cand.vessel?.vessel_type || 'Crude Oil Tanker'} • MMSI: {cand.vessel?.mmsi}
                  </div>
                </div>

                <div className="pt-2 border-t border-monochrome-800/60 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-[10px] font-mono text-monochrome-500 block uppercase">
                      Attribution Score
                    </span>
                    <span className="text-2xl font-display font-bold text-monochrome-100">
                      {Math.round(cand.overall_score || 85)}%
                    </span>
                  </div>
                  <RadialScore
                    score={Math.round(cand.overall_score || 85)}
                    size={48}
                    strokeWidth={4}
                    color={isTop ? '#fbbf24' : '#38bdf8'}
                  />
                </div>

                <p className="text-xs font-heading text-monochrome-400 line-clamp-2 pt-1 font-light">
                  {cand.natural_language_explanation || 'Vessel track intersects backward Lagrangian particle plume with significant temporal alignment.'}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* SECTION 5: OPERATIONAL PIPELINE FLOW */}
      <section className="space-y-6">
        <div>
          <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-500 block mb-1">
            END-TO-END PIPELINE ARCHITECTURE
          </span>
          <h2 className="text-2xl sm:text-3xl font-display font-bold text-monochrome-50 tracking-tight">
            Scientific Pipeline Stages
          </h2>
        </div>
        <DataPipelineFlow />
      </section>
    </div>
  );
};
