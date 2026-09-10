from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class SatelliteScene(Base):
    __tablename__ = "satellite_scenes"

    id = Column(String, primary_key=True, index=True)
    source = Column(String, nullable=False)  # e.g., "Copernicus Sentinel-1A"
    sensor = Column(String, nullable=False)  # e.g., "C-SAR"
    acquisition_time = Column(DateTime, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    bounding_box = Column(JSON, nullable=False)  # [min_lon, min_lat, max_lon, max_lat]
    resolution = Column(Float, default=10.0)  # meters
    file_path = Column(String, nullable=True)
    metadata_json = Column(JSON, default=dict)
    status = Column(String, default="INGESTED")  # INGESTED, PROCESSED, ERROR
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="SET NULL"),
                         nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    slicks = relationship("OilSlick", back_populates="scene", cascade="all, delete-orphan")
    incident = relationship("Incident", back_populates="scenes")
