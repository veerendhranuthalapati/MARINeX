from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class EvidenceRecordCreate(BaseModel):
    id: Optional[str] = None
    incident_id: Optional[str] = None
    evidence_type: str
    source: str
    source_version: str = ""
    status_label: str = "OBSERVED"
    confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    title: str = ""
    summary: str = ""
    value: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None


class EvidenceRecordResponse(BaseModel):
    id: str
    incident_id: str
    evidence_type: str
    source: str
    source_version: str = ""
    status_label: str = "OBSERVED"
    confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    title: str = ""
    summary: str = ""
    value: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceListResponse(BaseModel):
    total: int
    evidence_records: List[EvidenceRecordResponse]