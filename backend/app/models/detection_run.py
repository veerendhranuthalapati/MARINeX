from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class DetectionRun(Base):
    """One auditable inference execution on a scene.

    Stores BOTH the raw model output and the post-processed mask reference, so
    predictions are never silently overwritten (Phase 3). The artifact file
    (.npz) contains probs/raw_mask/post_mask.
    """

    __tablename__ = "detection_runs"

    id = Column(String, primary_key=True, index=True)
    scene_id = Column(String, ForeignKey("satellite_scenes.id", ondelete="CASCADE"),
                      index=True, nullable=False)
    incident_id = Column(String, index=True, nullable=True)
    model_id = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    preprocessing_version = Column(String, nullable=True)
    threshold = Column(Float, nullable=True)
    status = Column(String, default="SLICKS_FOUND")  # SLICKS_FOUND, NO_SLICKS, LOW_CONFIDENCE, ERROR
    artifact_path = Column(String, nullable=True)     # .npz with probs/raw_mask/post_mask
    method = Column(String, default="PRODUCTION_ML")
    confidence = Column(Float, nullable=True)
    metadata_json = Column(JSON, default=dict)        # full provenance
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    scene = relationship("SatelliteScene", primaryjoin="DetectionRun.scene_id==SatelliteScene.id")