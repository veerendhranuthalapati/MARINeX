from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.evidence_repo import EvidenceRepository
from app.schemas.evidence import EvidenceRecordResponse, EvidenceListResponse

router = APIRouter(prefix="/evidence", tags=["Evidence Ledger"])


@router.get("/{incident_id}", response_model=EvidenceListResponse)
def list_evidence(
    incident_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List all evidence records for an incident (Phase 22)."""
    recs = EvidenceRepository.list_for_incident(db, incident_id, skip=skip, limit=limit)
    if not recs and skip == 0:
        count = EvidenceRepository.count_for_incident(db, incident_id)
        if count == 0:
            # Not necessarily an error; empty ledger for a fresh incident.
            pass
    return EvidenceListResponse(total=EvidenceRepository.count_for_incident(db, incident_id),
                                evidence_records=recs)