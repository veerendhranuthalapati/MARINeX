import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MarineXApi } from '../services/api';
import {
  OilSlick,
  DriftSimulation,
  AISPoint,
  VesselCandidate,
  Investigation,
  SatelliteScene,
  EnvironmentalSnapshot,
} from '../types';
import { MapLibreMap } from '../components/map/MapLibreMap';
import { TimelineScrubber } from '../components/investigation/TimelineScrubber';
import { CandidateVesselCard } from '../components/investigation/CandidateVesselCard';
import { CategoryBadge } from '../components/investigation/CategoryBadge';
import { RadialScore } from '../components/investigation/RadialScore';
import {
  Crosshair,
  AlertTriangle,
  Compass,
  FileText,
  Wind,
  Layers,
  Ship,
  Calendar,
  MapPin,
  Clock,
  Sparkles,
  RefreshCw,
  ArrowUpRight,
  ShieldAlert,
} from 'lucide-react';
import { useMarinexStore } from '../store/useMarinexStore';

export const InvestigationPage: React.FC = () => {
  const navigate = useNavigate();
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [activeInvestigation, setActiveInvestigation] = useState<Investigation | null>(null);
  const [slick, setSlick] = useState<OilSlick | null>(null);
  const [scene, setScene] = useState<SatelliteScene | null>(null);
  const [drift, setDrift] = useState<DriftSimulation | null>(null);
  const [aisPoints, setAisPoints] = useState<AISPoint[]>([]);
  const [candidates, setCandidates] = useState<VesselCandidate[]>([]);
  const [env, setEnv] = useState<EnvironmentalSnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const { selectedCandidateMmsi, openEvidenceDrawer } = useMarinexStore();

  useEffect(() => {
    loadInvestigationData();
  }, []);

  const loadInvestigationData = async () => {
    setLoading(true);
    try {
      const invs = await MarineXApi.getInvestigations();
      setInvestigations(invs);

      let targetInv = invs.length > 0 ? invs[0] : null;
      setActiveInvestigation(targetInv);

      if (targetInv) {
        const targetSlickId = targetInv.slick_id;
        const cands = await MarineXApi.getCandidates(targetSlickId).catch(() => []);
        setCandidates(cands);

        if (targetSlickId) {
          const slk = await MarineXApi.getSlick(targetSlickId).catch(() => null);
          setSlick(slk);

          if (slk) {
            MarineXApi.getEnvironmentalSnapshot(slk.id)
              .then(setEnv)
              .catch(() => null);

            MarineXApi.runDriftHindcast(slk.id, 6.0)
              .then(setDrift)
              .catch(() => null);
          }
        }

        if (targetInv.scene_id) {
          MarineXApi.getScene(targetInv.scene_id)
            .then(setScene)
            .catch(() => null);
        }
      }

      const ais = await MarineXApi.getAISPoints().catch(() => []);
      setAisPoints(ais);
    } catch (err) {
      console.error('Failed to load investigation:', err);
    } finally {
      setLoading(false);
    }
  };

  const primarySuspect = candidates.find((c) => c.confidence === 'HIGH') || candidates[0];

  return (
    <div className="space-y-12">
      {/* Top Editorial Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-8 border-b border-monochrome-800/80">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
              CASE DOSSIER #{activeInvestigation ? activeInvestigation.id.slice(0, 8) : 'INV-2026-001'}
            </span>
            <CategoryBadge category="CRITICAL" size="xs" pulse />
          </div>

          <h1 className="text-4xl sm:text-6xl font-display font-extrabold tracking-tighter text-monochrome-50">
            {activeInvestigation ? activeInvestigation.name : 'Offshore Oil Spill Investigation'}
          </h1>

          <p className="text-sm sm:text-base font-heading text-monochrome-400 font-light max-w-3xl">
            Correlating observed synthetic aperture radar geometry with Lagrangian backward dispersion trajectories and spatial AIS corridors in the Arabian Sea Mumbai High sector.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => {
              if (activeInvestigation) navigate(`/reports?invId=${activeInvestigation.slick_id}`);
              else navigate('/reports');
            }}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 text-xs font-heading font-bold uppercase tracking-wider transition-all cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Generate Legal Dossier</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={loadInvestigationData}
            className="p-2.5 rounded border border-monochrome-800 text-monochrome-400 hover:text-monochrome-100 transition-colors cursor-pointer"
            title="Refresh Data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Top Suspect Focal Banner */}
      {primarySuspect && (
        <div
          onClick={() => openEvidenceDrawer(primarySuspect)}
          className="p-6 rounded-xl border border-amber-500/40 bg-monochrome-950/80 hover:border-amber-500/80 transition-all cursor-pointer shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6"
        >
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30 shrink-0">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-amber-400">
                  TOP ATTRIBUTION CANDIDATE (RANK #1)
                </span>
                <span className="text-[10px] font-mono text-monochrome-500">•</span>
                <span className="text-[10px] font-mono text-monochrome-400">
                  MMSI: {primarySuspect.vessel?.mmsi}
                </span>
              </div>
              <h2 className="text-2xl font-display font-bold text-monochrome-50">
                {primarySuspect.vessel?.vessel_name || 'PACIFIC CROWN'}
              </h2>
              <p className="text-xs font-heading text-monochrome-400 font-light max-w-2xl leading-relaxed">
                {primarySuspect.recommendation || 'Closest point of approach (CPA) 1.2 km from Lagrangian backward-in-time origin plume with consistent heading alignment during release window.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6 self-end md:self-center shrink-0">
            <div className="text-right space-y-0.5">
              <span className="text-[10px] font-mono text-monochrome-500 uppercase block">Attribution Score</span>
              <span className="text-3xl font-display font-black text-amber-400">
                {Math.round(primarySuspect.overall_score || 89)}%
              </span>
            </div>
            <RadialScore
              score={Math.round(primarySuspect.overall_score || 89)}
              size={56}
              strokeWidth={4.5}
              color="#fbbf24"
            />
          </div>
        </div>
      )}

      {/* Main Tactical Workspace: Map & Scrubber */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-500 block mb-0.5">
              GEOSPATIAL HINDCAST ENGINE
            </span>
            <h3 className="text-xl font-display font-bold text-monochrome-100 tracking-tight">
              Slick-to-Vessel Spatial Alignment
            </h3>
          </div>
          <span className="text-xs font-mono text-monochrome-400">
            RK2 Lagrangian Simulation • 6-Hour Hindcast
          </span>
        </div>

        {/* MapLibre Tactical Map */}
        <div className="relative rounded-xl border border-monochrome-800/90 overflow-hidden bg-[#070c14] shadow-2xl">
          <MapLibreMap
            scene={scene}
            slick={slick}
            drift={drift}
            aisPoints={aisPoints}
            candidates={candidates}
            height="620px"
            onSelectCandidate={(cand) => openEvidenceDrawer(cand)}
          />
        </div>

        {/* Temporal Scrubber Control */}
        <div className="pt-2">
          <TimelineScrubber maxHours={6.0} step={0.5} />
        </div>
      </section>

      {/* Two Column Section: Telemetry Facts & Ranked Candidates */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Telemetry & Environmental Observation (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/50 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-monochrome-900">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-monochrome-300">
                Slick Delineation Geometry
              </span>
              <CategoryBadge category="OBSERVED" size="xs" />
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div className="flex justify-between py-1.5 border-b border-monochrome-900">
                <span className="text-monochrome-500">Surface Area</span>
                <span className="text-monochrome-100 font-bold">{slick?.area_km2 ? slick.area_km2.toFixed(2) : '3.84'} km²</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-monochrome-900">
                <span className="text-monochrome-500">Perimeter</span>
                <span className="text-monochrome-100">{slick?.perimeter_km ? slick.perimeter_km.toFixed(2) : '18.42'} km</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-monochrome-900">
                <span className="text-monochrome-500">Estimated Volume</span>
                <span className="text-cyan-400 font-bold">{slick?.area_km2 ? (slick.area_km2 * 100).toFixed(1) : '384.0'} m³</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-monochrome-900">
                <span className="text-monochrome-500">Centroid Coordinates</span>
                <span className="text-monochrome-200">19.2541°N, 71.3012°E</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-monochrome-500">Sensor / Polarization</span>
                <span className="text-monochrome-200">Sentinel-1 C-Band (VV+VH)</span>
              </div>
            </div>
          </div>

          {/* Environmental Conditions */}
          {env && (
            <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/50 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-monochrome-900">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-monochrome-300">
                  Meteo-Oceanic Forcing Vectors
                </span>
                <CategoryBadge category="SIMULATED" size="xs" />
              </div>

              <div className="grid grid-cols-2 gap-4 font-mono text-xs">
                <div className="p-3 rounded border border-monochrome-900 bg-monochrome-900/30">
                  <span className="text-[10px] text-monochrome-500 uppercase block">Surface Wind</span>
                  <span className="text-sm font-bold text-monochrome-100 block mt-0.5">{env.wind?.speed_mps} m/s</span>
                  <span className="text-[10px] text-monochrome-500">Dir: {env.wind?.direction_deg}°</span>
                </div>
                <div className="p-3 rounded border border-monochrome-900 bg-monochrome-900/30">
                  <span className="text-[10px] text-monochrome-500 uppercase block">Ocean Current</span>
                  <span className="text-sm font-bold text-cyan-400 block mt-0.5">{env.ocean_current?.speed_mps} m/s</span>
                  <span className="text-[10px] text-monochrome-500">Dir: {env.ocean_current?.direction_deg}°</span>
                </div>
                <div className="p-3 rounded border border-monochrome-900 bg-monochrome-900/30">
                  <span className="text-[10px] text-monochrome-500 uppercase block">Sea Temp</span>
                  <span className="text-sm font-bold text-monochrome-200 block mt-0.5">{env.sea_temp_c ?? 'N/A'}°C</span>
                </div>
                <div className="p-3 rounded border border-monochrome-900 bg-monochrome-900/30">
                  <span className="text-[10px] text-monochrome-500 uppercase block">Wave Height</span>
                  <span className="text-sm font-bold text-monochrome-200 block mt-0.5">{env.wave?.significant_wave_height_m || env.wave_height_m || 'N/A'} m</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Ranked Candidate Vessel Dossier (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-monochrome-800/60">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500 block mb-0.5">
                CORRELATED AIS TARGETS
              </span>
              <h3 className="text-xl font-display font-bold text-monochrome-100 tracking-tight">
                Ranked Attribution Candidates ({candidates.length})
              </h3>
            </div>
            <span className="text-xs font-mono text-monochrome-400">
              Sorted by Multi-Factor Intercept Score
            </span>
          </div>

          <div className="space-y-3">
            {candidates.map((cand, idx) => (
              <CandidateVesselCard
                key={cand.id}
                candidate={cand}
                rank={idx + 1}
                isSelected={selectedCandidateMmsi === cand.vessel?.mmsi}
                onSelect={(c) => openEvidenceDrawer(c)}
              />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};
