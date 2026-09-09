import React, { useState, useEffect } from 'react';
import { MarineXApi } from '../services/api';
import { OilSlick, DriftSimulation } from '../types';
import { CategoryBadge } from '../components/investigation/CategoryBadge';
import { TimelineScrubber } from '../components/investigation/TimelineScrubber';
import {
  Wind,
  Compass,
  Play,
  Clock,
  MapPin,
  Sliders,
  RotateCcw,
  Layers,
  ArrowUpRight,
  Activity,
} from 'lucide-react';

export const DriftPage: React.FC = () => {
  const [slicks, setSlicks] = useState<OilSlick[]>([]);
  const [selectedSlickId, setSelectedSlickId] = useState<string>('');
  const [durationHours, setDurationHours] = useState<number>(6.0);
  const [windFactor, setWindFactor] = useState<number>(3.0);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [simulation, setSimulation] = useState<DriftSimulation | null>(null);

  useEffect(() => {
    loadSlicks();
  }, []);

  const loadSlicks = async () => {
    try {
      const data = await MarineXApi.getSlicks();
      setSlicks(data);
      if (data.length > 0) {
        setSelectedSlickId(data[0].id);
        const sim = await MarineXApi.runDriftHindcast(data[0].id, 6.0).catch(() => null);
        setSimulation(sim);
      }
    } catch (err) {
      console.error('Failed to load slicks:', err);
    }
  };

  const handleRunSimulation = async () => {
    if (!selectedSlickId) return;
    setSimulating(true);
    try {
      const sim = await MarineXApi.runDriftHindcast(selectedSlickId, durationHours, windFactor);
      setSimulation(sim);
    } catch (err) {
      console.error('Drift simulation error:', err);
    } finally {
      setSimulating(false);
    }
  };

  const selectedSlick = slicks.find((s) => s.id === selectedSlickId);

  return (
    <div className="space-y-12">
      {/* Editorial Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-8 border-b border-monochrome-800/80">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
              LAGRANGIAN HYDRODYNAMIC DRIFT
            </span>
            <CategoryBadge category="SIMULATED" size="xs" />
          </div>

          <h1 className="text-4xl sm:text-6xl font-display font-extrabold tracking-tighter text-monochrome-50">
            Lagrangian Drift Hindcast
          </h1>

          <p className="text-sm sm:text-base font-heading text-monochrome-400 font-light max-w-3xl">
            Simulating backward-in-time trajectory plumes using 2nd-order Runge-Kutta integration of Copernicus marine currents and ERA5 wind vectors to estimate spill origin locations.
          </p>
        </div>

        <button
          onClick={handleRunSimulation}
          disabled={simulating || !selectedSlickId}
          className="inline-flex items-center gap-2.5 px-6 py-3 rounded bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 text-xs font-heading font-bold uppercase tracking-wider transition-all disabled:opacity-50 cursor-pointer shrink-0"
        >
          <Play className={`w-3.5 h-3.5 fill-current ${simulating ? 'animate-pulse' : ''}`} />
          <span>{simulating ? 'Computing Plume...' : 'Simulate Hindcast'}</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Two Column Layout: Parameters & Scrubber Simulation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Physics Controls (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/60 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-monochrome-900">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-monochrome-300">
                Simulation Parameters
              </span>
              <span className="text-[10px] font-mono text-amber-400">PHYSICS RK2</span>
            </div>

            {/* Target Slick */}
            <div className="space-y-2">
              <label className="text-[11px] font-mono uppercase text-monochrome-400 block">
                Target Slick Geometry
              </label>
              <select
                value={selectedSlickId}
                onChange={(e) => setSelectedSlickId(e.target.value)}
                className="w-full px-3 py-2 rounded bg-monochrome-900 border border-monochrome-800 text-xs font-mono text-monochrome-200 focus:outline-none focus:border-cyan-400"
              >
                {slicks.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.id.slice(0, 16)}... ({s.area_km2?.toFixed(2)} km²)
                  </option>
                ))}
              </select>
            </div>

            {/* Hindcast Window */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-monochrome-400">Lookback Horizon</span>
                <span className="text-cyan-400 font-bold">{durationHours.toFixed(1)} hrs prior</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="24.0"
                step="1.0"
                value={durationHours}
                onChange={(e) => setDurationHours(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-monochrome-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              />
            </div>

            {/* Wind Drift Factor */}
            <div className="space-y-2 pt-2 border-t border-monochrome-900">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-monochrome-400">Wind Leeway Factor</span>
                <span className="text-amber-400 font-bold">{windFactor.toFixed(1)}%</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="5.0"
                step="0.5"
                value={windFactor}
                onChange={(e) => setWindFactor(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-monochrome-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
              />
              <span className="text-[10px] font-mono text-monochrome-500 block">
                Standard empirical leeway: 3.0% to 3.5%
              </span>
            </div>
          </div>

          {/* Hydrodynamic Telemetry Summary */}
          <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/60 space-y-4 font-mono text-xs">
            <span className="text-[10px] text-monochrome-500 uppercase block tracking-wider">
              Hydrodynamic Hindcast Telemetry
            </span>
            <div className="space-y-2">
              <div className="flex justify-between py-1 border-b border-monochrome-900">
                <span className="text-monochrome-500">Surface Current Field</span>
                <span className="text-monochrome-200">HYCOM 1/12° Analysis</span>
              </div>
              <div className="flex justify-between py-1 border-b border-monochrome-900">
                <span className="text-monochrome-500">Wind Reanalysis</span>
                <span className="text-monochrome-200">ERA5 10m Velocity</span>
              </div>
              <div className="flex justify-between py-1 border-b border-monochrome-900">
                <span className="text-monochrome-500">Integration Step dt</span>
                <span className="text-monochrome-200">300s (5 min)</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-monochrome-500">Plume Particles</span>
                <span className="text-cyan-400 font-bold">100 Tracers</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Particle Animation & Trajectory Replay (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/50 space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-monochrome-900">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-widest text-monochrome-500 block mb-0.5">
                  PARTICLE DISPERSION TIMELINE
                </span>
                <h3 className="text-lg font-heading font-bold text-monochrome-100">
                  Hindcast Trajectory Replay
                </h3>
              </div>
              <span className="text-xs font-mono text-cyan-400">
                {simulation ? `${simulation.particles?.length || 0} Waypoints Generated` : 'Ready'}
              </span>
            </div>

            {/* Interactive Timeline Scrubber */}
            <TimelineScrubber maxHours={durationHours} step={0.5} />

            {/* Mathematical Physics Equation Block */}
            <div className="p-5 rounded-lg border border-monochrome-900 bg-monochrome-900/30 space-y-2">
              <span className="text-[10px] font-mono uppercase text-monochrome-500 tracking-wider block">
                Lagrangian Displacement Equation
              </span>
              <div className="font-mono text-xs text-monochrome-300">
                {"dx/dt = - [ u_{current}(x, t) + α_{leeway} · W_{wind}(x, t) ]"}
              </div>
              <p className="text-[11px] font-heading text-monochrome-500 leading-relaxed">
                Backward integration inverts the net transport velocity field to trace slick centroid parcels back to candidate discharge coordinates and release timestamps.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
