from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class DriftSimulation(Base):
    __tablename__ = "drift_simulations"

    id = Column(String, primary_key=True, index=True)
    slick_id = Column(String, ForeignKey("oil_slicks.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    direction = Column(String, default="HINDCAST")  # HINDCAST or FORECAST
    model_name = Column(String, default="LAGRANGIAN_MONTE_CARLO_DRIFT_v1")
    parameters = Column(JSON, default=dict)
    origin_geometry = Column(JSON, nullable=True)  # GeoJSON Polygon / MultiPoint
    trajectory_geometry = Column(JSON, nullable=True)  # GeoJSON LineString
    particles = Column(JSON, default=list)  # list of particle coordinates
    uncertainty = Column(JSON, default=dict)
    status = Column(String, default="COMPLETED")  # PENDING, RUNNING, COMPLETED, FAILED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    slick = relationship("OilSlick", back_populates="drift_simulations")
