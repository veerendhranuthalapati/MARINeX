from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class AsyncJob(Base):
    __tablename__ = "async_jobs"

    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"),
                         index=True, nullable=True)
    job_type = Column(String, nullable=False)       # detection, drift, attribution, report, environment, ais
    status = Column(String, default="PENDING")       # PENDING, RUNNING, COMPLETED, FAILED
    progress_pct = Column(String, default="0")       # 0-100 if measurable
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    result = Column(JSON, default=dict)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="jobs")
