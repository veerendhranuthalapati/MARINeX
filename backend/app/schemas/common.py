from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GeoJSONGeometry(BaseModel):
    type: str = Field(..., description="Geometry type (e.g. Point, LineString, Polygon)")
    coordinates: Any = Field(..., description="GeoJSON coordinate array")


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    geometry: GeoJSONGeometry


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)
    properties: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    message: str
    status: str = "success"
    details: Optional[Dict[str, Any]] = None
