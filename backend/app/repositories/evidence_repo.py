from typing import List, Optional
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from app.models.evidence import EvidenceRecord
from app.schemas.evidence import EvidenceRecordCreate


def json_safe(obj):
    """Recursively convert datetime/Path/numpy values into JSON-serializable ones."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if hasattr(obj, "item"):  # numpy scalars
        return obj.item()
    return obj


class EvidenceRepository:

    @staticmethod
    def create(db: Session, data: EvidenceRecordCreate) -> EvidenceRecord:
        obj = EvidenceRecord(
            id=data.id or f"EV-{uuid.uuid4().hex[:8].upper()}",
            incident_id=data.incident_id,
            evidence_type=data.evidence_type,
            source=data.source,
            source_version=data.source_version,
            status_label=data.status_label,
            confidence=data.confidence,
            timestamp=data.timestamp,
            title=data.title,
            summary=data.summary,
            value=json_safe(data.value),
            provenance=json_safe(data.provenance),
            related_entity_type=data.related_entity_type,
            related_entity_id=data.related_entity_id,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def list_for_incident(db: Session, incident_id: str, skip: int = 0, limit: int = 1000
                          ) -> List[EvidenceRecord]:
        return (
            db.query(EvidenceRecord)
            .filter(EvidenceRecord.incident_id == incident_id)
            .order_by(EvidenceRecord.timestamp.asc(), EvidenceRecord.created_at.asc())
            .offset(skip).limit(limit).all()
        )

    @staticmethod
    def count_for_incident(db: Session, incident_id: str) -> int:
        return db.query(EvidenceRecord).filter(EvidenceRecord.incident_id == incident_id).count()