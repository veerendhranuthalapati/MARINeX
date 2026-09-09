from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.scene import SatelliteScene
from app.schemas.scene import SceneCreate


class SceneRepository:

    @staticmethod
    def get_by_id(db: Session, scene_id: str) -> Optional[SatelliteScene]:
        return db.query(SatelliteScene).filter(SatelliteScene.id == scene_id).first()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[SatelliteScene]:
        return db.query(SatelliteScene).order_by(SatelliteScene.acquisition_time.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def count(db: Session) -> int:
        return db.query(SatelliteScene).count()

    @staticmethod
    def create(db: Session, data: SceneCreate) -> SatelliteScene:
        obj = SatelliteScene(
            id=data.id,
            source=data.source,
            sensor=data.sensor,
            acquisition_time=data.acquisition_time,
            latitude=data.latitude,
            longitude=data.longitude,
            bounding_box=data.bounding_box,
            resolution=data.resolution,
            file_path=data.file_path,
            metadata_json=data.metadata_json,
            status=data.status,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update_status(db: Session, scene_id: str, status: str) -> Optional[SatelliteScene]:
        scene = db.query(SatelliteScene).filter(SatelliteScene.id == scene_id).first()
        if scene:
            scene.status = status
            db.commit()
            db.refresh(scene)
        return scene
