import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Compass,
  Play,
  Clock,
  Menu,
  X,
  Layers,
  Activity,
  ArrowUpRight,
  ShieldAlert,
} from 'lucide-react';
import { MarineXApi } from '../services/api';
import { EvidenceDrawer } from '../components/investigation/EvidenceDrawer';

export const AppLayout: React.FC = () => {
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [runningDemo, setRunningDemo] = useState<boolean>(false);
  const [demoMessage, setDemoMessage] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [utcTime, setUtcTime] = useState<string>('');

  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const checkBackend = async () => {
      try {
        await MarineXApi.checkHealth();
        setApiConnected(true);
      } catch (err) {
        setApiConnected(false);
      }
    };
    checkBackend();
    const interval = setInterval(checkBackend, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleRunDemo = async () => {
    setRunningDemo(true);
    setDemoMessage('Running E2E attribution pipeline: SAR ingestion -> AI segmentation -> Lagrangian hindcast -> AIS ranking...');
    try {
      await MarineXApi.runDemoPipeline();
      setDemoMessage('Pipeline execution complete. Opening investigation dossier...');
      setTimeout(() => {
        setDemoMessage(null);
        setRunningDemo(false);
        navigate('/investigation');
      }, 1200);
    } catch (err: any) {
      setDemoMessage(`Pipeline error: ${err.message || 'Check server connection'}`);
      setTimeout(() => {
        setDemoMessage(null);
        setRunningDemo(false);
      }, 4000);
    }
  };

  const navLinks = [
    { to: '/', label: 'Overview', exact: true },
    { to: '/investigation', label: 'Investigation' },
    { to: '/detection', label: 'SAR AI Detection' },
    { to: '/drift', label: 'Lagrangian Drift' },
    { to: '/ais', label: 'AIS Intelligence' },
    { to: '/candidates', label: 'Vessel Ranking' },
    { to: '/scenes', label: 'Satellite Scenes' },
    { to: '/reports', label: 'Legal Dossier' },
  ];

  return (
    <div className="min-h-screen w-full bg-[#05070a] text-monochrome-200 antialiased flex flex-col selection:bg-cyan-500/20 selection:text-cyan-300">
      {/* Top Editorial Bar */}
      <header className="sticky top-0 z-40 w-full border-b border-monochrome-800/60 bg-[#05070a]/90 backdrop-blur-xl">
        <div className="max-w-[1720px] mx-auto px-6 sm:px-10 h-20 flex items-center justify-between">
          {/* Brand Mark */}
          <NavLink to="/" className="group flex items-center gap-3.5">
            <div className="w-8 h-8 rounded-sm bg-monochrome-100 flex items-center justify-center text-[#05070a] group-hover:bg-cyan-400 transition-colors">
              <Compass className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-display font-bold text-lg tracking-wider text-monochrome-50">
                  MARINeX
                </span>
                <span className="text-[9px] font-mono tracking-widest text-monochrome-500 uppercase px-1.5 py-0.5 border border-monochrome-800 rounded">
                  SIH26143
                </span>
              </div>
              <span className="text-[9px] font-mono uppercase tracking-widest text-monochrome-500">
                Satellite Spill Intelligence
              </span>
            </div>
          </NavLink>

          {/* Minimal Editorial Navigation */}
          <nav className="hidden xl:flex items-center gap-1">
            {navLinks.map((item) => {
              const isActive = item.exact
                ? location.pathname === item.to
                : location.pathname.startsWith(item.to);
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={`px-3.5 py-1.5 text-xs font-heading font-medium tracking-tight rounded-md transition-all ${
                    isActive
                      ? 'bg-monochrome-100 text-[#05070a] font-semibold'
                      : 'text-monochrome-400 hover:text-monochrome-100 hover:bg-monochrome-900/60'
                  }`}
                >
                  {item.label}
                </NavLink>
              );
            })}
          </nav>

          {/* Right Utilities */}
          <div className="flex items-center gap-4">
            {/* Live UTC Telemetry */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded border border-monochrome-800/80 bg-monochrome-900/50 text-[11px] font-mono text-monochrome-400">
              <span className={`w-1.5 h-1.5 rounded-full ${apiConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
              <span>{utcTime}</span>
            </div>

            {/* Pipeline Trigger CTA */}
            <button
              onClick={handleRunDemo}
              disabled={runningDemo}
              className="group relative inline-flex items-center gap-2 px-4 py-2 rounded border border-monochrome-200/20 bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 hover:border-cyan-400 text-xs font-heading font-semibold transition-all shadow-sm disabled:opacity-50 cursor-pointer"
            >
              <Play className={`w-3 h-3 fill-current ${runningDemo ? 'animate-pulse' : ''}`} />
              <span>{runningDemo ? 'Simulating...' : 'Run Attribution'}</span>
              <ArrowUpRight className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </button>

            {/* Mobile Navigation Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="xl:hidden p-2 rounded border border-monochrome-800 text-monochrome-400 hover:text-monochrome-100"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown */}
        {mobileMenuOpen && (
          <div className="xl:hidden border-t border-monochrome-800/80 bg-[#05070a]/98 px-6 py-4 space-y-2">
            {navLinks.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 text-sm font-heading text-monochrome-300 hover:text-monochrome-100 hover:bg-monochrome-900/50 rounded"
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        )}
      </header>

      {/* Global Notification Banner */}
      {demoMessage && (
        <div className="border-b border-cyan-500/30 bg-cyan-950/40 text-cyan-200 px-6 py-2.5 text-xs font-mono flex items-center justify-center gap-2 animate-fadeIn">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span>{demoMessage}</span>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-[1720px] mx-auto px-6 sm:px-10 py-8 lg:py-12">
        <Outlet />
      </main>

      {/* Global Evidence Dossier Drawer */}
      <EvidenceDrawer />

      {/* Editorial Footer */}
      <footer className="border-t border-monochrome-900 bg-[#05070a] py-10 text-monochrome-500 text-xs font-mono">
        <div className="max-w-[1720px] mx-auto px-6 sm:px-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="font-display font-bold text-monochrome-200 text-sm">MARINeX</span>
            <span>•</span>
            <span>SIH-2026 Problem Statement SIH26143</span>
            <span>•</span>
            <span>Copernicus Sentinel-1 SAR + Lagrangian Hindcast</span>
          </div>
          <div className="flex items-center gap-6">
            <span>Sector: Mumbai High (19.25°N, 71.30°E)</span>
            <span className="text-monochrome-400">Strict Evidentiary Domain Separation</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
