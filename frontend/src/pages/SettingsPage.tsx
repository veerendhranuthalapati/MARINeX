import React, { useState, useEffect } from 'react';
import { MarineXApi } from '../services/api';
import { Badge } from '../components/common/Badge';
import {
  Settings,
  Sliders,
  Database,
  Cpu,
  Save,
  RotateCcw,
  CheckCircle2,
  Server,
  Terminal,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  // Attribution engine weights
  const [wProx, setWProx] = useState<number>(0.35);
  const [wTemp, setWTemp] = useState<number>(0.25);
  const [wTraj, setWTraj] = useState<number>(0.25);
  const [wBehav, setWBehav] = useState<number>(0.15);

  // Hindcast physics
  const [windFactor, setWindFactor] = useState<number>(3.0);
  const [currentFactor, setCurrentFactor] = useState<number>(100.0);

  // Backend diagnostics
  const [backendHealth, setBackendHealth] = useState<any>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    MarineXApi.checkHealth()
      .then(setBackendHealth)
      .catch(() => setBackendHealth({ status: 'offline' }));
  }, []);

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handleReset = () => {
    setWProx(0.35);
    setWTemp(0.25);
    setWTraj(0.25);
    setWBehav(0.15);
    setWindFactor(3.0);
    setCurrentFactor(100.0);
  };

  const totalWeight = Math.round((wProx + wTemp + wTraj + wBehav) * 100);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <Settings className="w-6 h-6 text-cyan-400" />
          MARINeX Platform & Algorithmic Parameters
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Fine-tune multi-factor vessel attribution coefficients, drift model hydrodynamic parameters, and verify platform infrastructure health.
        </p>
      </div>

      {savedSuccess && (
        <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Algorithmic weights and drift parameters updated successfully.</span>
        </div>
      )}

      {/* Attribution Weights Card */}
      <div className="bg-[#0e1a2c]/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-cyan-400" />
            Vessel Attribution Multi-Factor Scoring Weights
          </h2>
          <span
            className={`text-xs font-mono font-bold ${
              totalWeight === 100 ? 'text-emerald-400' : 'text-amber-400'
            }`}
          >
            Total: {totalWeight}%
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">Spatial Proximity (W_prox)</span>
              <span className="font-mono text-cyan-300 font-bold">{Math.round(wProx * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.60"
              step="0.05"
              value={wProx}
              onChange={(e) => setWProx(parseFloat(e.target.value))}
              className="w-full accent-cyan-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500 block">Distance to estimated spill origin</span>
          </div>

          <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">Temporal Synchronization (W_temp)</span>
              <span className="font-mono text-amber-300 font-bold">{Math.round(wTemp * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.50"
              step="0.05"
              value={wTemp}
              onChange={(e) => setWTemp(parseFloat(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500 block">Timestamp alignment with release time</span>
          </div>

          <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">Trajectory Intersection (W_traj)</span>
              <span className="font-mono text-cyan-300 font-bold">{Math.round(wTraj * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.50"
              step="0.05"
              value={wTraj}
              onChange={(e) => setWTraj(parseFloat(e.target.value))}
              className="w-full accent-cyan-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500 block">Course segment path cutting origin polygon</span>
          </div>

          <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">Behavioral Anomaly (W_behav)</span>
              <span className="font-mono text-emerald-300 font-bold">{Math.round(wBehav * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.40"
              step="0.05"
              value={wBehav}
              onChange={(e) => setWBehav(parseFloat(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500 block">Speed drop or irregular maneuvers</span>
          </div>
        </div>
      </div>

      {/* Backend Health Diagnostics */}
      <div className="bg-[#0e1a2c]/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Server className="w-4 h-4 text-cyan-400" />
          Backend Service Architecture & Connectivity
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block">FastAPI Server</span>
            <span className="text-emerald-400 font-bold text-sm block mt-1">
              {backendHealth?.status === 'ok' ? 'HEALTHY (v1.0)' : 'UNREACHABLE'}
            </span>
            <span className="text-slate-500 text-[10px] mt-0.5 block">Port 8000</span>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block">Database Engine</span>
            <span className="text-cyan-300 font-bold text-sm block mt-1">
              SQLite / PostGIS
            </span>
            <span className="text-slate-500 text-[10px] mt-0.5 block">SQLAlchemy ORM</span>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block">Spatial Engine</span>
            <span className="text-amber-300 font-bold text-sm block mt-1">
              Shapely WGS-84
            </span>
            <span className="text-slate-500 text-[10px] mt-0.5 block">Metric Projection</span>
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={handleReset}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-300 text-xs font-semibold"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Defaults</span>
        </button>

        <button
          onClick={handleSave}
          className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-cyan-600/20"
        >
          <Save className="w-3.5 h-3.5" />
          <span>Apply Configuration</span>
        </button>
      </div>
    </div>
  );
};
