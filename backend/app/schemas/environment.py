from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class WindData(BaseModel):
    speed_mps: float
    direction_deg: float
    u_component_mps: float
    v_component_mps: float
    gust_mps: Optional[float] = None


class OceanCurrentData(BaseModel):
    speed_mps: float
    direction_deg: float
    u_component_mps: float
    v_component_mps: float
    depth_meters: Optional[float] = 0.5


class WaveData(BaseModel):
    significant_wave_height_m: float
    peak_period_seconds: Optional[float] = None
    mean_direction_deg: Optional[float] = None


class EnvironmentalSnapshotResponse(BaseModel):
    id: str
    slick_id: Optional[str] = None
    timestamp: datetime
    latitude: float
    longitude: float
    wind: WindData
    ocean_current: OceanCurrentData
    wave: Optional[WaveData] = None
    source: str
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
