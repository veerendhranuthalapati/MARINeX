from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.vessel_repo import VesselRepository
from app.schemas.ais import VesselSchema
from app.api.v1.ais import get_ais_provider

router = APIRouter(prefix="/vessels", tags=["Vessels"])


@router.get("/{vessel_id}", response_model=VesselSchema)
def get_vessel(vessel_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific vessel by ID or MMSI."""
    # Check DB first
    vessel = VesselRepository.get_by_id(db, vessel_id)
    if vessel:
        return VesselSchema(
            id=vessel.id,
            mmsi=vessel.mmsi,
            imo=vessel.imo,
            vessel_name=vessel.vessel_name,
            vessel_type=vessel.vessel_type,
            flag=vessel.flag,
            metadata_json=vessel.metadata_json or {},
            created_at=vessel.created_at,
        )

    # Check AIS provider
    provider = get_ais_provider()
    traj = provider.get_vessel_trajectory(vessel_id)
    if traj:
        return traj.vessel

    raise HTTPException(status_code=404, detail=f"Vessel '{vessel_id}' not found.")
