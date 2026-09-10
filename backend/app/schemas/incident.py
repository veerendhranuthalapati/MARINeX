from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.scene import SceneResponse
from app.schemas.slick import SlickResponse
from app.schemas.evidence import EvidenceRecordResponse


class IncidentCreate(BaseModel):
    id: Optional[str] = None
    title: str
    description: str = ""
    incident_time: Optional[datetime] = None
    detection_time: Optional[datetime] = None
    centroid: Optional[List[float]] = None
    bounding_box: Optional[List[float]] = None
    scenario: str = "DEMO"
    status: str = "OPEN"
    priority_level: str = "HIGH"
    assigned_analyst: str = "Coast Guard Duty Officer"
    analyst_notes: str = ""
    ml_model_id: Optional[str] = None
    ml_threshold: Optional[float] = None
    occupancy: str = Field("OBSERVED", description="Scientific status label")


class IncidentResponse(BaseModel):
    id: str
    title: str
    description: str = ""
    incident_time: Optional[datetime] = None
    detection_time: Optional[datetime] = None
    centroid: Optional[List[float]] = None
    bounding_box: Optional[List[float]] = None
    scenario: str = "DEMO"
    status: str = "OPEN"
    priority_level: str = "HIGH"
    assigned_analyst: str = ""
    analyst_notes: str = ""
    ml_model_id: Optional[str] = None
    ml_threshold: Optional[float] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)
    status_label: str = "OBSERVED"
    created_at: datetime
    updated_at: Optional[datetime] = None
    scene_count: int = 0
    slick_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class IncidentDetailResponse(IncidentResponse):
    scenes: List[SceneResponse] = Field(default_factory=list)
    slicks: List[SlickResponse] = Field(default_factory=list)
    evidence_records: List[EvidenceRecordResponse] = Field(default_factory=list)


class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority_level: Optional[str] = None
    assigned_analyst: Optional[str] = None
    analyst_notes: Optional[str] = None
    status_label: Optional[str] = None


class IncidentListResponse(BaseModel):
    total: int
    incidents: List[IncidentResponse]


class AttachSceneRequest(BaseModel):
    scene_id: str