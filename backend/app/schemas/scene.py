from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SceneBase(BaseModel):
    id: str
    source: str
    sensor: str
    acquisition_time: datetime
    latitude: float
    longitude: float
    bounding_box: List[float] = Field(..., description="[min_lon, min_lat, max_lon, max_lat]")
    resolution: float = 10.0
    status: str = "INGESTED"
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class SceneCreate(SceneBase):
    file_path: Optional[str] = None


class SceneResponse(SceneBase):
    file_path: Optional[str] = None
    created_at: datetime
    slick_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class SceneListResponse(BaseModel):
    total: int
    scenes: List[SceneResponse]
