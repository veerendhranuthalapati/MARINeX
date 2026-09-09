from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.slick_repo import SlickRepository
from app.services.environmental.service import EnvironmentalService
from app.schemas.environment import EnvironmentalSnapshotResponse

router = APIRouter(prefix="/environment", tags=["Environmental Data"])


@router.get("/{slick_id}", response_model=EnvironmentalSnapshotResponse)
def get_environmental_conditions(slick_id: str, db: Session = Depends(get_db)):
    """Retrieve wind, current, and wave conditions corresponding to the slick location and time."""
    slick = SlickRepository.get_by_id(db, slick_id)
    if not slick:
        raise HTTPException(status_code=404, detail=f"Slick '{slick_id}' not found.")

    env_service = EnvironmentalService()
    lon, lat = slick.centroid[0], slick.centroid[1]
    return env_service.get_conditions_for_slick(
        slick_id=slick_id,
        lat=lat,
        lon=lon,
        timestamp=slick.detected_at,
    )
