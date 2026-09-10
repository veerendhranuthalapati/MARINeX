from typing import List, Optional
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from app.models.detection_run import DetectionRun


class DetectionRunRepository:

    @staticmethod
    def create(db: Session, scene_id: str, model_id: str, status: str = "SLICKS_FOUND",
               artifact_path: Optional[str] = None, method: str = "PRODUCTION_ML",
               incident_id: Optional[str] = None, model_version: Optional[str] = None,
               preprocessing_version: Optional[str] = None, threshold: Optional[float] = None,
               confidence: Optional[float] = None, metadata_json: Optional[dict] = None) -> DetectionRun:
        obj = DetectionRun(
            id=f"RUN-{uuid.uuid4().hex[:10].upper()}",
            scene_id=scene_id,
            incident_id=incident_id,
            model_id=model_id,
            model_version=model_version,
            preprocessing_version=preprocessing_version,
            threshold=threshold,
            status=status,
            artifact_path=artifact_path,
            method=method,
            confidence=confidence,
            metadata_json=metadata_json or {},
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def latest_for_scene(db: Session, scene_id: str) -> Optional[DetectionRun]:
        return (db.query(DetectionRun).filter(DetectionRun.scene_id == scene_id)
                .order_by(DetectionRun.created_at.desc()).first())

    @staticmethod
    def list_for_incident(db: Session, incident_id: str) -> List[DetectionRun]:
        return db.query(DetectionRun).filter(DetectionRun.incident_id == incident_id)\
            .order_by(DetectionRun.created_at.desc()).all()