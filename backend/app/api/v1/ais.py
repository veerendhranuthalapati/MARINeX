from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.ais.csv_provider import CSVAISProvider
from app.services.ais.mock_provider import MockAISProvider
from app.schemas.ais import VesselSchema, AISQueryRequest, VesselTrajectoryResponse

router = APIRouter(prefix="/ais", tags=["AIS Vessel Intelligence"])


import functools


@functools.lru_cache(maxsize=1)
def get_ais_provider():
    # Prefer CSV provider with sample data; fallback to mock if empty
    csv_p = CSVAISProvider()
    if csv_p._df is not None and not csv_p._df.empty:
        return csv_p
    return MockAISProvider()


@router.post("/query", response_model=List[VesselSchema])
def query_vessels(req: AISQueryRequest):
    """Query vessels transiting a geographic bounding box during a specific time window."""
    provider = get_ais_provider()
    return provider.query_vessels(
        bounding_box=req.bounding_box,
        start_time=req.start_time,
        end_time=req.end_time,
        vessel_types=req.vessel_types,
    )


@router.get("/trajectories/{vessel_id}", response_model=VesselTrajectoryResponse)
def get_vessel_trajectory(
    vessel_id: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
):
    """Retrieve full chronological trajectory breadcrumbs for a vessel."""
    provider = get_ais_provider()
    traj = provider.get_vessel_trajectory(vessel_id, start_time, end_time)
    if not traj:
        raise HTTPException(status_code=404, detail=f"Trajectory for vessel '{vessel_id}' not found.")
    return traj


@router.get("/corridor/all", response_model=List[VesselTrajectoryResponse])
def get_all_corridor_trajectories(
    min_lon: float = Query(71.0),
    min_lat: float = Query(19.0),
    max_lon: float = Query(71.8),
    max_lat: float = Query(19.6),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
):
    """Retrieve all vessel trajectories within the shipping corridor for map visualization."""
    provider = get_ais_provider()
    bbox = [min_lon, min_lat, max_lon, max_lat]
    t0 = start_time or datetime(2026, 3, 1, 0, 0, 0)
    t1 = end_time or datetime(2026, 3, 1, 8, 0, 0)
    return provider.get_all_trajectories_in_window(bbox, t0, t1)
