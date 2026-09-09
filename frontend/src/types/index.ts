export interface SatelliteScene {
  id: string;
  source: string;
  sensor: string;
  acquisition_time: string;
  latitude: number;
  longitude: number;
  bounding_box: number[];
  resolution: number;
  status: string;
  metadata_json?: Record<string, any>;
  file_path?: string;
  created_at?: string;
  slick_count?: number;
  satellite?: string;
  region?: string;
  resolution_meters?: number;
  bbox?: number[];
  image_path?: string;
  footprint?: number[][];
  satellite_id?: string;
}

export interface OilSlick {
  id: string;
  scene_id: string;
  geometry: {
    type: string;
    coordinates: number[][][];
  };
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
  area_sqkm?: number;
  confidence_score?: number;
  polygon_geojson?: any;
  centroid_lat?: number;
  centroid_lon?: number;
  estimated_volume_m3?: number;
}

export interface WindData {
  speed_mps: number;
  direction_deg: number;
  u_component_mps: number;
  v_component_mps: number;
  gust_mps?: number;
}

export interface OceanCurrentData {
  speed_mps: number;
  direction_deg: number;
  u_component_mps: number;
  v_component_mps: number;
  depth_meters?: number;
}

export interface WaveData {
  significant_wave_height_m: number;
  peak_period_seconds?: number;
  mean_direction_deg?: number;
}

export interface EnvironmentalSnapshot {
  id?: string;
  slick_id?: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  wind: WindData;
  ocean_current: OceanCurrentData;
  wave?: WaveData;
  source: string;
  raw_data?: Record<string, any>;
  created_at?: string;
  wind_speed_ms?: number;
  wind_direction_deg?: number;
  current_speed_ms?: number;
  current_direction_deg?: number;
  sea_temp_c?: number;
  wave_height_m?: number;
}

export interface DriftSimulation {
  id: string;
  slick_id: string;
  direction: string;
  start_time: string;
  end_time: string;
  model_name: string;
  parameters: Record<string, any>;
  origin_geometry?: {
    type: string;
    coordinates?: any;
  };
  trajectory_geometry?: {
    type: string;
    coordinates?: any;
    features?: any[];
  };
  particles: Array<{
    particle_id: number;
    coordinates: number[];
    timestamp: string;
    status: string;
  }>;
  uncertainty: Record<string, any>;
  probable_origin_time?: string;
  probable_origin_centroid?: number[];
  status: string;
  created_at: string;
  points?: Array<{ lat: number; lon: number; time: string }>;
  origin_centroid_lat?: number;
  origin_centroid_lon?: number;
  hindcast_duration_hours?: number;
  origin_uncertainty_radius_km?: number;
}

export interface Vessel {
  id: string;
  mmsi: number;
  imo?: number;
  vessel_name: string;
  vessel_type: string;
  flag: string;
  metadata_json?: Record<string, any>;
  created_at?: string;
  length_m?: number;
}

export interface AISPoint {
  id?: string;
  vessel_id?: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  speed: number;
  course: number;
  heading: number;
  navigation_status: string;
  mmsi?: number;
  speed_over_ground_knots?: number;
  course_over_ground_deg?: number;
  distance_to_origin_km?: number;
}

export interface FactorBreakdown {
  proximity_score: number;
  temporal_score: number;
  trajectory_score: number;
  behavior_score: number;
}

export interface CandidateMetrics {
  closest_distance_km: number;
  time_delta_minutes: number;
  trajectory_intersects_origin: boolean;
  transit_speed_knots: number;
  speed_anomaly_detected: boolean;
}

export interface VesselCandidate {
  id: string;
  slick_id: string;
  vessel_id: string;
  vessel: Vessel;
  rank: number;
  overall_score: number;
  confidence: string;
  factors: FactorBreakdown;
  metrics: CandidateMetrics;
  evidence: string[];
  recommendation: string;
  evaluated_at: string;
  ranking?: number;
  classification?: string;
  spatial_proximity_score?: number;
  evidence_summary?: {
    closest_distance_km?: number;
    speed_at_closest_knots?: number;
    time_delta_minutes?: number;
  };
  natural_language_explanation?: string;
}

export interface Investigation {
  id: string;
  name: string;
  slick_id: string;
  scene_id: string;
  status: string;
  priority_level?: string;
  assigned_analyst?: string | null;
  analyst_notes?: string | null;
  primary_suspect_mmsi?: number;
  confidence_level?: number;
  notes?: string;
  candidate_count?: number;
  slick?: {
    id: string;
    area_km2?: number;
    confidence?: number;
    detected_at?: string;
    centroid?: number[];
    scene_id?: string;
  };
  created_at: string;
  updated_at?: string;
}

export interface InvestigationReport {
  report_id: string;
  incident_id: string;
  generated_at: string;
  analyst: string;
  priority_level: string;
  executive_summary: string;
  observed_facts: string[];
  model_predictions: string[];
  assumptions_and_limitations: string[];
  slick_details: OilSlick;
  environmental_conditions?: EnvironmentalSnapshot;
  drift_analysis: Record<string, any>;
  candidate_vessels: VesselCandidate[];
  recommended_actions: string[];
  legal_disclaimer: string;
}

export interface DetectionRunResult {
  scene_id: string;
  detector_name: string;
  execution_time_ms?: number;
  confidence_threshold: number;
  slicks_detected: number;
  slicks: OilSlick[];
  slicks_found?: number;
}
