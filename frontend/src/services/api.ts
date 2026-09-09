import axios from 'axios';
import type {
  SatelliteScene,
  OilSlick,
  EnvironmentalSnapshot,
  DriftSimulation,
  Vessel,
  AISPoint,
  VesselCandidate,
  Investigation,
  InvestigationReport,
  DetectionRunResult,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// ---------------------------------------------------------------------------
// Response mappers: convert backend (tested) contracts into the augmented
// frontend shapes consumed by pages/components. Backend remains source of truth.
// ---------------------------------------------------------------------------

interface BackendSlick {
  id: string;
  scene_id: string;
  geometry: { type: string; coordinates: number[][][] };
  area_km2: number;
  perimeter_km: number;
  centroid: number[];
  confidence: number;
  detection_method: string;
  detected_at: string;
  length_km: number;
  width_km: number;
  orientation_deg: number;
  compactness: number;
  attributes: Record<string, any>;
  created_at?: string;
}

const mapSlick = (s: BackendSlick): OilSlick => ({
  ...s,
  area_sqkm: s.area_km2,
  confidence_score: s.confidence,
  polygon_geojson: s.geometry,
  centroid_lon: s.centroid?.[0],
  centroid_lat: s.centroid?.[1],
});

interface BackendDrift {
  id: string;
  slick_id: string;
  direction: string;
  start_time: string;
  end_time: string;
  model_name: string;
  parameters: Record<string, any>;
  origin_geometry?: any;
  trajectory_geometry?: any;
  particles: Array<{ particle_id: number; coordinates: number[]; timestamp: string; status: string }>;
  uncertainty: Record<string, any>;
  probable_origin_time?: string;
  probable_origin_centroid?: number[];
  status: string;
  created_at: string;
}

const mapDrift = (d: BackendDrift): DriftSimulation => {
  const origin = d.probable_origin_centroid || [0, 0];
  return {
    ...d,
    origin_centroid_lon: origin[0],
    origin_centroid_lat: origin[1],
    hindcast_duration_hours: Number(d.parameters?.duration_hours ?? 0),
    origin_uncertainty_radius_km: Number(d.uncertainty?.diffusion_radius_km ?? 0),
  };
};

interface BackendCandidate {
  id: string;
  slick_id: string;
  vessel_id: string;
  vessel: Vessel;
  rank: number;
  overall_score: number;
  confidence: string;
  factors?: {
    proximity_score?: number;
    temporal_score?: number;
    trajectory_score?: number;
    behavior_score?: number;
  };
  metrics?: {
    closest_distance_km?: number;
    time_delta_minutes?: number;
    trajectory_intersects_origin?: boolean;
    transit_speed_knots?: number;
    speed_anomaly_detected?: boolean;
  };
  evidence?: string[];
  recommendation?: string;
  evaluated_at: string;
}

const mapCandidate = (c: BackendCandidate): VesselCandidate => ({
  ...c,
  factors: {
    proximity_score: c.factors?.proximity_score ?? 0,
    temporal_score: c.factors?.temporal_score ?? 0,
    trajectory_score: c.factors?.trajectory_score ?? 0,
    behavior_score: c.factors?.behavior_score ?? 0,
  },
  metrics: {
    closest_distance_km: c.metrics?.closest_distance_km ?? 0,
    time_delta_minutes: c.metrics?.time_delta_minutes ?? 0,
    trajectory_intersects_origin: c.metrics?.trajectory_intersects_origin ?? false,
    transit_speed_knots: c.metrics?.transit_speed_knots ?? 0,
    speed_anomaly_detected: c.metrics?.speed_anomaly_detected ?? false,
  },
  evidence: c.evidence ?? [],
  recommendation: c.recommendation ?? '',
  ranking: c.rank,
  classification: c.rank === 1 ? 'PRIMARY_SUSPECT' : 'SECONDARY_SUSPECT',
  spatial_proximity_score: c.factors?.proximity_score,
  evidence_summary: {
    closest_distance_km: c.metrics?.closest_distance_km,
    speed_at_closest_knots: c.metrics?.transit_speed_knots,
    time_delta_minutes: c.metrics?.time_delta_minutes,
  },
  natural_language_explanation:
    c.recommendation || (c.evidence && c.evidence.length > 0 ? c.evidence.join(' ') : ''),
});

interface BackendAISPoint {
  id?: string;
  vessel_id?: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  speed: number;
  course: number;
  heading: number;
  navigation_status: string;
}

const mapAISPoints = (points: BackendAISPoint[], mmsi: number): AISPoint[] =>
  points.map((p) => ({
    ...p,
    mmsi,
    speed_over_ground_knots: p.speed,
    course_over_ground_deg: p.course,
  }));

// ---------------------------------------------------------------------------

export const MarineXApi = {
  // Health
  checkHealth: async () => {
    const res = await api.get('/health');
    return res.data;
  },

  // Scenes
  getScenes: async (): Promise<SatelliteScene[]> => {
    const res = await api.get('/scenes');
    return res.data.scenes ?? res.data;
  },

  getScene: async (sceneId: string): Promise<SatelliteScene> => {
    const res = await api.get(`/scenes/${sceneId}`);
    return res.data;
  },

  // Detection
  runDetection: async (
    sceneId: string,
    detectorName: string = 'mock_dl',
    confidenceThreshold: number = 0.70
  ): Promise<DetectionRunResult> => {
    const res = await api.post(`/detection/run/${sceneId}`, null, {
      params: {
        method: detectorName.toUpperCase(),
        confidence_threshold: confidenceThreshold,
      },
    });
    const slicks: OilSlick[] = res.data.map(mapSlick);
    return {
      scene_id: sceneId,
      detector_name: detectorName,
      confidence_threshold: confidenceThreshold,
      slicks_detected: slicks.length,
      slicks,
      slicks_found: slicks.length,
    };
  },

  // Slicks
  getSlicks: async (): Promise<OilSlick[]> => {
    const res = await api.get('/slicks');
    return (res.data.slicks ?? res.data).map(mapSlick);
  },

  getSlick: async (slickId: string): Promise<OilSlick> => {
    const res = await api.get(`/slicks/${slickId}`);
    return mapSlick(res.data);
  },

  // Environmental (keyed by slick, per backend contract)
  getEnvironmentalSnapshot: async (slickId: string): Promise<EnvironmentalSnapshot> => {
    const res = await api.get(`/environment/${slickId}`);
    return res.data;
  },

  // Drift Simulation
  runDriftHindcast: async (
    slickId: string,
    durationHours: number = 6.0,
    windFactor: number = 3.2
  ): Promise<DriftSimulation> => {
    const res = await api.post(`/drift/${slickId}/simulate`, {
      duration_hours: durationHours,
      direction: 'HINDCAST',
      wind_drift_factor: Math.max(0.01, Math.min(0.06, windFactor / 100)),
    });
    return mapDrift(res.data);
  },

  getDriftSimulation: async (slickId: string): Promise<DriftSimulation> => {
    const res = await api.get(`/drift/${slickId}`);
    return mapDrift(res.data);
  },

  // AIS & Vessels
  getVessels: async (): Promise<Vessel[]> => {
    const res = await api.get('/ais/corridor/all');
    const trajectories = res.data ?? [];
    const seen = new Map<string, Vessel>();
    trajectories.forEach((t: any) => {
      if (t?.vessel && !seen.has(t.vessel.id)) seen.set(t.vessel.id, t.vessel);
    });
    return Array.from(seen.values());
  },

  getAISPoints: async (): Promise<AISPoint[]> => {
    const res = await api.get('/ais/corridor/all');
    const trajectories = res.data ?? [];
    const points: AISPoint[] = [];
    trajectories.forEach((t: any) => {
      if (t?.vessel && t.points?.length) {
        points.push(...mapAISPoints(t.points, t.vessel.mmsi));
      }
    });
    return points;
  },

  getVesselTrajectory: async (vesselId: string): Promise<AISPoint[]> => {
    const res = await api.get(`/ais/trajectories/${vesselId}`);
    const traj = res.data;
    if (traj?.points) return mapAISPoints(traj.points, traj.vessel?.mmsi);
    return mapAISPoints(traj ?? [], (traj as any)?.vessel?.mmsi);
  },

  // Attribution
  runAttribution: async (params: {
    slick_id: string;
    search_radius_km?: number;
    time_window_hours_before?: number;
    time_window_hours_after?: number;
  }): Promise<VesselCandidate[]> => {
    const res = await api.post(`/attribution/${params.slick_id}/run`, {
      search_radius_km: params.search_radius_km ?? 35.0,
      time_window_hours_before: params.time_window_hours_before ?? 6.0,
      time_window_hours_after: params.time_window_hours_after ?? 2.0,
    });
    return (res.data.candidates ?? []).map(mapCandidate);
  },

  getCandidates: async (slickId: string): Promise<VesselCandidate[]> => {
    const res = await api.get(`/candidates/${slickId}`);
    return res.data.map(mapCandidate);
  },

  // Investigations
  getInvestigations: async (): Promise<Investigation[]> => {
    const res = await api.get('/investigations');
    return res.data;
  },

  getInvestigation: async (slickId: string): Promise<Investigation> => {
    const res = await api.get(`/investigations/${slickId}`);
    return res.data;
  },

  updateInvestigation: async (
    slickId: string,
    data: { status?: string; priority_level?: string; analyst_notes?: string; assigned_analyst?: string }
  ) => {
    const res = await api.patch(`/investigations/${slickId}`, data);
    return res.data;
  },

  // Reports (keyed by slick_id per backend contract)
  generateReport: async (
    slickId: string,
    opts?: { analyst_name?: string; analyst_notes?: string; priority_level?: string }
  ): Promise<InvestigationReport> => {
    const res = await api.post(`/reports/${slickId}/generate`, {
      analyst_name: opts?.analyst_name ?? 'Lead Coast Guard Intelligence Analyst',
      analyst_notes: opts?.analyst_notes ?? null,
      priority_level: opts?.priority_level ?? 'HIGH',
    });
    return res.data;
  },

  getReport: async (slickId: string): Promise<InvestigationReport> => {
    const res = await api.get(`/reports/${slickId}`);
    return res.data;
  },

  // Demo Pipeline
  runDemoPipeline: async () => {
    const res = await api.post('/demo/run-e2e');
    return res.data;
  },
};

export default api;