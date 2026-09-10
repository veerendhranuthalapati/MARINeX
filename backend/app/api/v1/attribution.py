from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.slick_repo import SlickRepository
from app.repositories.investigation_repo import InvestigationRepository
from app.repositories.vessel_repo import VesselRepository
from app.services.attribution.engine import VesselAttributionEngine
from app.services.drift.service import MockDriftService
from app.services.environmental.service import EnvironmentalService
from app.services.evidence import EvidenceService
from app.api.v1.ais import get_ais_provider
from app.schemas.attribution import (
    AttributionRunRequest,
    AttributionResultsResponse,
    VesselCandidateResponse,
    FactorBreakdown,
    CandidateMetrics,
)
from app.schemas.ais import VesselSchema
from app.schemas.drift import DriftSimulationRequest

router = APIRouter(tags=["Vessel Attribution Engine"])


@router.post("/attribution/{slick_id}/run", response_model=AttributionResultsResponse)
def run_vessel_attribution(
    slick_id: str,
    req: AttributionRunRequest,
    db: Session = Depends(get_db),
):
    """
    Execute explainable multi-factor vessel attribution for an oil slick.
    Correlates AIS trajectories with drift hindcast origin to produce ranked candidate polluters.
    """
    slick = SlickRepository.get_by_id(db, slick_id)
    if not slick:
        raise HTTPException(status_code=404, detail=f"Slick '{slick_id}' not found.")

    # 1. Obtain environmental conditions & run drift hindcast to find origin
    env_service = EnvironmentalService()
    lon, lat = slick.centroid[0], slick.centroid[1]
    env = env_service.get_conditions_for_slick(slick_id, lat, lon, slick.detected_at)

    drift_service = MockDriftService()
    drift_req = DriftSimulationRequest(
        duration_hours=req.time_window_hours_before,
        direction="HINDCAST",
    )
    drift_res = drift_service.simulate(
        slick_id=slick_id,
        centroid=slick.centroid,
        start_time=slick.detected_at,
        req=drift_req,
        wind_u=env.wind.u_component_mps,
        wind_v=env.wind.v_component_mps,
        current_u=env.ocean_current.u_component_mps,
        current_v=env.ocean_current.v_component_mps,
    )

    origin_centroid = drift_res.probable_origin_centroid or slick.centroid
    origin_time = drift_res.probable_origin_time or (slick.detected_at - timedelta(hours=3.5))

    origin_poly = drift_res.origin_geometry
    if origin_poly and "coordinates" in origin_poly and origin_poly["coordinates"]:
        origin_poly_coords = origin_poly["coordinates"][0]
    else:
        # Fallback small buffer
        o_lon, o_lat = origin_centroid[0], origin_centroid[1]
        origin_poly_coords = [
            [o_lon - 0.02, o_lat - 0.02],
            [o_lon + 0.02, o_lat - 0.02],
            [o_lon + 0.02, o_lat + 0.02],
            [o_lon - 0.02, o_lat + 0.02],
            [o_lon - 0.02, o_lat - 0.02],
        ]

    # 2. Query AIS trajectories in spatio-temporal search window
    ais_provider = get_ais_provider()
    # Search bbox around origin and slick
    delta_deg = req.search_radius_km / 111.0
    search_bbox = [
        min(origin_centroid[0], slick.centroid[0]) - delta_deg,
        min(origin_centroid[1], slick.centroid[1]) - delta_deg,
        max(origin_centroid[0], slick.centroid[0]) + delta_deg,
        max(origin_centroid[1], slick.centroid[1]) + delta_deg,
    ]

    t_start = origin_time - timedelta(hours=req.time_window_hours_before)
    t_end = slick.detected_at + timedelta(hours=req.time_window_hours_after)

    trajectories = ais_provider.get_all_trajectories_in_window(search_bbox, t_start, t_end)

    # 3. Score and rank candidates using explainable 4-factor engine
    engine = VesselAttributionEngine(weights=req.weights)
    results = engine.evaluate_candidates(
        slick_id=slick_id,
        origin_centroid=origin_centroid,
        origin_polygon_coords=origin_poly_coords,
        origin_time=origin_time,
        trajectories=trajectories,
        weights_override=req.weights,
    )

    # 4. Save candidates to database
    for cand in results.candidates:
        # Save vessel in DB if not present
        VesselRepository.create_or_update(db, cand.vessel)
    InvestigationRepository.save_candidates(db, results.candidates)

    # Ensure investigation record exists
    InvestigationRepository.create_or_update(
        db=db,
        slick_id=slick_id,
        status="UNDER_INVESTIGATION",
        priority_level="HIGH" if (results.candidates and results.candidates[0].overall_score >= 70) else "MEDIUM",
    )

    # Phase 21: record AIS correlation + attribution evidence on the incident ledger.
    incident_id = getattr(slick, "incident_id", None)
    if incident_id:
        EvidenceService.record_ais(
            db, incident_id=incident_id, slick_id=slick_id,
            vessel_count=len(trajectories),
            query_window={"search_bbox": search_bbox,
                          "t_start": t_start.isoformat(), "t_end": t_end.isoformat()},
        )
        EvidenceService.record_attribution(
            db, incident_id=incident_id, slick_id=slick_id, results=results)

    return results


@router.get("/candidates/{slick_id}", response_model=List[VesselCandidateResponse])
def get_slick_candidates(slick_id: str, db: Session = Depends(get_db)):
    """Retrieve ranked candidate polluters previously evaluated for this oil slick."""
    db_cands = InvestigationRepository.get_candidates_for_slick(db, slick_id)
    if not db_cands:
        # If not evaluated yet, run attribution automatically with default parameters
        req = AttributionRunRequest()
        res = run_vessel_attribution(slick_id=slick_id, req=req, db=db)
        return res.candidates

    items = []
    for c in db_cands:
        vessel = VesselRepository.get_by_id(db, c.vessel_id)
        vessel_schema = (
            VesselSchema(
                id=vessel.id,
                mmsi=vessel.mmsi,
                imo=vessel.imo,
                vessel_name=vessel.vessel_name,
                vessel_type=vessel.vessel_type,
                flag=vessel.flag,
            )
            if vessel
            else VesselSchema(
                id=c.vessel_id,
                mmsi=0,
                vessel_name="Unknown Vessel",
                vessel_type="Unknown",
            )
        )

        metrics_dict = c.metrics or {}
        items.append(
            VesselCandidateResponse(
                id=c.id,
                slick_id=c.slick_id,
                vessel_id=c.vessel_id,
                vessel=vessel_schema,
                rank=c.rank,
                overall_score=c.overall_score,
                confidence=c.confidence,
                factors=FactorBreakdown(
                    proximity_score=c.proximity_score,
                    temporal_score=c.temporal_score,
                    trajectory_score=c.trajectory_score,
                    behavior_score=c.behavior_score,
                ),
                metrics=CandidateMetrics(
                    closest_distance_km=metrics_dict.get("closest_distance_km", 0.0),
                    time_delta_minutes=metrics_dict.get("time_delta_minutes", 0.0),
                    trajectory_intersects_origin=metrics_dict.get("trajectory_intersects_origin", False),
                    transit_speed_knots=metrics_dict.get("transit_speed_knots", 0.0),
                    speed_anomaly_detected=metrics_dict.get("speed_anomaly_detected", False),
                ),
                evidence=c.evidence or [],
                recommendation=c.recommendation or "",
                evaluated_at=c.evaluated_at,
            )
        )
    return items
