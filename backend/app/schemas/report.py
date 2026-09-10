from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.attribution import VesselCandidateResponse
from app.schemas.environment import EnvironmentalSnapshotResponse
from app.schemas.slick import SlickResponse


class InvestigationReportGenerateRequest(BaseModel):
    analyst_name: str = "Lead Coast Guard Intelligence Analyst"
    analyst_notes: Optional[str] = None
    priority_level: Optional[str] = "HIGH"


class InvestigationReportResponse(BaseModel):
    report_id: str
    incident_id: str
    generated_at: datetime
    analyst: str
    priority_level: str
    executive_summary: str
    observed_facts: List[str]
    model_predictions: List[str]
    assumptions_and_limitations: List[str]
    slick_details: SlickResponse
    environmental_conditions: Optional[EnvironmentalSnapshotResponse] = None
    drift_analysis: Dict[str, Any]
    candidate_vessels: List[VesselCandidateResponse]
    recommended_actions: List[str]
    legal_disclaimer: str
    conclusion: str = "CANDIDATE_IDENTIFIED"
    conclusion_detail: str = (
        "Candidate vessels were correlated against the drift-hindcast origin region."
    )
    data_quality: Dict[str, Any] = Field(default_factory=dict)
