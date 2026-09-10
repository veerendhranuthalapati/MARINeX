from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class AsyncJobCreate(BaseModel):
    incident_id: Optional[str] = None
    job_type: str = "detection"


class AsyncJobResponse(BaseModel):
    id: str
    incident_id: Optional[str] = None
    job_type: str
    status: str = "PENDING"       # PENDING, RUNNING, COMPLETED, FAILED
    progress_pct: str = "0"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)