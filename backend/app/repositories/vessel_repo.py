from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.vessel import Vessel, AISPoint
from app.schemas.ais import VesselSchema, AISPointSchema


class VesselRepository:

    @staticmethod
    def get_by_id(db: Session, vessel_id: str) -> Optional[Vessel]:
        return db.query(Vessel).filter(Vessel.id == vessel_id).first()

    @staticmethod
    def get_by_mmsi(db: Session, mmsi: int) -> Optional[Vessel]:
        return db.query(Vessel).filter(Vessel.mmsi == mmsi).first()

    @staticmethod
    def create_or_update(db: Session, data: VesselSchema) -> Vessel:
        existing = db.query(Vessel).filter(Vessel.mmsi == data.mmsi).first()
        if existing:
            existing.vessel_name = data.vessel_name
            existing.vessel_type = data.vessel_type
            existing.flag = data.flag
            if data.imo:
                existing.imo = data.imo
            db.commit()
            db.refresh(existing)
            return existing

        obj = Vessel(
            id=data.id,
            mmsi=data.mmsi,
            imo=data.imo,
            vessel_name=data.vessel_name,
            vessel_type=data.vessel_type,
            flag=data.flag,
            metadata_json=data.metadata_json,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def add_points(db: Session, points: List[AISPointSchema], vessel_id: str):
        for p in points:
            pt = AISPoint(
                id=p.id or f"pt_{p.vessel_id}_{int(p.timestamp.timestamp())}",
                vessel_id=vessel_id,
                timestamp=p.timestamp,
                latitude=p.latitude,
                longitude=p.longitude,
                speed=p.speed,
                course=p.course,
                heading=p.heading,
                navigation_status=p.navigation_status,
            )
            db.merge(pt)
        db.commit()

    @staticmethod
    def get_points(
        db: Session,
        vessel_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AISPoint]:
        query = db.query(AISPoint).filter(AISPoint.vessel_id == vessel_id)
        if start_time:
            query = query.filter(AISPoint.timestamp >= start_time)
        if end_time:
            query = query.filter(AISPoint.timestamp <= end_time)
        return query.order_by(AISPoint.timestamp.asc()).all()
