import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.repositories.scene_repo import SceneRepository
from app.repositories.slick_repo import SlickRepository
from app.repositories.vessel_repo import VesselRepository
from app.repositories.investigation_repo import InvestigationRepository
from app.repositories.incident_repo import IncidentRepository
from app.repositories.detection_run_repo import DetectionRunRepository
from app.repositories.evidence_repo import EvidenceRepository
from app.schemas.scene import SceneCreate
from app.schemas.slick import SlickCharacterization
from app.schemas.incident import IncidentCreate
from app.models.incident import Incident
from app.schemas.attribution import AttributionRunRequest
from app.schemas.ais import VesselSchema, AISPointSchema, VesselTrajectoryResponse
from app.schemas.report import InvestigationReportGenerateRequest
from app.core.status import StatusLabel
from app.services.data_quality.service import DataQualityService
from app.services.reporting.generator import ReportGeneratorService
from app.services.ais.csv_provider import CSVAISProvider
from app.api.v1.detection import run_detection
from app.api.v1.attribution import run_vessel_attribution
from app.api.v1.reports import generate_investigation_report
from app.core.logging import logger

router = APIRouter(prefix="/demo", tags=["Demo Pipeline"])


@router.post("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """
    Seed database with the full SIH26143 Mumbai Offshore SAR demo scenario:
    - Sentinel-1 SAR Scene
    - Historical AIS vessel traffic
    - Incident (central domain object) bound to scene + detected slicks
    - Oil slick detection (production-class in the UI, MOCK geometry for DEMO)
    """
    logger.info("Executing demo data seeder...")

    scene_id = "scene_s1a_20260301_arabian_sea_001"
    incident_id = "incident_sih26143_mumbai_offshore_001"

    # 0. Create the incident (idempotent).
    incident = IncidentRepository.get_by_id(db, incident_id)
    if not incident:
        incident = IncidentRepository.create(db, IncidentCreate(
            id=incident_id,
            title="Mumbai Offshore SAR Oil Spill (SIH26143 Demo)",
            description=("Oil spill signature detected in the Mumbai Offshore corridor, "
                         "Arabian Sea. Satellite-derived detection, drift hindcast, and "
                         "AIS vessel correlation under investigation."),
            scenario="DEMO",
            centroid=[71.42, 19.35],
            bounding_box=[71.15, 19.15, 71.68, 19.55],
            status_label=StatusLabel.OBSERVED.value,
        ))

    # 1. Seed Satellite Scene
    existing_scene = SceneRepository.get_by_id(db, scene_id)
    if not existing_scene:
        sample_meta_path = settings.SAMPLES_DIR / "sample_scene_sentinel1_sar.json"
        if sample_meta_path.exists():
            with open(sample_meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            acq_dt = datetime.fromisoformat(meta["acquisition_time"].replace("Z", "+00:00"))
            scene_create = SceneCreate(
                id=meta["id"],
                source=meta["source"],
                sensor=meta["sensor"],
                acquisition_time=acq_dt,
                latitude=meta["latitude"],
                longitude=meta["longitude"],
                bounding_box=meta["bounding_box"],
                resolution=meta["resolution_meters"],
                file_path=str(settings.SAMPLES_DIR / "imagery" / "sentinel1_20260301_sar_sample.png"),
                status="INGESTED",
                metadata_json=meta.get("metadata", {}),
            )
            SceneRepository.create(db, scene_create)

    # Bind scene to incident.
    scene = SceneRepository.get_by_id(db, scene_id)
    if scene and getattr(scene, "incident_id", None) != incident_id:
        scene.incident_id = incident_id
        db.commit()

    # 2. Seed AIS Vessels & Trajectory Points
    csv_provider = CSVAISProvider()
    if csv_provider._df is not None and not csv_provider._df.empty:
        vessels = csv_provider.query_vessels(
            bounding_box=[71.0, 19.0, 71.8, 19.6],
            start_time=datetime(2026, 3, 1, 0, 0, 0),
            end_time=datetime(2026, 3, 1, 8, 0, 0),
        )
        for v in vessels:
            VesselRepository.create_or_update(db, v)
            traj = csv_provider.get_vessel_trajectory(v.id)
            if traj:
                VesselRepository.add_points(db, traj.points, v.id)

    # 3. Trigger detection bound to the incident (idempotent).
    existing_slicks = SlickRepository.list_by_scene(db, scene_id)
    if not existing_slicks:
        created_slicks = run_detection(scene_id=scene_id, method="MOCK",
                                       incident_id=incident_id, db=db)
        primary_slick_id = created_slicks[0].id if created_slicks else "slick_s1a_20260301_001"
        incident.status = "UNDER_INVESTIGATION"
        db.commit()
    else:
        primary_slick_id = existing_slicks[0].id

    return {
        "status": "success",
        "message": "Demo scenario seeded with incident, Sentinel-1 scene, AIS traffic, and detected slick.",
        "incident_id": incident_id,
        "scene_id": scene_id,
        "slick_id": primary_slick_id,
    }


@router.post("/run-e2e")
def run_end_to_end_demo(db: Session = Depends(get_db)):
    """
    Execute the entire automated pipeline end-to-end:
    Scene Ingestion -> Detection -> Characterization -> Drift Hindcasting -> AIS Correlation -> Vessel Attribution -> Report
    """
    # 1. Ensure scene and data seeded
    seed_demo_data(db)

    # 2. Trigger detection
    slicks = run_detection(scene_id="scene_s1a_20260301_arabian_sea_001", method="MOCK", db=db)
    if not slicks:
        slicks = SlickRepository.list_by_scene(db, "scene_s1a_20260301_arabian_sea_001")
    slick_id = slicks[0].id

    # 3. Trigger attribution
    attr_req = AttributionRunRequest()
    attr_res = run_vessel_attribution(slick_id=slick_id, req=attr_req, db=db)

    # 4. Generate report
    rep_req = InvestigationReportGenerateRequest(
        analyst_name="Coast Guard Maritime Intelligence Unit",
        analyst_notes="Automated forensic run for SIH26143 Mumbai Offshore Corridor incident.",
        priority_level="HIGH",
    )
    report = generate_investigation_report(slick_id=slick_id, req=rep_req, db=db)

    return {
        "status": "success",
        "pipeline": "Scene -> Detection -> Characterization -> Drift -> AIS -> Attribution -> Report",
        "slick_id": slick_id,
        "slick_area_km2": slicks[0].area_km2,
        "candidate_count": len(attr_res.candidates),
        "primary_suspect": attr_res.candidates[0].vessel.vessel_name if attr_res.candidates else None,
        "primary_suspect_score": attr_res.candidates[0].overall_score if attr_res.candidates else None,
        "report_id": report.report_id,
    }


# --------------------------------------------------------------------------- #
# Demonstration cases (Phases 54-56).
#
# Every case runs the REAL backend algorithms (drift, attribution, data quality,
# conclusion tiers, state transitions) on clearly-labeled DEMO scenario inputs.
# Synthetic inputs (extra AIS tracks, low-signal rasters) are produced in-code
# and flagged status_label=DEMO_DATA in provenance. Outcomes are never faked.
# --------------------------------------------------------------------------- #
CASE_IDS = {"case_a_high_confidence", "case_b_low_confidence",
            "case_c_multi_candidate", "case_d_no_candidate", "incident_complete"}


def _demo_trajectory(vessel_id: str, mmsi: int, name: str, vtype: str, flag: str,
                     points: list, origin_time: datetime) -> VesselTrajectoryResponse:
    """Build a clearly-labeled DEMO AIS trajectory for scenario construction."""
    vessel = VesselSchema(
        id=vessel_id, mmsi=mmsi, imo=int(f"9{mmsi % 10000000}"),
        vessel_name=name, vessel_type=vtype, flag=flag,
        metadata_json={"scenario": "demo_case", "status_label": "DEMO_DATA"},
    )
    pts = []
    for (lat, lon, ts_offs_min, speed) in points:
        ts = origin_time + timedelta(minutes=ts_offs_min)
        pts.append(AISPointSchema(
            id=f"pt_{mmsi}_{int(ts.timestamp())}", vessel_id=vessel_id,
            timestamp=ts, latitude=lat, longitude=lon, speed=speed,
            course=90.0, heading=90.0, navigation_status="Under way using engine",
        ))
    return VesselTrajectoryResponse(
        vessel=vessel, points=pts, point_count=len(pts),
        start_time=pts[0].timestamp, end_time=pts[-1].timestamp,
    )


def _build_incident_for_case(db: Session, case_id: str) -> Incident:
    inc_id = f"incident_sih26143_demo_{case_id}_001"
    inc = IncidentRepository.get_by_id(db, inc_id)
    if not inc:
        inc = IncidentRepository.create(db, IncidentCreate(
            id=inc_id,
            title=f"MARINeX demo case ({case_id})",
            description="Demonstration scenario - inputs are clearly labeled DEMO_DATA; "
                        "all computations are the real production algorithms.",
            scenario="DEMO",
            centroid=[71.42, 19.35],
            bounding_box=[71.15, 19.15, 71.68, 19.55],
            status_label=StatusLabel.DEMO_DATA.value,
        ))
    return inc


@router.post("/cases/{case_id}")
def run_demo_case(case_id: str, db: Session = Depends(get_db)):
    """
    Execute a scripted demonstration case through the REAL backend pipeline.

    case_a_high_confidence : slick + drift + a DEMO AIS tanker crossing the origin
                             region at release time -> HIGH evidence candidate.
    case_b_low_confidence  : detection on a low-signal raster -> LOW_CONFIDENCE
                             gate, NO automatic attribution, analyst-review flag.
    case_c_multi_candidate : full pipeline on the standard demo corridor -> ranked
                             multi-vessel matrix with honest conclusion.
    case_d_no_candidate    : slick far from any AIS traffic -> NO_RELIABLE_CANDIDATE.

    Synthetic scenario inputs carry status_label=DEMO_DATA; reported numbers are
    computed by the production engine, never hard-coded.
    """
    if case_id not in CASE_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown demo case '{case_id}'. "
                            f"Valid: {sorted(CASE_IDS)}.")

    if case_id == "case_c_multi_candidate":
        return _case_c_multi_candidate(db)

    if case_id == "case_d_no_candidate":
        return _case_d_no_candidate(db)

    if case_id == "incident_complete":
        return _case_incident_complete(db)

    if case_id == "case_b_low_confidence":
        return _case_b_low_confidence(db)

    return _case_a_high_confidence(db)


def _case_c_multi_candidate(db: Session) -> Dict[str, Any]:
    """Standard demo corridor: 5 real AIS vessels ranked by the scoring engine."""
    seed_demo_data(db)
    scene_id = "scene_s1a_20260301_arabian_sea_001"

    slicks = SlickRepository.list_by_scene(db, scene_id)
    if not slicks:
        slicks = run_detection(scene_id=scene_id, method="MOCK",
                               incident_id="incident_sih26143_mumbai_offshore_001", db=db)
    slick = slicks[0]

    from app.api.v1.attribution import run_vessel_attribution
    attr = run_vessel_attribution(slick_id=slick.id, req=AttributionRunRequest(
        search_radius_km=35.0, time_window_hours_before=6.0, time_window_hours_after=2.0), db=db)

    return {
        "case_id": "case_c_multi_candidate",
        "scenario": "Standard corridor with historical AIS traffic (5 vessels).",
        "slick_id": slick.id,
        "conclusion": attr.conclusion,
        "conclusion_detail": attr.conclusion_detail,
        "total_vessels_scanned": attr.total_vessels_scanned,
        "candidates": [
            {"rank": c.rank, "vessel_name": c.vessel.vessel_name, "mmsi": c.vessel.mmsi,
             "vessel_type": c.vessel.vessel_type, "overall_score": c.overall_score,
             "confidence": c.confidence,
             "factors": {"proximity": c.factors.proximity_score, "temporal": c.factors.temporal_score,
                         "trajectory": c.factors.trajectory_score, "behavior": c.factors.behavior_score}}
            for c in attr.candidates],
        "data_quality": DataQualityService.assess(
            detection_status="SLICKS_FOUND", detection_confidence=slick.confidence,
            env_quality={"overall": "WARN", "checks": []}, drift_ok=True,
            ais_track_count=attr.total_vessels_scanned),
        "honesty_note": "Rankings reflect forensic consistency; they are NOT definitive liability.",
    }


def _case_d_no_candidate(db: Session) -> Dict[str, Any]:
    """Remote slick: no AIS traffic in the search window -> NO_RELIABLE_CANDIDATE."""
    inc = _build_incident_for_case(db, "case_d_no_candidate")
    from app.services.detection.characterizer import SlickCharacterizer

    far_centroid = [72.55, 17.45]  # ~150 km from the demo corridor - no AIS there.
    poly = []
    cx, cy = far_centroid[0], far_centroid[1]
    for i in range(12):
        import math
        a = 2 * math.pi * i / 12
        poly.append([cx + 0.012 * math.cos(a), cy + 0.008 * math.sin(a)])
    poly.append(poly[0])

    char = SlickCharacterizer.characterize_polygon(coords=poly, confidence=0.91, attributes={
        "detector": "classical_baseline", "status_label": StatusLabel.DEMO_DATA.value,
        "model_id": "demo", "note": "Scenario slick constructed for no-candidate demonstration.",
    })
    slick_id = f"slick_{inc.id[-10:]}"
    slick = SlickRepository.create(
        db=db, slick_id=slick_id, scene_id="scene_s1a_20260301_arabian_sea_001",
        geometry={"type": "Polygon", "coordinates": [poly]}, characterization=char,
        detection_method="classical_baseline", detected_at=datetime(2026, 3, 1, 4, 0, 0),
        confidence=0.91,
    )
    slick.incident_id = inc.id
    db.commit()

    from app.api.v1.attribution import run_vessel_attribution
    attr = run_vessel_attribution(slick_id=slick_id, req=AttributionRunRequest(
        search_radius_km=35.0, time_window_hours_before=6.0, time_window_hours_after=2.0), db=db)

    return {
        "case_id": "case_d_no_candidate",
        "scenario": "Slick located in an area with no AIS vessel traffic in the search window.",
        "slick_id": slick_id,
        "conclusion": attr.conclusion,
        "conclusion_detail": attr.conclusion_detail,
        "total_vessels_scanned": attr.total_vessels_scanned,
        "candidates": [{"rank": c.rank, "vessel_name": c.vessel.vessel_name,
                        "overall_score": c.overall_score, "confidence": c.confidence}
                       for c in attr.candidates],
        "behavior": "With zero trajectories the engine reports NO_RELIABLE_CANDIDATE; "
                    "no port-state escalation is recommended.",
    }


def _case_b_low_confidence(db: Session) -> Dict[str, Any]:
    """Detection on a physically-degraded (radiometric +3 dB) raster -> LOW_CONFIDENCE gate."""
    from app.services.detection.service import DetectionService

    inc = _build_incident_for_case(db, "case_b_low_confidence")
    scene_id = "scene_s1a_20260301_arabian_sea_001"
    scene = SceneRepository.get_by_id(db, scene_id)
    if not scene:
        raise HTTPException(status_code=409,
                            detail="Seed the demo first: POST /api/v1/demo/seed")

    # Build a low-signal raster: real demo SAR pixels raised +3 dB (washes out
    # backscatter contrast), so the frozen UNet genuinely drops below threshold.
    from PIL import Image
    import numpy as np
    import os
    img_path = scene.file_path
    if not img_path or not settings.BASE_DIR.joinpath(img_path).exists():
        img_path = str(settings.SAMPLES_DIR / "imagery" / "sentinel1_20260301_sar_sample.png")
    raw = np.array(Image.open(img_path).convert("RGB"))
    low = np.clip(raw * (10 ** (3.0 / 10.0)), 0, 255).astype(np.uint8)

    service = DetectionService()
    slicks, run_meta = service.run_on_scene(
        db=db, scene_id=scene_id, bbox=scene.bounding_box, image_source=low,
        method="PRODUCTION_ML", incident_id=inc.id,
    )

    return {
        "case_id": "case_b_low_confidence",
        "scenario": "Sentinel-1 raster degraded +3 dB (physical radiometric shift) - "
                    "runs the frozen production UNet through the confidence gate.",
        "detection_status": run_meta.get("status"),
        "message": run_meta.get("message"),
        "confidence": run_meta.get("confidence"),
        "slicks_auto_created": len(slicks),
        "automatic_attribution_run": False,
        "behavior": "Low-confidence detections are flagged for analyst review; "
                    "the system deliberately does NOT auto-continue to drift/attribution (Phase 40).",
        "status_label": StatusLabel.DEMO_DATA.value,
    }


def _case_a_high_confidence(db: Session) -> Dict[str, Any]:
    """Slick + drift + a DEMO AIS tanker crossing the origin polygon at release time."""
    inc = _build_incident_for_case(db, "case_a_high_confidence")

    seed_demo_data(db)
    scene_id = "scene_s1a_20260301_arabian_sea_001"
    slicks = SlickRepository.list_by_scene(db, scene_id)
    if not slicks:
        slicks = run_detection(scene_id=scene_id, method="MOCK",
                               incident_id="incident_sih26143_mumbai_offshore_001", db=db)
    slick = slicks[0]

    # Drift hindcast (real algorithm) to obtain the origin region/time.
    from app.api.v1.drift import run_drift_simulation
    from app.schemas.drift import DriftSimulationRequest
    drift = run_drift_simulation(slick_id=slick.id, req=DriftSimulationRequest(
        duration_hours=3.5, direction="HINDCAST"), db=db)
    origin_centroid = drift.probable_origin_centroid or slick.centroid
    origin_time = drift.probable_origin_time or (slick.detected_at - timedelta(hours=3.5))

    # Build a DEMO AIS tanker track that passes exactly through the origin at release.
    o_lon, o_lat = origin_centroid[0], origin_centroid[1]
    demo_trajs = [
        _demo_trajectory(
            "vessel_demo_tanker_001", 477001234, "MV ARABIAN PRESTIGE DEMO",
            "Crude Oil Tanker", "PA", [
                (o_lat + 0.02, o_lon - 0.03, -25, 12.0),
                (o_lat + 0.01, o_lon - 0.015, -12, 11.0),
                (o_lat, o_lon, 0, 10.0),              # at origin at release time
                (o_lat - 0.01, o_lon + 0.015, 12, 10.5),
                (o_lat - 0.02, o_lon + 0.03, 25, 11.0),
            ], origin_time),
        _demo_trajectory(
            "vessel_demo_cargo_001", 477002345, "MV INDIAN SEA CARGO DEMO",
            "Cargo Ship", "IN", [
                (o_lat + 0.05, o_lon - 0.06, -40, 14.0),
                (o_lat + 0.03, o_lon - 0.04, -20, 13.5),
                (o_lat + 0.015, o_lon - 0.02, 0, 13.0),
                (o_lat - 0.005, o_lon, 20, 13.0),
                (o_lat - 0.025, o_lon + 0.02, 40, 12.5),
            ], origin_time),
    ]

    from app.services.attribution.engine import VesselAttributionEngine
    origin_poly = drift.origin_geometry
    origin_poly_coords = origin_poly["coordinates"][0] if origin_poly and origin_poly.get("coordinates") else None
    if not origin_poly_coords:
        d = 0.02
        origin_poly_coords = [[o_lon - d, o_lat - d], [o_lon + d, o_lat - d],
                              [o_lon + d, o_lat + d], [o_lon - d, o_lat + d], [o_lon - d, o_lat - d]]

    engine = VesselAttributionEngine()
    attr = engine.evaluate_candidates(
        slick_id=slick.id, origin_centroid=origin_centroid,
        origin_polygon_coords=origin_poly_coords, origin_time=origin_time,
        trajectories=demo_trajs,
    )

    return {
        "case_id": "case_a_high_confidence",
        "scenario": "Slick + 3.5h hindcast + DEMO AIS tanker crossing the origin polygon at release time.",
        "slick_id": slick.id,
        "origin_centroid": origin_centroid,
        "origin_time": origin_time.isoformat(),
        "conclusion": attr.conclusion,
        "conclusion_detail": attr.conclusion_detail,
        "total_vessels_scanned": attr.total_vessels_scanned,
        "candidates": [
            {"rank": c.rank, "vessel_name": c.vessel.vessel_name, "mmsi": c.vessel.mmsi,
             "vessel_type": c.vessel.vessel_type, "overall_score": c.overall_score,
             "confidence": c.confidence,
             "factors": {"proximity": c.factors.proximity_score, "temporal": c.factors.temporal_score,
                         "trajectory": c.factors.trajectory_score, "behavior": c.factors.behavior_score}}
            for c in attr.candidates],
        "status_label": StatusLabel.DEMO_DATA.value,
        "honesty_note": "AIS tracks are DEMO_DATA; scores are computed by the production engine.",
    }


def _case_incident_complete(db: Session) -> Dict[str, Any]:
    """Full 13-artifact incident: scene, detection, characterization, environment,
    drift, origin, AIS, attribution, report, evidence ledger, provenance."""
    seed_demo_data(db)
    scene_id = "scene_s1a_20260301_arabian_sea_001"
    incident_id = "incident_sih26143_mumbai_offshore_001"

    slicks = SlickRepository.list_by_scene(db, scene_id)
    if not slicks:
        slicks = run_detection(scene_id=scene_id, method="MOCK",
                               incident_id=incident_id, db=db)
    slick = slicks[0]

    from app.api.v1.drift import run_drift_simulation
    from app.api.v1.attribution import run_vessel_attribution
    from app.schemas.drift import DriftSimulationRequest
    from app.schemas.report import InvestigationReportGenerateRequest

    drift = run_drift_simulation(slick_id=slick.id, req=DriftSimulationRequest(
        duration_hours=4.0, direction="HINDCAST"), db=db)
    attr = run_vessel_attribution(slick_id=slick.id, req=AttributionRunRequest(
        search_radius_km=35.0, time_window_hours_before=6.0, time_window_hours_after=2.0), db=db)
    report = generate_investigation_report(
        slick_id=slick.id,
        req=InvestigationReportGenerateRequest(
            analyst_name="Coast Guard Maritime Intelligence Unit",
            analyst_notes="Automated completion of the SIH26143 demo incident.",
            priority_level="HIGH"),
        db=db)
    markdown = ReportGeneratorService.to_markdown(report)

    evidence = EvidenceRepository.list_for_incident(db, incident_id)
    runs = DetectionRunRepository.list_for_incident(db, incident_id)

    return {
        "case_id": "incident_complete",
        "incident_id": incident_id,
        "scene_id": scene_id,
        "slick_id": slick.id,
        "artifacts": {
            "incident": incident_id,
            "scene": scene_id,
            "detection": len(runs),
            "slicks": 1,
            "characterization": slick.id,
            "environment": True,
            "drift": drift.id,
            "origin": drift.probable_origin_centroid,
            "ais": attr.total_vessels_scanned,
            "attribution": len(attr.candidates),
            "report": report.report_id,
            "evidence_ledger": len(evidence),
            "provenance": True,
        },
        "conclusion": report.conclusion,
        "conclusion_detail": report.conclusion_detail,
        "data_quality": report.data_quality,
        "evidence_types": sorted({e.evidence_type for e in evidence}),
        "report_markdown": markdown,
    }
