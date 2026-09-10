from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class OilSlick(Base):
    __tablename__ = "oil_slicks"

    id = Column(String, primary_key=True, index=True)
    scene_id = Column(String, ForeignKey("satellite_scenes.id", ondelete="CASCADE"), nullable=False)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="SET NULL"),
                         nullable=True, index=True)
    geometry = Column(JSON, nullable=False)  # GeoJSON Polygon dict
    area_km2 = Column(Float, nullable=False)
    perimeter_km = Column(Float, nullable=False)
    centroid = Column(JSON, nullable=False)  # [longitude, latitude]
    confidence = Column(Float, default=0.85)
    detection_method = Column(String, nullable=False)
    detected_at = Column(DateTime, nullable=False)
    length_km = Column(Float, default=0.0)
    width_km = Column(Float, default=0.0)
    orientation_deg = Column(Float, default=0.0)
    compactness = Column(Float, default=0.0)
    eccentricity = Column(Float, default=0.0)
    attributes = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    scene = relationship("SatelliteScene", back_populates="slicks")
    incident = relationship("Incident", back_populates="slicks")
    drift_simulations = relationship("DriftSimulation", back_populates="slick", cascade="all, delete-orphan")
    candidates = relationship("VesselCandidate", back_populates="slick", cascade="all, delete-orphan")
    investigation = relationship("Investigation", back_populates="slick", uselist=False, cascade="all, delete-orphan")
