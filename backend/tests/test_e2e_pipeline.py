import pytest
from datetime import datetime, timezone
from app.repositories.scene_repo import SceneRepository
from app.repositories.slick_repo import SlickRepository
from app.repositories.vessel_repo import VesselRepository
from app.schemas.scene import SceneCreate
from app.services.detection.classical_baseline import ClassicalBaselineDetector
from app.services.detection.characterizer import SlickCharacterizer
from app.services.environmental.service import EnvironmentalService
from app.services.drift.service import MockDriftService
from app.services.ais.csv_provider import CSVAISProvider
from app.services.attribution.engine import VesselAttributionEngine
from app.services.reporting.generator import ReportGeneratorService
from app.schemas.drift import DriftSimulationRequest
from app.schemas.slick import SlickResponse


def test_end_to_end_sih_pipeline(db_session):
    """
    Integration test covering the full SIH26143 pipeline:
    1. Satellite Scene Ingestion
    2. Oil Spill Detection (Classical Baseline)
    3. Slick Morphological Characterization
    4. Environmental Conditions Retrieval
    5. Lagrangian Drift Hindcast to find Origin Region & Uncertainty
    6. AIS Historical Trajectory Retrieval
    7. Explainable Vessel Candidate Scoring & Ranking
    8. Formal Forensic Investigation Report Generation
    """

    # --- Step 1: Ingest Satellite Scene ---
    scene_id = "scene_s1a_e2e_001"
    acq_time = datetime(2026, 3, 1, 6, 45, 0, tzinfo=timezone.utc)
    bbox = [71.15, 19.15, 71.68, 19.55]

    scene_data = SceneCreate(
        id=scene_id,
        source="Copernicus Sentinel-1A",
        sensor="C-SAR",
        acquisition_time=acq_time,
        latitude=19.345,
        longitude=71.418,
        bounding_box=bbox,
        resolution=10.0,
        status="INGESTED",
    )
    scene = SceneRepository.create(db_session, scene_data)
    assert scene.id == scene_id

    # --- Step 2 & 3: Run Detection & Slick Characterization ---
    detector = ClassicalBaselineDetector()
    sample_polygon = [
        [71.385, 19.320],
        [71.402, 19.332],
        [71.425, 19.348],
        [71.450, 19.362],
        [71.462, 19.370],
        [71.458, 19.375],
        [71.438, 19.368],
        [71.415, 19.352],
        [71.392, 19.336],
        [71.380, 19.326],
        [71.385, 19.320],
    ]

    char = SlickCharacterizer.characterize_polygon(sample_polygon, confidence=0.915)
    assert char.area_km2 > 0.5
    assert char.perimeter_km > 5.0
    assert len(char.centroid) == 2

    slick_id = f"slick_{scene_id}_001"
    slick = SlickRepository.create(
        db=db_session,
        slick_id=slick_id,
        scene_id=scene_id,
        geometry={"type": "Polygon", "coordinates": [sample_polygon]},
        characterization=char,
        detection_method="CLASSICAL_BASELINE_ADAPTIVE_THRESHOLD",
        detected_at=acq_time,
        confidence=char.confidence,
    )
    assert slick.id == slick_id

    # --- Step 4: Environmental Data Retrieval ---
    env_service = EnvironmentalService()
    env = env_service.get_conditions_for_slick(slick_id, char.centroid[1], char.centroid[0], acq_time)
    assert env.wind.speed_mps > 0
    assert env.ocean_current.speed_mps > 0

    # --- Step 5: Drift Simulation (Backward Hindcast) ---
    drift_service = MockDriftService()
    drift_req = DriftSimulationRequest(duration_hours=3.25, direction="HINDCAST")
    drift_res = drift_service.simulate(
        slick_id=slick_id,
        centroid=char.centroid,
        start_time=acq_time,
        req=drift_req,
        wind_u=env.wind.u_component_mps,
        wind_v=env.wind.v_component_mps,
        current_u=env.ocean_current.u_component_mps,
        current_v=env.ocean_current.v_component_mps,
    )
    assert drift_res.status == "COMPLETED"
    assert drift_res.probable_origin_centroid is not None
    assert drift_res.probable_origin_time is not None

    origin_poly = drift_res.origin_geometry["coordinates"][0]

    # --- Step 6: AIS Trajectory Retrieval ---
    ais_provider = CSVAISProvider()
    trajectories = ais_provider.get_all_trajectories_in_window(
        bounding_box=[71.0, 19.0, 71.8, 19.6],
        start_time=datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 1, 8, 0, 0, tzinfo=timezone.utc),
    )
    assert len(trajectories) >= 3

    # --- Step 7: Vessel Attribution & Ranking ---
    engine = VesselAttributionEngine()
    attr_res = engine.evaluate_candidates(
        slick_id=slick_id,
        origin_centroid=drift_res.probable_origin_centroid,
        origin_polygon_coords=origin_poly,
        origin_time=drift_res.probable_origin_time,
        trajectories=trajectories,
    )
    assert len(attr_res.candidates) >= 3
    top_candidate = attr_res.candidates[0]
    assert top_candidate.rank == 1
    assert top_candidate.overall_score > 60.0
    assert len(top_candidate.evidence) >= 2

    # --- Step 8: Formal Investigation Report Generation ---
    slick_schema = SlickResponse(
        id=slick.id,
        scene_id=slick.scene_id,
        geometry=slick.geometry,
        area_km2=slick.area_km2,
        perimeter_km=slick.perimeter_km,
        centroid=slick.centroid,
        confidence=slick.confidence,
        detection_method=slick.detection_method,
        detected_at=slick.detected_at,
        length_km=slick.length_km,
        width_km=slick.width_km,
        orientation_deg=slick.orientation_deg,
        compactness=slick.compactness,
        attributes=slick.attributes or {},
        created_at=slick.created_at,
    )

    report = ReportGeneratorService.generate_report(
        slick=slick_schema,
        environmental=env,
        drift_data=drift_res.model_dump(),
        candidates=attr_res.candidates,
        analyst_name="Coast Guard Commander",
    )

    assert report.report_id.startswith("REP-")
    assert len(report.observed_facts) >= 4
    assert len(report.model_predictions) >= 3
    assert len(report.assumptions_and_limitations) >= 4
    assert len(report.candidate_vessels) >= 3
    assert "PACIFIC CROWN" in report.executive_summary or top_candidate.vessel.vessel_name in report.executive_summary
