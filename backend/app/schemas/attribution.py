from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.ais import VesselSchema


class FactorBreakdown(BaseModel):
    proximity_score: float = Field(..., ge=0.0, le=100.0)
    temporal_score: float = Field(..., ge=0.0, le=100.0)
    trajectory_score: float = Field(..., ge=0.0, le=100.0)
    behavior_score: float = Field(..., ge=0.0, le=100.0)


class CandidateMetrics(BaseModel):
    closest_distance_km: float
    time_delta_minutes: float
    trajectory_intersects_origin: bool
    transit_speed_knots: float
    speed_anomaly_detected: bool = False


class VesselCandidateResponse(BaseModel):
    id: str
    slick_id: str
    vessel_id: str
    vessel: VesselSchema
    rank: int
    overall_score: float
    confidence: str  # HIGH, MEDIUM, LOW, EXCLUDED
    factors: FactorBreakdown
    metrics: CandidateMetrics
    evidence: List[str]
    recommendation: str
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScoringWeightsConfig(BaseModel):
    proximity: float = 0.35
    temporal: float = 0.25
    trajectory: float = 0.25
    behavior: float = 0.15


class AttributionRunRequest(BaseModel):
    weights: Optional[ScoringWeightsConfig] = None
    search_radius_km: float = Field(35.0, ge=5.0, le=100.0)
    time_window_hours_before: float = Field(6.0, ge=1.0, le=24.0)
    time_window_hours_after: float = Field(2.0, ge=0.0, le=12.0)


class AttributionResultsResponse(BaseModel):
    slick_id: str
    evaluated_at: datetime
    total_vessels_scanned: int
    weights_applied: ScoringWeightsConfig
    disclaimer: str = (
        "Scores represent relative forensic investigation priority based on geometric and temporal consistency "
        "with the drift hindcast. They do NOT represent definitive legal proof or calibrated probability of liability."
    )
    candidates: List[VesselCandidateResponse]
    conclusion: str = (
        "CANDIDATE_IDENTIFIED"
    )
    conclusion_detail: str = (
        "Candidate vessels were correlated against the drift-hindcast origin region."
    )
