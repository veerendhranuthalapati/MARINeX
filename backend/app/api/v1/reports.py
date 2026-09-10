from fastapi import APIRouter, Depends, HTTPException, Response
from datetime import timedelta
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.repositories.slick_repo import SlickRepository
from app.repositories.detection_run_repo import DetectionRunRepository
from app.repositories.investigation_repo import InvestigationRepository
from app.services.environmental.service import EnvironmentalService
from app.services.environmental.quality import EnvironmentQualityChecker
from app.services.data_quality.service import DataQualityService
from app.services.reporting.generator import ReportGeneratorService
from app.schemas.report import InvestigationReportGenerateRequest, InvestigationReportResponse
from app.schemas.slick import SlickResponse
from app.api.v1.attribution import get_slick_candidates
from app.api.v1.drift import get_latest_drift_simulation

router = APIRouter(prefix="/reports", tags=["Investigation Reports"])


@router.post("/{slick_id}/generate", response_model=InvestigationReportResponse)
def generate_investigation_report(
    slick_id: str,
    req: InvestigationReportGenerateRequest,
    db: Session = Depends(get_db),
):
    """
    Generate an official forensic investigation report for an oil spill incident.
    Separates empirical facts, model predictions, assumptions, and candidate vessel evidence.
    """
    slick = SlickRepository.get_by_id(db, slick_id)
    if not slick:
        raise HTTPException(status_code=404, detail=f"Slick '{slick_id}' not found.")

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

    env_service = EnvironmentalService()
    lon, lat = slick.centroid[0], slick.centroid[1]
    env = env_service.get_conditions_for_slick(slick_id, lat, lon, slick.detected_at)

    drift = get_latest_drift_simulation(slick_id, db)
    candidates = get_slick_candidates(slick_id, db)

    # Phase 31: data quality from ACTUAL pipeline inputs (no fabricated grades).
    incident_id = getattr(slick, "incident_id", None)
    runs = DetectionRunRepository.list_for_incident(db, incident_id) if incident_id \
        else DetectionRunRepository.latest_for_scene(db, slick.scene_id)
    detection_run = runs[0] if runs else None
    env_qc = EnvironmentQualityChecker()
    env_quality = env_qc.check_snapshot(
        env_qc.check_window(lat=lat, lon=lon,
                            requested_start=slick.detected_at - timedelta(hours=4),
                            requested_end=slick.detected_at),
        wind_speed_mps=env.wind.speed_mps,
        current_speed_mps=env.ocean_current.speed_mps,
        wave_height_m=env.wave.significant_wave_height_m if env.wave else None,
    ).to_dict()
    data_quality = DataQualityService.assess(
        detection_status=detection_run.status if detection_run else None,
        detection_confidence=slick.confidence,
        env_quality=env_quality,
        drift_ok=bool(drift and drift.probable_origin_centroid and drift.probable_origin_time),
        ais_track_count=len(candidates) if candidates else 0,
    )

    conclusion, conclusion_detail = ReportGeneratorService.derive_conclusion(candidates)

    report = ReportGeneratorService.generate_report(
        slick=slick_schema,
        environmental=env,
        drift_data=drift.model_dump(),
        candidates=candidates,
        analyst_name=req.analyst_name,
        analyst_notes=req.analyst_notes,
        priority_level=req.priority_level or "HIGH",
        data_quality=data_quality,
        conclusion=conclusion,
        conclusion_detail=conclusion_detail,
    )

    # Record report generation in investigation
    InvestigationRepository.create_or_update(
        db=db,
        slick_id=slick_id,
        status="UNDER_INVESTIGATION",
        analyst_notes=req.analyst_notes or "",
    )

    return report


@router.get("/{slick_id}", response_model=InvestigationReportResponse)
def get_report(slick_id: str, db: Session = Depends(get_db)):
    """Retrieve the generated investigation report for an incident."""
    req = InvestigationReportGenerateRequest()
    return generate_investigation_report(slick_id=slick_id, req=req, db=db)


@router.get("/{slick_id}/markdown")
def get_report_markdown(slick_id: str, db: Session = Depends(get_db)):
    """Export the forensic report as raw GitHub Flavored Markdown."""
    req = InvestigationReportGenerateRequest()
    report = generate_investigation_report(slick_id=slick_id, req=req, db=db)
    md_content = ReportGeneratorService.to_markdown(report)
    return Response(content=md_content, media_type="text/markdown")
