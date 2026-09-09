import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { OilSlick, DriftSimulation, AISPoint, VesselCandidate, SatelliteScene } from '../../types';
import { useMarinexStore } from '../../store/useMarinexStore';
import { Layers, Eye, EyeOff, Navigation, Maximize2, RotateCcw } from 'lucide-react';
import { CategoryBadge } from '../ui/CategoryBadge';

interface MapLibreMapProps {
  scene?: SatelliteScene | null;
  slick?: OilSlick | null;
  slicks?: OilSlick[];
  drift?: DriftSimulation | null;
  aisPoints?: AISPoint[];
  candidates?: VesselCandidate[];
  center?: [number, number]; // [lng, lat]
  zoom?: number;
  height?: string;
  onSelectCandidate?: (candidate: VesselCandidate) => void;
}

export const MapLibreMap: React.FC<MapLibreMapProps> = ({
  scene,
  slick,
  slicks = [],
  drift,
  aisPoints = [],
  candidates = [],
  center = [71.30, 19.25], // MapLibre uses [lng, lat]
  zoom = 8.8,
  height = '600px',
  onSelectCandidate,
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [showLayerPanel, setShowLayerPanel] = useState(false);

  const {
    mapLayers,
    toggleMapLayer,
    selectedCandidateMmsi,
    openEvidenceDrawer,
    timelineHours,
  } = useMarinexStore();

  // Combine single slick with slicks list
  const allSlicks = React.useMemo(() => {
    const list = [...slicks];
    if (slick && !list.find((s) => s.id === slick.id)) {
      list.push(slick);
    }
    return list;
  }, [slick, slicks]);

  // Group AIS points by MMSI to form LineStrings
  const vesselTrajectories = React.useMemo(() => {
    const map: { [mmsi: number]: AISPoint[] } = {};
    aisPoints.forEach((p) => {
      const key = p.mmsi ?? 0;
      if (!map[key]) map[key] = [];
      map[key].push(p);
    });
    Object.keys(map).forEach((k) => {
      map[Number(k)].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    });
    return map;
  }, [aisPoints]);

  // Initialize Map
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'carto-dark': {
            type: 'raster',
            tiles: [
              'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
              'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
              'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
            ],
            tileSize: 256,
            attribution: '&copy; CartoDB &copy; OpenStreetMap',
          },
        },
        layers: [
          {
            id: 'carto-dark-tiles',
            type: 'raster',
            source: 'carto-dark',
            minzoom: 0,
            maxzoom: 20,
          },
        ],
      },
      center: center,
      zoom: zoom,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'bottom-right');

    map.on('load', () => {
      mapRef.current = map;
      updateMapSources(map);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update GeoJSON Sources and Layers whenever data changes
  const updateMapSources = (map: maplibregl.Map) => {
    // 1. Observed Oil Slick Source & Layers
    const slickFeatures = allSlicks.map((s) => ({
      type: 'Feature',
      properties: {
        id: s.id,
        area: s.area_sqkm,
        conf: s.confidence_score,
        detected_at: s.detected_at,
      },
      geometry: s.polygon_geojson,
    }));

    const slickSource = map.getSource('slicks-src') as maplibregl.GeoJSONSource;
    if (!slickSource) {
      map.addSource('slicks-src', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: slickFeatures as any },
      });

      // Fill Layer (OBSERVED - Red/Crimson)
      map.addLayer({
        id: 'slick-fill',
        type: 'fill',
        source: 'slicks-src',
        paint: {
          'fill-color': '#ef4444',
          'fill-opacity': 0.65,
        },
      });

      // Outline Layer (OBSERVED - Glowing border)
      map.addLayer({
        id: 'slick-outline',
        type: 'line',
        source: 'slicks-src',
        paint: {
          'line-color': '#f87171',
          'line-width': 2.5,
        },
      });
    } else {
      slickSource.setData({ type: 'FeatureCollection', features: slickFeatures as any });
    }

    // 2. Simulated Drift Hindcast & Inferred Origin
    if (drift && slick) {
      const originLng = drift.origin_centroid_lon;
      const originLat = drift.origin_centroid_lat;
      const slickLng = slick.centroid_lon;
      const slickLat = slick.centroid_lat;

      // Trajectory Line
      const driftLineFeature = {
        type: 'Feature',
        properties: { hours: drift.hindcast_duration_hours },
        geometry: {
          type: 'LineString',
          coordinates: [
            [slickLng, slickLat],
            [originLng, originLat],
          ],
        },
      };

      const driftSource = map.getSource('drift-src') as maplibregl.GeoJSONSource;
      if (!driftSource) {
        map.addSource('drift-src', {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [driftLineFeature as any] },
        });

        map.addLayer({
          id: 'drift-line',
          type: 'line',
          source: 'drift-src',
          paint: {
            'line-color': '#f59e0b',
            'line-width': 2.5,
            'line-dasharray': [3, 2],
          },
        });
      } else {
        driftSource.setData({ type: 'FeatureCollection', features: [driftLineFeature as any] });
      }

      // Inferred Origin Point & Uncertainty Ring
      const originPointFeature = {
        type: 'Feature',
        properties: { radius: drift.origin_uncertainty_radius_km },
        geometry: {
          type: 'Point',
          coordinates: [originLng, originLat],
        },
      };

      const originSource = map.getSource('origin-src') as maplibregl.GeoJSONSource;
      if (!originSource) {
        map.addSource('origin-src', {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [originPointFeature as any] },
        });

        map.addLayer({
          id: 'origin-circle',
          type: 'circle',
          source: 'origin-src',
          paint: {
            'circle-radius': 24, // approx uncertainty visualization
            'circle-color': '#f59e0b',
            'circle-opacity': 0.25,
            'circle-stroke-color': '#fbbf24',
            'circle-stroke-width': 2,
          },
        });

        map.addLayer({
          id: 'origin-center',
          type: 'circle',
          source: 'origin-src',
          paint: {
            'circle-radius': 6,
            'circle-color': '#fef08a',
            'circle-stroke-color': '#d97706',
            'circle-stroke-width': 2,
          },
        });
      } else {
        originSource.setData({ type: 'FeatureCollection', features: [originPointFeature as any] });
      }
    }

    // 3. Tracked AIS Vessel Trajectories
    const aisLineFeatures = Object.entries(vesselTrajectories).map(([mmsiStr, pts]) => {
      const mmsi = Number(mmsiStr);
      const isCandidate = candidates.find((c) => c.vessel?.mmsi === mmsi);
      const isPrimary = isCandidate?.classification === 'PRIMARY_SUSPECT';
      const isSelected = selectedCandidateMmsi === mmsi;

      return {
        type: 'Feature',
        properties: {
          mmsi,
          isPrimary,
          isSelected,
          color: isPrimary ? '#ef4444' : isSelected ? '#38bdf8' : '#64748b',
        },
        geometry: {
          type: 'LineString',
          coordinates: pts.map((p) => [p.longitude, p.latitude]),
        },
      };
    });

    const aisSource = map.getSource('ais-src') as maplibregl.GeoJSONSource;
    if (!aisSource) {
      map.addSource('ais-src', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: aisLineFeatures as any },
      });

      map.addLayer({
        id: 'ais-lines',
        type: 'line',
        source: 'ais-src',
        paint: {
          'line-color': ['get', 'color'],
          'line-width': ['case', ['get', 'isPrimary'], 3.5, ['get', 'isSelected'], 3.0, 1.8],
          'line-opacity': 0.85,
        },
      });
    } else {
      aisSource.setData({ type: 'FeatureCollection', features: aisLineFeatures as any });
    }

    // 4. Candidate Vessels Positions
    const vesselPointFeatures = Object.entries(vesselTrajectories).map(([mmsiStr, pts]) => {
      const mmsi = Number(mmsiStr);
      const latest = pts[pts.length - 1];
      const cand = candidates.find((c) => c.vessel?.mmsi === mmsi);
      const isPrimary = cand?.classification === 'PRIMARY_SUSPECT';
      const isSelected = selectedCandidateMmsi === mmsi;

      return {
        type: 'Feature',
        properties: {
          mmsi,
          name: cand?.vessel?.vessel_name || `MMSI: ${mmsi}`,
          speed: latest?.speed_over_ground_knots,
          course: latest?.course_over_ground_deg,
          score: cand?.overall_score || 0,
          isPrimary,
          isSelected,
        },
        geometry: {
          type: 'Point',
          coordinates: [latest.longitude, latest.latitude],
        },
      };
    });

    const vesselSource = map.getSource('vessel-points-src') as maplibregl.GeoJSONSource;
    if (!vesselSource) {
      map.addSource('vessel-points-src', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: vesselPointFeatures as any },
      });

      map.addLayer({
        id: 'vessel-points',
        type: 'circle',
        source: 'vessel-points-src',
        paint: {
          'circle-radius': ['case', ['get', 'isPrimary'], 9, 6],
          'circle-color': ['case', ['get', 'isPrimary'], '#ef4444', ['get', 'isSelected'], '#38bdf8', '#0284c7'],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 1.5,
        },
      });

      // Click event on vessel points
      map.on('click', 'vessel-points', (e: any) => {
        if (!e.features || !e.features[0]) return;
        const props = e.features[0].properties;
        const mmsi = Number(props.mmsi);
        const cand = candidates.find((c) => c.vessel?.mmsi === mmsi);
        if (cand) {
          openEvidenceDrawer(cand);
          if (onSelectCandidate) onSelectCandidate(cand);
        }
      });
    } else {
      vesselSource.setData({ type: 'FeatureCollection', features: vesselPointFeatures as any });
    }
  };

  // Sync data updates
  useEffect(() => {
    if (mapRef.current && mapRef.current.isStyleLoaded()) {
      updateMapSources(mapRef.current);
    }
  }, [allSlicks, drift, aisPoints, candidates, selectedCandidateMmsi]);

  // Handle Layer Toggles
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    if (map.getLayer('slick-fill')) {
      map.setLayoutProperty('slick-fill', 'visibility', mapLayers.observedSlicks ? 'visible' : 'none');
      map.setLayoutProperty('slick-outline', 'visibility', mapLayers.observedSlicks ? 'visible' : 'none');
    }
    if (map.getLayer('drift-line')) {
      map.setLayoutProperty('drift-line', 'visibility', mapLayers.driftHindcast ? 'visible' : 'none');
    }
    if (map.getLayer('origin-circle')) {
      map.setLayoutProperty('origin-circle', 'visibility', mapLayers.inferredOrigin ? 'visible' : 'none');
      map.setLayoutProperty('origin-center', 'visibility', mapLayers.inferredOrigin ? 'visible' : 'none');
    }
    if (map.getLayer('ais-lines')) {
      map.setLayoutProperty('ais-lines', 'visibility', mapLayers.aisTracks ? 'visible' : 'none');
    }
    if (map.getLayer('vessel-points')) {
      map.setLayoutProperty('vessel-points', 'visibility', mapLayers.candidateVessels ? 'visible' : 'none');
    }
  }, [mapLayers]);

  // FlyTo selected candidate vessel
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedCandidateMmsi) return;

    const pts = vesselTrajectories[selectedCandidateMmsi];
    if (pts && pts.length > 0) {
      const latest = pts[pts.length - 1];
      map.flyTo({
        center: [latest.longitude, latest.latitude],
        zoom: 10.2,
        speed: 1.2,
        curve: 1.4,
      });
    }
  }, [selectedCandidateMmsi, vesselTrajectories]);

  return (
    <div className="relative w-full rounded-2xl overflow-hidden border border-slate-800 bg-[#060b13] shadow-2xl">
      {/* Tactical GIS View Header Ticker */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-[#060b14]/90 backdrop-blur-md border border-slate-800/80 px-3.5 py-1.5 rounded-xl shadow-xl font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-bold text-white tracking-wider uppercase">
            MapLibre Tactical GIS
          </span>
        </div>
        <span className="text-slate-500">•</span>
        <span className="text-cyan-400 font-semibold">19.25°N, 71.30°E</span>
        <span className="text-slate-500">•</span>
        <CategoryBadge category="DEMO_DATA" size="xs" />
      </div>

      {/* Layer Control Button */}
      <div className="absolute top-4 right-4 z-10">
        <button
          onClick={() => setShowLayerPanel(!showLayerPanel)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#0a101d]/90 hover:bg-[#0e172a] border border-slate-700/80 text-xs font-mono font-bold text-slate-200 shadow-xl backdrop-blur-md transition-colors"
        >
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>LAYERS</span>
        </button>

        {showLayerPanel && (
          <div className="absolute right-0 mt-2 w-64 bg-[#0a101d] border border-slate-700/80 rounded-2xl p-3.5 shadow-2xl space-y-2.5 backdrop-blur-md z-30">
            <span className="text-[10px] font-mono uppercase tracking-widest text-slate-400 font-bold block mb-1">
              GEOSPATIAL LAYERS
            </span>

            <button
              onClick={() => toggleMapLayer('observedSlicks')}
              className="flex items-center justify-between w-full text-xs font-mono text-slate-200 hover:bg-slate-900/80 p-2 rounded-lg"
            >
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                OBSERVED Slicks
              </span>
              {mapLayers.observedSlicks ? <Eye className="w-4 h-4 text-cyan-400" /> : <EyeOff className="w-4 h-4 text-slate-600" />}
            </button>

            <button
              onClick={() => toggleMapLayer('driftHindcast')}
              className="flex items-center justify-between w-full text-xs font-mono text-slate-200 hover:bg-slate-900/80 p-2 rounded-lg"
            >
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                SIMULATED Hindcast
              </span>
              {mapLayers.driftHindcast ? <Eye className="w-4 h-4 text-cyan-400" /> : <EyeOff className="w-4 h-4 text-slate-600" />}
            </button>

            <button
              onClick={() => toggleMapLayer('inferredOrigin')}
              className="flex items-center justify-between w-full text-xs font-mono text-slate-200 hover:bg-slate-900/80 p-2 rounded-lg"
            >
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
                INFERRED Origin
              </span>
              {mapLayers.inferredOrigin ? <Eye className="w-4 h-4 text-cyan-400" /> : <EyeOff className="w-4 h-4 text-slate-600" />}
            </button>

            <button
              onClick={() => toggleMapLayer('aisTracks')}
              className="flex items-center justify-between w-full text-xs font-mono text-slate-200 hover:bg-slate-900/80 p-2 rounded-lg"
            >
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
                TRACKED AIS Paths
              </span>
              {mapLayers.aisTracks ? <Eye className="w-4 h-4 text-cyan-400" /> : <EyeOff className="w-4 h-4 text-slate-600" />}
            </button>

            <button
              onClick={() => toggleMapLayer('candidateVessels')}
              className="flex items-center justify-between w-full text-xs font-mono text-slate-200 hover:bg-slate-900/80 p-2 rounded-lg"
            >
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
                CANDIDATE Vessels
              </span>
              {mapLayers.candidateVessels ? <Eye className="w-4 h-4 text-cyan-400" /> : <EyeOff className="w-4 h-4 text-slate-600" />}
            </button>
          </div>
        )}
      </div>

      {/* Map Legend Overlay (Bottom Left) */}
      <div className="absolute bottom-4 left-4 z-10 bg-[#060b14]/90 backdrop-blur-md border border-slate-800/80 p-3 rounded-xl shadow-xl font-mono text-[10px] space-y-1.5 hidden sm:block">
        <span className="text-slate-500 uppercase tracking-widest font-bold block mb-1">
          EVIDENTIARY DOMAINS
        </span>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-sm bg-red-500" />
          <span className="text-slate-300">OBSERVED — SAR Oil Slick</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-0.5 bg-amber-400 border-b border-dashed" />
          <span className="text-slate-300">SIMULATED — Drift Hindcast Vector</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full border border-dashed border-yellow-400 bg-yellow-500/20" />
          <span className="text-slate-300">INFERRED — Probable Discharge Origin</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-0.5 bg-blue-400" />
          <span className="text-slate-300">TRACKED — AIS Vessel Trajectory</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 border border-white" />
          <span className="text-slate-300">CANDIDATE — Prioritized Vessel Marker</span>
        </div>
      </div>

      {/* MapLibre DOM Container */}
      <div ref={mapContainer} style={{ height, width: '100%' }} />
    </div>
  );
};
