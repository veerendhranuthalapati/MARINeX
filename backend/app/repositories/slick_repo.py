from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.slick import OilSlick
from app.schemas.slick import SlickCreate, SlickCharacterization


class SlickRepository:

    @staticmethod
    def get_by_id(db: Session, slick_id: str) -> Optional[OilSlick]:
        return db.query(OilSlick).filter(OilSlick.id == slick_id).first()

    @staticmethod
    def list_by_scene(db: Session, scene_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[OilSlick]:
        query = db.query(OilSlick)
        if scene_id:
            query = query.filter(OilSlick.scene_id == scene_id)
        return query.order_by(OilSlick.detected_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def count(db: Session, scene_id: Optional[str] = None) -> int:
        query = db.query(OilSlick)
        if scene_id:
            query = query.filter(OilSlick.scene_id == scene_id)
        return query.count()

    @staticmethod
    def create(
        db: Session,
        slick_id: str,
        scene_id: str,
        geometry: dict,
        characterization: SlickCharacterization,
        detection_method: str,
        detected_at: Optional[datetime] = None,
        confidence: float = 0.85,
    ) -> OilSlick:
        existing = db.query(OilSlick).filter(OilSlick.id == slick_id).first()
        if existing:
            existing.geometry = geometry
            existing.area_km2 = characterization.area_km2
            existing.perimeter_km = characterization.perimeter_km
            existing.centroid = characterization.centroid
            existing.confidence = confidence
            existing.detection_method = detection_method
            existing.detected_at = detected_at or existing.detected_at
            existing.length_km = characterization.length_km
            existing.width_km = characterization.width_km
            existing.orientation_deg = characterization.orientation_deg
            existing.compactness = characterization.compactness
            existing.attributes = characterization.attributes
            db.commit()
            db.refresh(existing)
            return existing

        obj = OilSlick(
            id=slick_id,
            scene_id=scene_id,
            geometry=geometry,
            area_km2=characterization.area_km2,
            perimeter_km=characterization.perimeter_km,
            centroid=characterization.centroid,
            confidence=confidence,
            detection_method=detection_method,
            detected_at=detected_at or datetime.now(timezone.utc),
            length_km=characterization.length_km,
            width_km=characterization.width_km,
            orientation_deg=characterization.orientation_deg,
            compactness=characterization.compactness,
            attributes=characterization.attributes,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
