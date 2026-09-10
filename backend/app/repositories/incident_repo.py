from typing import List, Optional
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from app.models.incident import Incident
from app.models.scene import SatelliteScene
from app.schemas.incident import IncidentCreate, IncidentUpdate


class IncidentRepository:

    @staticmethod
    def get_by_id(db: Session, incident_id: str) -> Optional[Incident]:
        return db.query(Incident).filter(Incident.id == incident_id).first()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Incident]:
        return db.query(Incident).order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def count(db: Session) -> int:
        return db.query(Incident).count()

    @staticmethod
    def create(db: Session, data: IncidentCreate) -> Incident:
        obj = Incident(
            id=data.id or f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
            title=data.title,
            description=data.description,
            incident_time=data.incident_time,
            detection_time=data.detection_time,
            centroid=data.centroid,
            bounding_box=data.bounding_box,
            scenario=data.scenario,
            status=data.status,
            priority_level=data.priority_level,
            assigned_analyst=data.assigned_analyst,
            analyst_notes=data.analyst_notes,
            ml_model_id=data.ml_model_id,
            ml_threshold=data.ml_threshold,
            status_label=data.occupancy,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(db: Session, incident_id: str, data: IncidentUpdate) -> Optional[Incident]:
        obj = db.query(Incident).filter(Incident.id == incident_id).first()
        if not obj:
            return None
        for field in ["title", "description", "status", "priority_level",
                      "assigned_analyst", "analyst_notes", "status_label"]:
            val = getattr(data, field, None)
            if val is not None:
                setattr(obj, field, val)
        obj.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def attach_scene(db: Session, incident_id: str, scene_id: str) -> Optional[Incident]:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        scene = db.query(SatelliteScene).filter(SatelliteScene.id == scene_id).first()
        if not incident or not scene:
            return None
        scene.incident_id = incident_id
        # Inherit spatial context if incident has none
        if incident.incident_time is None:
            incident.incident_time = scene.acquisition_time
        if incident.centroid is None:
            incident.centroid = [scene.longitude, scene.latitude]
        if incident.bounding_box is None:
            incident.bounding_box = scene.bounding_box
        incident.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(incident)
        return incident

    @staticmethod
    def update_ml(db: Session, incident_id: str, model_id: str, threshold: float,
                  status_label: Optional[str] = None) -> Optional[Incident]:
        obj = db.query(Incident).filter(Incident.id == incident_id).first()
        if not obj:
            return None
        obj.ml_model_id = model_id
        obj.ml_threshold = threshold
        if status_label:
            obj.status_label = status_label
        obj.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(obj)
        return obj