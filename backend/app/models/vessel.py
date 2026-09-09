from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Vessel(Base):
    __tablename__ = "vessels"

    id = Column(String, primary_key=True, index=True)
    mmsi = Column(Integer, unique=True, index=True, nullable=False)
    imo = Column(Integer, nullable=True, index=True)
    vessel_name = Column(String, nullable=False, index=True)
    vessel_type = Column(String, nullable=False)  # Tanker, Cargo, Tug, Fishing, etc.
    flag = Column(String, default="Unknown")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    ais_points = relationship("AISPoint", back_populates="vessel", cascade="all, delete-orphan")
    candidacies = relationship("VesselCandidate", back_populates="vessel", cascade="all, delete-orphan")


class AISPoint(Base):
    __tablename__ = "ais_points"

    id = Column(String, primary_key=True, index=True)
    vessel_id = Column(String, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, default=0.0)  # SOG in knots
    course = Column(Float, default=0.0)  # COG in degrees
    heading = Column(Float, default=0.0)  # True heading
    navigation_status = Column(String, default="Under way using engine")

    vessel = relationship("Vessel", back_populates="ais_points")
