from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, JSON
from app.core.database import Base


class EnvironmentalSnapshot(Base):
    __tablename__ = "environmental_snapshots"

    id = Column(String, primary_key=True, index=True)
    slick_id = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    wind_speed = Column(Float, nullable=False)  # m/s
    wind_direction = Column(Float, nullable=False)  # deg
    ocean_current_u = Column(Float, nullable=False)  # m/s eastward
    ocean_current_v = Column(Float, nullable=False)  # m/s northward
    wave_height = Column(Float, default=1.0)  # meters
    source = Column(String, default="Copernicus Marine / ERA5")
    raw_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
