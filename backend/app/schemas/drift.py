from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DriftSimulationRequest(BaseModel):
    duration_hours: float = Field(4.0, ge=0.5, le=48.0, description="Simulation duration in hours")
    direction: str = Field("HINDCAST", description="'HINDCAST' (backward in time) or 'FORECAST' (forward)")
    time_step_seconds: int = Field(900, ge=60, le=3600)
    num_particles: int = Field(200, ge=50, le=2000)
    wind_drift_factor: Optional[float] = Field(0.032, ge=0.01, le=0.06)
    diffusion_coefficient: Optional[float] = Field(10.0, ge=0.0, le=100.0)
    custom_wind_u: Optional[float] = None
    custom_wind_v: Optional[float] = None
    custom_current_u: Optional[float] = None
    custom_current_v: Optional[float] = None


class DriftParticle(BaseModel):
    particle_id: int
    coordinates: List[float] = Field(..., description="[longitude, latitude]")
    timestamp: datetime
    status: str = "active"


class DriftSimulationResponse(BaseModel):
    id: str
    slick_id: str
    direction: str
    start_time: datetime
    end_time: datetime
    model_name: str
    parameters: Dict[str, Any]
    origin_geometry: Optional[Dict[str, Any]] = None  # GeoJSON Polygon / MultiPoint
    trajectory_geometry: Optional[Dict[str, Any]] = None  # GeoJSON LineString
    particles: List[Dict[str, Any]] = Field(default_factory=list)
    uncertainty: Dict[str, Any] = Field(default_factory=dict)
    probable_origin_time: Optional[datetime] = None
    probable_origin_centroid: Optional[List[float]] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
