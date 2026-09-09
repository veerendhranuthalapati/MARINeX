import json
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.repositories.scene_repo import SceneRepository
from app.repositories.slick_repo import SlickRepository
from app.repositories.vessel_repo import VesselRepository
from app.repositories.investigation_repo import InvestigationRepository
from app.schemas.scene import SceneCreate
from app.schemas.slick import SlickCharacterization
from app.schemas.attribution import AttributionRunRequest
from app.schemas.report import InvestigationReportGenerateRequest
from app.api.v1.detection import run_detection
from app.api.v1.attribution import run_vessel_attribution
from app.api.v1.reports import generate_investigation_report
from app.services.ais.csv_provider import CSVAISProvider
from app.core.logging import logger

router = APIRouter(prefix="/demo", tags=["Demo Pipeline"])


@router.post("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """
    Seed database with the full SIH26143 Mumbai Offshore SAR demo scenario:
    - Sentinel-1 SAR Scene
    - Historical AIS vessel traffic
    - Oil slick detection with classical baseline
    """
    logger.info("Executing demo data seeder...")

    # 1. Seed Satellite Scene
    scene_id = "scene_s1a_20260301_arabian_sea_001"
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

    # 3. Seed or trigger detection
    existing_slicks = SlickRepository.list_by_scene(db, scene_id)
    if not existing_slicks:
        created_slicks = run_detection(scene_id=scene_id, method="MOCK", db=db)
        primary_slick_id = created_slicks[0].id if created_slicks else "slick_s1a_20260301_001"
    else:
        primary_slick_id = existing_slicks[0].id

    return {
        "status": "success",
        "message": "Demo scenario seeded successfully with Sentinel-1 scene, AIS traffic, and detected slick.",
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
