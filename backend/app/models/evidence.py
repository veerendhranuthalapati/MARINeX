from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"),
                         index=True, nullable=False)
    evidence_type = Column(String, nullable=False)     # SATELLITE, DETECTION, SLICK, DRIFT, ORIGIN, AIS, CANDIDATE, ENVIRONMENT, REPORT
    source = Column(String, nullable=False)             # e.g. "Sentinel-1 C-SAR", "MARINeX-UNet-V1", "ERA5", "AIS CSV", "OpenDrift"
    source_version = Column(String, default="")
    status_label = Column(String, default="OBSERVED")  # OBSERVED, INFERRED, SIMULATED, PREDICTED, TRACKED, CANDIDATE, DEMO_DATA
    confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    title = Column(String, nullable=False)
    summary = Column(Text, default="")
    value = Column(JSON, default=dict)                 # structured payload
    provenance = Column(JSON, default=dict)            # model, config, processing_stage, etc.
    related_entity_type = Column(String, nullable=True)  # slick, drift, candidate, scene
    related_entity_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="evidence_records")
