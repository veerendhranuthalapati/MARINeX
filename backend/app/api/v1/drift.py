from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.slick_repo import SlickRepository
from app.models.drift import DriftSimulation
from app.services.drift.service import MockDriftService
from app.services.environmental.service import EnvironmentalService
from app.schemas.drift import DriftSimulationRequest, DriftSimulationResponse

router = APIRouter(prefix="/drift", tags=["Drift Simulation & Hindcasting"])


@router.post("/{slick_id}/simulate", response_model=DriftSimulationResponse)
def run_drift_simulation(
    slick_id: str,
    req: DriftSimulationRequest,
    db: Session = Depends(get_db),
):
    """
    Execute Lagrangian oil drift simulation or backward hindcasting.
    Generates probable origin region, uncertainty polygon, and particle dispersion cloud.
    """
    slick = SlickRepository.get_by_id(db, slick_id)
    if not slick:
        raise HTTPException(status_code=404, detail=f"Slick '{slick_id}' not found.")

    env_service = EnvironmentalService()
    lon, lat = slick.centroid[0], slick.centroid[1]
    env = env_service.get_conditions_for_slick(slick_id, lat, lon, slick.detected_at)

    drift_service = MockDriftService()
    sim_res = drift_service.simulate(
        slick_id=slick_id,
        centroid=slick.centroid,
        start_time=slick.detected_at,
        req=req,
        wind_u=env.wind.u_component_mps,
        wind_v=env.wind.v_component_mps,
        current_u=env.ocean_current.u_component_mps,
        current_v=env.ocean_current.v_component_mps,
    )

    # Persist simulation in DB
    sim_db = DriftSimulation(
        id=sim_res.id,
        slick_id=slick_id,
        start_time=sim_res.start_time,
        end_time=sim_res.end_time,
        direction=sim_res.direction,
        model_name=sim_res.model_name,
        parameters=sim_res.parameters,
        origin_geometry=sim_res.origin_geometry,
        trajectory_geometry=sim_res.trajectory_geometry,
        particles=sim_res.particles,
        uncertainty=sim_res.uncertainty,
        status=sim_res.status,
    )
    db.add(sim_db)
    db.commit()

    return sim_res


@router.get("/{slick_id}", response_model=DriftSimulationResponse)
def get_latest_drift_simulation(slick_id: str, db: Session = Depends(get_db)):
    """Retrieve the latest drift simulation/hindcast executed for this oil slick."""
    sim = (
        db.query(DriftSimulation)
        .filter(DriftSimulation.slick_id == slick_id)
        .order_by(DriftSimulation.created_at.desc())
        .first()
    )
    if not sim:
        # If no simulation run yet, run a default 4-hour hindcast automatically
        req = DriftSimulationRequest(duration_hours=4.0, direction="HINDCAST")
        return run_drift_simulation(slick_id=slick_id, req=req, db=db)

    # Reconstruct origin centroid and time from parameters/geometry
    origin_centroid = None
    origin_time = sim.end_time if sim.direction == "HINDCAST" else sim.start_time
    if sim.trajectory_geometry and "coordinates" in sim.trajectory_geometry:
        coords = sim.trajectory_geometry["coordinates"]
        if coords:
            origin_centroid = coords[-1]

    return DriftSimulationResponse(
        id=sim.id,
        slick_id=sim.slick_id,
        direction=sim.direction,
        start_time=sim.start_time,
        end_time=sim.end_time,
        model_name=sim.model_name,
        parameters=sim.parameters or {},
        origin_geometry=sim.origin_geometry,
        trajectory_geometry=sim.trajectory_geometry,
        particles=sim.particles or [],
        uncertainty=sim.uncertainty or {},
        probable_origin_time=origin_time,
        probable_origin_centroid=origin_centroid,
        status=sim.status,
        created_at=sim.created_at,
    )
