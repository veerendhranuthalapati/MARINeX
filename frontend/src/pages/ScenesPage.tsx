import React, { useEffect, useState } from 'react';
import { Satellite, Search, RefreshCw, Eye, ArrowUpRight, ShieldCheck, Layers } from 'lucide-react';
import { MarineXApi } from '../services/api';
import type { SatelliteScene } from '../types';
import { CategoryBadge } from '../components/investigation/CategoryBadge';
import { Link } from 'react-router-dom';

export const ScenesPage: React.FC = () => {
  const [scenes, setScenes] = useState<SatelliteScene[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('ALL');
  const [selectedScene, setSelectedScene] = useState<SatelliteScene | null>(null);

  useEffect(() => {
    loadScenes();
  }, []);

  const loadScenes = async () => {
    setLoading(true);
    try {
      const data = await MarineXApi.getScenes();
      setScenes(data);
      if (data.length > 0 && !selectedScene) {
        setSelectedScene(data[0]);
      }
    } catch (err) {
      console.error('Failed to load scenes:', err);
      const mockScenes: SatelliteScene[] = [
        {
          id: 'S1A_IW_GRDH_1SDV_20260312T014500_MUMBAI',
          source: 'Sentinel-1A SAR (C-Band)',
          sensor: 'C-SAR',
          acquisition_time: '2026-03-12T01:45:00Z',
          resolution: 10,
          latitude: 19.0,
          longitude: 72.5,
          bounding_box: [72.15, 18.72, 72.85, 19.35],
          status: 'INGESTED',
        },
        {
          id: 'S1B_IW_GRDH_1SDV_20260310T021500_GUJARAT',
          source: 'Sentinel-1B SAR (C-Band)',
          sensor: 'C-SAR',
          acquisition_time: '2026-03-10T02:15:00Z',
          resolution: 10,
          latitude: 20.75,
          longitude: 71.9,
          bounding_box: [71.55, 20.45, 72.25, 21.05],
          status: 'INGESTED',
        },
        {
          id: 'S1A_IW_GRDH_1SDV_20260308T183000_GOA',
          source: 'Sentinel-1A SAR (C-Band)',
          sensor: 'C-SAR',
          acquisition_time: '2026-03-08T18:30:00Z',
          resolution: 10,
          latitude: 15.4,
          longitude: 73.67,
          bounding_box: [73.40, 15.15, 73.95, 15.65],
          status: 'INGESTED',
        },
        {
          id: 'S2B_MSI_L2A_20260312T051000_MALABAR',
          source: 'Sentinel-2B MSI (Optical/SWIR)',
          sensor: 'MSI',
          acquisition_time: '2026-03-12T05:10:00Z',
          resolution: 10,
          latitude: 9.88,
          longitude: 75.92,
          bounding_box: [75.60, 9.60, 76.25, 10.15],
          status: 'INGESTED',
        }
      ];
      setScenes(mockScenes);
      setSelectedScene(mockScenes[0]);
    } finally {
      setLoading(false);
    }
  };

  const filteredScenes = scenes.filter((scene) => {
    const matchesSearch =
      scene.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (scene.satellite ?? scene.source ?? '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (scene.region ?? '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType =
      filterType === 'ALL' ||
      (filterType === 'SAR' && (scene.satellite ?? scene.source ?? '').includes('SAR')) ||
      (filterType === 'OPTICAL' && !(scene.satellite ?? scene.source ?? '').includes('SAR'));
    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-12">
      {/* Editorial Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-8 border-b border-monochrome-800/80">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
              EARTH OBSERVATION INGESTION
            </span>
            <CategoryBadge category="OBSERVED" size="xs" />
          </div>

          <h1 className="text-4xl sm:text-6xl font-display font-extrabold tracking-tighter text-monochrome-50">
            Satellite Scene Catalog
          </h1>

          <p className="text-sm sm:text-base font-heading text-monochrome-400 font-light max-w-3xl">
            Acquisition repository containing Sentinel-1 C-band SAR products, preprocessed level-1 GRD imagery, and multi-temporal swath mosaics over the Arabian Sea and shipping lanes.
          </p>
        </div>

        <button
          onClick={loadScenes}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 text-xs font-heading font-bold uppercase tracking-wider transition-all cursor-pointer shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Catalog</span>
        </button>
      </div>

      {/* Catalog Search & Filter */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl border border-monochrome-800/80 bg-monochrome-950/50">
        <div className="flex items-center gap-2">
          {['ALL', 'SAR', 'OPTICAL'].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-all ${
                filterType === type
                  ? 'bg-monochrome-100 text-[#05070a] font-bold'
                  : 'bg-monochrome-900/60 text-monochrome-400 hover:text-monochrome-200 border border-monochrome-800'
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-monochrome-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search scene, satellite, region..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 rounded bg-monochrome-900 border border-monochrome-800 text-xs font-mono text-monochrome-200 placeholder-monochrome-600 focus:outline-none focus:border-cyan-400"
          />
        </div>
      </div>

      {/* Main Grid: Catalog List + Detailed Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Scenes List */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between text-xs font-mono text-monochrome-500 pb-2">
            <span>AVAILABLE SWATH PRODUCTS ({filteredScenes.length})</span>
            <span>POLARISATION / RESOLUTION</span>
          </div>

          <div className="space-y-3">
            {filteredScenes.map((scene) => {
              const isSelected = selectedScene?.id === scene.id;
              const isSAR = scene.source.includes('SAR');

              return (
                <div
                  key={scene.id}
                  onClick={() => setSelectedScene(scene)}
                  className={`p-5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'border-cyan-500/50 bg-monochrome-900/80 shadow-lg shadow-cyan-950/20'
                      : 'border-monochrome-800/60 bg-monochrome-950/40 hover:border-monochrome-700 hover:bg-monochrome-900/30'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <Satellite className={`w-4 h-4 ${isSAR ? 'text-cyan-400' : 'text-emerald-400'}`} />
                        <span className="text-xs font-mono text-monochrome-300 font-medium">
                          {scene.source}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-monochrome-800/80 text-monochrome-400">
                          {scene.resolution}m GSD
                        </span>
                      </div>
                      <h3 className="text-base font-heading font-semibold text-monochrome-100">
                        {scene.region}
                      </h3>
                      <p className="text-[11px] font-mono text-monochrome-500 break-all">
                        {scene.id}
                      </p>
                    </div>

                    <div className="text-right space-y-1 shrink-0">
                      <div className="text-xs font-mono text-monochrome-400">
                        {new Date(scene.acquisition_time).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric'
                        })}
                      </div>
                      <div className="text-[11px] font-mono text-monochrome-500">
                        {new Date(scene.acquisition_time).toLocaleTimeString('en-US', {
                          hour: '2-digit',
                          minute: '2-digit',
                          timeZone: 'UTC'
                        })}{' '}
                        UTC
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Scene Inspector Detail */}
        <div className="lg:col-span-5">
          {selectedScene ? (
            <div className="p-6 rounded-xl border border-monochrome-800/80 bg-monochrome-950/60 space-y-6 sticky top-24">
              <div className="flex items-center justify-between border-b border-monochrome-800/60 pb-4">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono uppercase text-monochrome-400">
                    ACQUISITION DOSSIER
                  </span>
                  <h3 className="text-lg font-heading font-bold text-monochrome-100">
                    Product Metadata
                  </h3>
                </div>
                <CategoryBadge category="OBSERVED" size="xs" />
              </div>

              {/* Synthetic SAR Preview Wireframe */}
              <div className="relative aspect-video rounded-lg overflow-hidden border border-monochrome-800/80 bg-monochrome-900/60 flex items-center justify-center">
                <div className="absolute inset-0 bg-radial from-cyan-950/20 via-transparent to-black/60 pointer-events-none" />
                <div className="text-center space-y-2 p-4 z-10">
                  <Layers className="w-8 h-8 text-monochrome-500 mx-auto" />
                  <div className="text-xs font-mono text-monochrome-300">
                        {selectedScene.source}
                  </div>
                  <div className="text-[11px] font-mono text-monochrome-500">
                    Level-1 Ground Range Detected (GRD)
                  </div>
                </div>
              </div>

              {/* Telemetry Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 rounded bg-monochrome-900/40 border border-monochrome-800/40">
                  <span className="text-monochrome-500 block text-[10px]">POLARISATION</span>
                  <span className="text-monochrome-200 font-semibold">Dual VV + VH</span>
                </div>
                <div className="p-3 rounded bg-monochrome-900/40 border border-monochrome-800/40">
                  <span className="text-monochrome-500 block text-[10px]">INCIDENT ANGLE</span>
                  <span className="text-monochrome-200 font-semibold">34.2° – 42.8°</span>
                </div>
                <div className="p-3 rounded bg-monochrome-900/40 border border-monochrome-800/40">
                  <span className="text-monochrome-500 block text-[10px]">ORBIT DIRECTION</span>
                  <span className="text-monochrome-200 font-semibold">DESCENDING</span>
                </div>
                <div className="p-3 rounded bg-monochrome-900/40 border border-monochrome-800/40">
                  <span className="text-monochrome-500 block text-[10px]">CALIBRATION</span>
                  <span className="text-monochrome-200 font-semibold">Sigma0 (σ₀) dB</span>
                </div>
              </div>

              <div className="space-y-2 text-xs font-mono">
                <span className="text-monochrome-500 text-[10px] uppercase">GEOMETRIC BOUNDING BOX [W, S, E, N]</span>
                <div className="p-3 rounded bg-monochrome-900/60 border border-monochrome-800/40 text-monochrome-300 text-[11px]">
                  [{(selectedScene.bbox ?? selectedScene.bounding_box ?? []).join(', ')}]
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-col gap-2">
                <Link
                  to="/detection"
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 text-xs font-heading font-bold uppercase tracking-wider transition-all"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Execute Neural Segmentation</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  to="/investigation"
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded bg-monochrome-900/80 border border-monochrome-800 text-monochrome-200 hover:border-monochrome-600 text-xs font-heading font-medium tracking-wider transition-all"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Open in Investigation Workspace</span>
                </Link>
              </div>
            </div>
          ) : (
            <div className="p-12 rounded-xl border border-dashed border-monochrome-800 text-center text-monochrome-500 text-xs font-mono">
              Select a scene from the catalog to inspect radar telemetry
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
