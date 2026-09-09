from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.slick_repo import SlickRepository
from app.repositories.investigation_repo import InvestigationRepository
from app.schemas.attribution import VesselCandidateResponse

router = APIRouter(prefix="/investigations", tags=["Investigations"])


def _serialize_investigation(slick, db: Session) -> Dict[str, Any]:
    """Build the standard investigation response dict for a slick."""
    inv = InvestigationRepository.get_by_slick(db, slick.id)
    if not inv:
        inv = InvestigationRepository.create_or_update(
            db=db,
            slick_id=slick.id,
            status="OPEN",
            priority_level="HIGH" if slick.area_km2 > 10.0 else "MEDIUM",
        )
    candidates = InvestigationRepository.get_candidates_for_slick(db, slick.id)

    return {
        "id": inv.id,
        "slick_id": slick.id,
        "name": f"INV-{slick.id[:6].upper()}",
        "scene_id": slick.scene_id,
        "status": inv.status,
        "priority_level": inv.priority_level,
        "assigned_analyst": inv.assigned_analyst,
        "analyst_notes": inv.analyst_notes,
        "created_at": inv.created_at,
        "updated_at": inv.updated_at,
        "candidate_count": len(candidates),
        "slick": {
            "id": slick.id,
            "area_km2": slick.area_km2,
            "confidence": slick.confidence,
            "detected_at": slick.detected_at,
            "centroid": slick.centroid,
            "scene_id": slick.scene_id,
        },
    }


@router.get("")
def list_investigations(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Retrieve all open investigations across all detected slicks."""
    slicks = SlickRepository.list_by_scene(db)
    return [_serialize_investigation(s, db) for s in slicks]


@router.get("/{slick_id}")
def get_investigation(slick_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve full investigation workspace status, notes, and metrics for a slick."""
    slick = SlickRepository.get_by_id(db, slick_id)
    if not slick:
        raise HTTPException(status_code=404, detail=f"Slick '{slick_id}' not found.")

    inv = InvestigationRepository.get_by_slick(db, slick_id)
    if not inv:
        inv = InvestigationRepository.create_or_update(
            db=db,
            slick_id=slick_id,
            status="OPEN",
            priority_level="HIGH" if slick.area_km2 > 10.0 else "MEDIUM",
        )

    candidates = InvestigationRepository.get_candidates_for_slick(db, slick_id)

    return {
        "id": inv.id,
        "slick_id": slick.id,
        "name": f"INV-{slick.id[:6].upper()}",
        "scene_id": slick.scene_id,
        "status": inv.status,
        "priority_level": inv.priority_level,
        "assigned_analyst": inv.assigned_analyst,
        "analyst_notes": inv.analyst_notes,
        "created_at": inv.created_at,
        "updated_at": inv.updated_at,
        "candidate_count": len(candidates),
        "slick": {
            "id": slick.id,
            "area_km2": slick.area_km2,
            "confidence": slick.confidence,
            "detected_at": slick.detected_at,
            "centroid": slick.centroid,
            "scene_id": slick.scene_id,
        },
    }


@router.patch("/{slick_id}")
def update_investigation(
    slick_id: str,
    status: Optional[str] = Body(None),
    priority_level: Optional[str] = Body(None),
    analyst_notes: Optional[str] = Body(None),
    assigned_analyst: Optional[str] = Body(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Update investigation status, priority, or analyst notes."""
    inv = InvestigationRepository.get_by_slick(db, slick_id)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Investigation for slick '{slick_id}' not found.")

    updated = InvestigationRepository.create_or_update(
        db=db,
        slick_id=slick_id,
        status=status or inv.status,
        priority_level=priority_level or inv.priority_level,
        analyst_notes=analyst_notes if analyst_notes is not None else inv.analyst_notes,
        assigned_analyst=assigned_analyst or inv.assigned_analyst,
    )

    return {
        "status": "success",
        "message": "Investigation updated successfully",
        "investigation_id": updated.id,
        "new_status": updated.status,
        "updated_at": updated.updated_at,
    }
