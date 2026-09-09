from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class VesselCandidate(Base):
    __tablename__ = "vessel_candidates"

    id = Column(String, primary_key=True, index=True)
    slick_id = Column(String, ForeignKey("oil_slicks.id", ondelete="CASCADE"), nullable=False, index=True)
    vessel_id = Column(String, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False, index=True)
    proximity_score = Column(Float, nullable=False)
    temporal_score = Column(Float, nullable=False)
    trajectory_score = Column(Float, nullable=False)
    behavior_score = Column(Float, nullable=False)
    overall_score = Column(Float, nullable=False)
    rank = Column(Integer, default=1)
    confidence = Column(String, default="MEDIUM")  # HIGH, MEDIUM, LOW, EXCLUDED
    evidence = Column(JSON, default=list)  # list of strings
    metrics = Column(JSON, default=dict)  # closest_distance_km, time_delta_minutes, etc.
    recommendation = Column(String, default="")
    evaluated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    slick = relationship("OilSlick", back_populates="candidates")
    vessel = relationship("Vessel", back_populates="candidacies")
