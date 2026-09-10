from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Text, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    incident_time = Column(DateTime, nullable=True)
    detection_time = Column(DateTime, nullable=True)
    centroid = Column(JSON, nullable=True)            # [lon, lat]
    bounding_box = Column(JSON, nullable=True)         # [min_lon, min_lat, max_lon, max_lat]
    scenario = Column(String, default="DEMO")         # DEMO, OPERATIONAL, EXPERIMENTAL
    status = Column(String, default="OPEN")           # OPEN, UNDER_INVESTIGATION, ESCALATED, CLOSED, NO_SLICKS, LOW_CONFIDENCE
    priority_level = Column(String, default="HIGH")   # CRITICAL, HIGH, MEDIUM, LOW
    assigned_analyst = Column(String, default="Coast Guard Duty Officer")
    analyst_notes = Column(Text, default="")
    ml_model_id = Column(String, nullable=True)
    ml_threshold = Column(Float, nullable=True)
    provenance = Column(JSON, default=dict)
    status_label = Column(String, default="OBSERVED") # OBSERVED, INFERRED, SIMULATED, PREDICTED, TRACKED, CANDIDATE
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    scenes = relationship("SatelliteScene", back_populates="incident")
    slicks = relationship("OilSlick", back_populates="incident")
    evidence_records = relationship("EvidenceRecord", back_populates="incident",
                                    cascade="all, delete-orphan")
    jobs = relationship("AsyncJob", back_populates="incident",
                        cascade="all, delete-orphan")
