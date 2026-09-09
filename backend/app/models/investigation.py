from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String, primary_key=True, index=True)
    slick_id = Column(String, ForeignKey("oil_slicks.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(String, default="OPEN")  # OPEN, UNDER_INVESTIGATION, ESCALATED, CLOSED
    priority_level = Column(String, default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    assigned_analyst = Column(String, default="Coast Guard Duty Officer")
    analyst_notes = Column(Text, default="")
    report_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    slick = relationship("OilSlick", back_populates="investigation")
