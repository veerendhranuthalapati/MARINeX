from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AISPointSchema(BaseModel):
    id: Optional[str] = None
    vessel_id: Optional[str] = None
    timestamp: datetime
    latitude: float
    longitude: float
    speed: float = Field(0.0, description="Speed over ground in knots")
    course: float = Field(0.0, description="Course over ground in degrees")
    heading: float = Field(0.0, description="True heading in degrees")
    navigation_status: str = "Under way using engine"

    model_config = ConfigDict(from_attributes=True)


class VesselSchema(BaseModel):
    id: str
    mmsi: int
    imo: Optional[int] = None
    vessel_name: str
    vessel_type: str
    flag: str = "Unknown"
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AISQueryRequest(BaseModel):
    bounding_box: List[float] = Field(..., description="[min_lon, min_lat, max_lon, max_lat]")
    start_time: datetime
    end_time: datetime
    vessel_types: Optional[List[str]] = None


class VesselTrajectoryResponse(BaseModel):
    vessel: VesselSchema
    points: List[AISPointSchema]
    point_count: int
    start_time: datetime
    end_time: datetime
