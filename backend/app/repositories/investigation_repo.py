from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.investigation import Investigation
from app.models.attribution import VesselCandidate
from app.schemas.attribution import VesselCandidateResponse


class InvestigationRepository:

    @staticmethod
    def get_by_slick(db: Session, slick_id: str) -> Optional[Investigation]:
        return db.query(Investigation).filter(Investigation.slick_id == slick_id).first()

    @staticmethod
    def create_or_update(
        db: Session,
        slick_id: str,
        status: str = "OPEN",
        priority_level: str = "HIGH",
        analyst_notes: str = "",
        assigned_analyst: str = "Coast Guard Duty Officer",
    ) -> Investigation:
        inv = db.query(Investigation).filter(Investigation.slick_id == slick_id).first()
        if inv:
            inv.status = status
            inv.priority_level = priority_level
            inv.analyst_notes = analyst_notes
            inv.assigned_analyst = assigned_analyst
            inv.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(inv)
            return inv

        inv = Investigation(
            id=f"inv_{slick_id[:16]}",
            slick_id=slick_id,
            status=status,
            priority_level=priority_level,
            analyst_notes=analyst_notes,
            assigned_analyst=assigned_analyst,
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)
        return inv

    @staticmethod
    def save_candidates(db: Session, candidates: List[VesselCandidateResponse]):
        for c in candidates:
            cand = VesselCandidate(
                id=c.id,
                slick_id=c.slick_id,
                vessel_id=c.vessel_id,
                proximity_score=c.factors.proximity_score,
                temporal_score=c.factors.temporal_score,
                trajectory_score=c.factors.trajectory_score,
                behavior_score=c.factors.behavior_score,
                overall_score=c.overall_score,
                rank=c.rank,
                confidence=c.confidence,
                evidence=c.evidence,
                metrics=c.metrics.model_dump(),
                recommendation=c.recommendation,
                evaluated_at=c.evaluated_at,
            )
            db.merge(cand)
        db.commit()

    @staticmethod
    def get_candidates_for_slick(db: Session, slick_id: str) -> List[VesselCandidate]:
        return (
            db.query(VesselCandidate)
            .filter(VesselCandidate.slick_id == slick_id)
            .order_by(VesselCandidate.rank.asc())
            .all()
        )
