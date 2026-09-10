from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.common import GeoJSONGeometry


class SlickCharacterization(BaseModel):
    area_km2: float
    perimeter_km: float
    centroid: List[float] = Field(..., description="[longitude, latitude]")
    bounding_box: List[float] = Field(..., description="[min_lon, min_lat, max_lon, max_lat]")
    length_km: float
    width_km: float
    orientation_deg: float
    compactness: float
    eccentricity: float = 0.0
    confidence: float
    attributes: Dict[str, Any] = Field(default_factory=dict)


class SlickCreate(BaseModel):
    id: Optional[str] = None
    scene_id: str
    geometry: GeoJSONGeometry
    detection_method: str
    detected_at: Optional[datetime] = None
    confidence: float = 0.85
    characterization: Optional[SlickCharacterization] = None


class SlickResponse(BaseModel):
    id: str
    scene_id: str
    geometry: Dict[str, Any]
    area_km2: float
    perimeter_km: float
    centroid: List[float]
    confidence: float
    detection_method: str
    detected_at: datetime
    length_km: float
    width_km: float
    orientation_deg: float
    compactness: float
    eccentricity: float = 0.0
    attributes: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SlickListResponse(BaseModel):
    total: int
    slicks: List[SlickResponse]
