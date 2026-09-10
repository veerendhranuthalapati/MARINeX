"""
Incident-centric investigation API (Phase 2 - Incident as central domain object).

An Incident aggregates scenes, slicks, evidence, drift, and attribution. Every
scientific output carries a status_label (OBSERVED / ML_SEGMENTED / INFERRED /
SIMULATED / PREDICTED / TRACKED / CANDIDATE / DEMO_DATA) and provenance.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.status import StatusLabel, make_provenance
from app.models.scene import SatelliteScene
from app.models.slick import OilSlick
from app.models.incident import Incident
from app.repositories.incident_repo import IncidentRepository
from app.repositories.scene_repo import SceneRepository
from app.repositories.slick_repo import SlickRepository
from app.repositories.detection_run_repo import DetectionRunRepository
from app.repositories.evidence_repo import EvidenceRepository
from app.schemas.incident import (IncidentCreate, IncidentResponse, IncidentDetailResponse,
                                  IncidentListResponse, IncidentUpdate, AttachSceneRequest)
from app.schemas.evidence import EvidenceRecordCreate, EvidenceListResponse, EvidenceRecordResponse
from app.services.detection.service import DetectionService
from app.services.evidence import EvidenceService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


def _serialize(inc, db: Session, scene_count: Optional[int] = None,
               slick_count: Optional[int] = None, ev_count: Optional[int] = None) -> IncidentResponse:
    return IncidentResponse(
        id=inc.id,
        title=inc.title,
        description=inc.description or "",
        incident_time=inc.incident_time,
        detection_time=inc.detection_time,
        centroid=inc.centroid,
        bounding_box=inc.bounding_box,
        scenario=inc.scenario or "DEMO",
        status=inc.status or "OPEN",
        priority_level=inc.priority_level or "HIGH",
        assigned_analyst=inc.assigned_analyst or "",
        analyst_notes=inc.analyst_notes or "",
        ml_model_id=inc.ml_model_id,
        ml_threshold=inc.ml_threshold,
        provenance=inc.provenance or {},
        status_label=inc.status_label or StatusLabel.OBSERVED.value,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        scene_count=scene_count if scene_count is not None else db.query(SatelliteScene)
                    .filter(SatelliteScene.incident_id == inc.id).count(),
        slick_count=slick_count if slick_count is not None else db.query(OilSlick)
                    .filter(OilSlick.incident_id == inc.id).count(),
    )


@router.post("", response_model=IncidentResponse, status_code=201)
def create_incident(data: IncidentCreate, db: Session = Depends(get_db)):
    """Create a new oil spill incident (central domain object)."""
    if data.id and IncidentRepository.get_by_id(db, data.id):
        raise HTTPException(status_code=409, detail=f"Incident '{data.id}' already exists.")
    inc = IncidentRepository.create(db, data)
    inc.status_label = data.occupancy or StatusLabel.OBSERVED.value
    inc.provenance = make_provenance(source="MARINeX Console", source_version="v1",
                                     processing_stage="incident.create",
                                     config={"scenario": data.scenario})
    db.commit()
    db.refresh(inc)
    return _serialize(inc, db)


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    incidents = IncidentRepository.list_all(db, skip=skip, limit=limit)
    return IncidentListResponse(
        total=IncidentRepository.count(db),
        incidents=[_serialize(i, db) for i in incidents],
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    """Retrieve full incident detail: scenes, slicks, and the evidence ledger."""
    inc = IncidentRepository.get_by_id(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    scenes = db.query(SatelliteScene).filter(SatelliteScene.incident_id == incident_id).all()
    slices = db.query(OilSlick).filter(OilSlick.incident_id == incident_id).all()
    evidence = EvidenceRepository.list_for_incident(db, incident_id)

    base = _serialize(inc, db, scene_count=len(scenes), slick_count=len(slices))
    return IncidentDetailResponse(
        **base.model_dump(),
        scenes=scenes,
        slicks=slices,
        evidence_records=evidence,
    )


@router.patch("/{incident_id}", response_model=IncidentResponse)
def update_incident(incident_id: str, data: IncidentUpdate, db: Session = Depends(get_db)):
    if not IncidentRepository.get_by_id(db, incident_id):
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    updated = IncidentRepository.update(db, incident_id, data)
    return _serialize(updated, db)


@router.post("/{incident_id}/scenes", response_model=IncidentResponse)
def attach_scene_to_incident(incident_id: str, req: AttachSceneRequest, db: Session = Depends(get_db)):
    """Attach a satellite scene to an incident (inherits spatial/temporal context)."""
    inc = IncidentRepository.attach_scene(db, incident_id, req.scene_id)
    if not inc:
        raise HTTPException(status_code=404,
                            detail=f"Incident '{incident_id}' or scene '{req.scene_id}' not found.")
    return _serialize(inc, db)


@router.post("/{incident_id}/detect", response_model=Dict[str, Any])
def run_incident_detection(
    incident_id: str,
    scene_id: Optional[str] = Query(None, description="Scene to analyze (default: first attached)"),
    method: str = Query("PRODUCTION_ML"),
    confidence_threshold: float = Query(0.50, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """
    Run the full detection stage on an incident (Phase 3/5/38).

    Chooses the app: the real validated UNet (PRODUCTION_ML), the explainable
    classical baseline, or the deterministic demo geometry (MOCK). Records a
    DetectionRun + evidence; marks incident status NO_SLICKS / LOW_CONFIDENCE /
    UNDER_INVESTIGATION as appropriate.
    """
    inc = IncidentRepository.get_by_id(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    if scene_id:
        scene = SceneRepository.get_by_id(db, scene_id)
    else:
        scene = db.query(SatelliteScene).filter(SatelliteScene.incident_id == incident_id).first()
    if not scene:
        raise HTTPException(status_code=404,
                            detail="No scene available. Pass scene_id or attach a scene first.")

    bbox = inc.bounding_box or scene.bounding_box or [71.15, 19.15, 71.68, 19.55]
    img_source = scene.file_path
    if not img_source or not (settings.BASE_DIR.parent / img_source).exists():
        sample_img = settings.SAMPLES_DIR / "imagery" / "sentinel1_20260301_sar_sample.png"
        img_source = str(sample_img) if sample_img.exists() else None

    service = DetectionService()
    slicks, run_meta = service.run_on_scene(
        db=db, scene_id=scene.id, bbox=bbox, image_source=img_source,
        method=method, incident_id=incident_id, confidence_threshold=confidence_threshold,
    )

    status = run_meta.get("status", DetectionService.NO_SLICKS)
    if status == DetectionService.SLICKS_FOUND:
        new_status = "UNDER_INVESTIGATION"
    elif status == DetectionService.LOW_CONFIDENCE:
        new_status = "LOW_CONFIDENCE"
    else:
        new_status = "NO_SLICKS"
    IncidentRepository.update(db, incident_id, IncidentUpdate(status=new_status,
                                                              status_label=StatusLabel.ML_SEGMENTED.value))

    SceneRepository.update_status(db, scene.id,
                                  "PROCESSED_SLICKS_FOUND" if slicks else "PROCESSED_NO_SLICKS")
    return {"incident_id": incident_id, "scene_id": scene.id,
            "method": method, **run_meta,
            "slicks": [{"id": s.id, "area_km2": s.area_km2, "centroid": s.centroid,
                        "confidence": s.confidence, "eccentricity": s.eccentricity}
                       for s in slicks]}


@router.get("/{incident_id}/evidence", response_model=EvidenceListResponse)
def list_incident_evidence(
    incident_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Retrieve the full evidence ledger for an incident (Phase 22)."""
    if not IncidentRepository.get_by_id(db, incident_id):
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    recs = EvidenceRepository.list_for_incident(db, incident_id, skip=skip, limit=limit)
    return EvidenceListResponse(total=EvidenceRepository.count_for_incident(db, incident_id),
                                evidence_records=recs)


@router.post("/{incident_id}/evidence", response_model=EvidenceRecordResponse, status_code=201)
def add_incident_evidence(incident_id: str, data: EvidenceRecordCreate, db: Session = Depends(get_db)):
    """Analyst may append a manual evidence record (e.g. inspection report)."""
    if not IncidentRepository.get_by_id(db, incident_id):
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    data.incident_id = incident_id
    return EvidenceRepository.create(db, data)


@router.get("/{incident_id}/detection-runs", response_model=List[Dict[str, Any]])
def list_incident_detection_runs(incident_id: str, db: Session = Depends(get_db)):
    """All auditable detection executions on an incident's scenes."""
    runs = DetectionRunRepository.list_for_incident(db, incident_id)
    return [{"run_id": r.id, "scene_id": r.scene_id, "model_id": r.model_id,
             "status": r.status, "confidence": r.confidence, "artifact_path": r.artifact_path,
             "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in runs]


def _primary_slick(db: Session, incident: Incident, require: bool = True):
    """Highest-confidence slick bound to an incident (evidence-driven selection)."""
    slicks = sorted(incident.slicks or [], key=lambda s: (s.confidence or 0.0), reverse=True)
    if not slicks:
        if require:
            raise HTTPException(status_code=404,
                                detail=f"No slicks detected for incident '{incident.id}' yet - run detection first.")
        return None
    return slicks[0]


@router.get("/{incident_id}/drift-reports", response_model=List[Dict[str, Any]])
def list_incident_drift_reports(incident_id: str, db: Session = Depends(get_db)):
    """Drift hindcast/forecast simulations run for every slick in the incident."""
    incident = IncidentRepository.get_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    from app.models.drift import DriftSimulation
    slick_ids = [s.id for s in (incident.slicks or [])]
    if not slick_ids:
        return []
    sims = (db.query(DriftSimulation).filter(DriftSimulation.slick_id.in_(slick_ids))
            .order_by(DriftSimulation.created_at.desc()).all())
    return [{"id": s.id, "slick_id": s.slick_id, "direction": s.direction,
             "start_time": s.start_time.isoformat() if s.start_time else None,
             "end_time": s.end_time.isoformat() if s.end_time else None,
             "model_name": s.model_name, "status": s.status,
             "probable_origin_centroid": s.origin_geometry.get("coordinates")[-1][0]
                if s.origin_geometry and s.origin_geometry.get("coordinates")
                and isinstance(s.origin_geometry["coordinates"], list)
                and s.origin_geometry["coordinates"] else None,
             "uncertainty_km": (s.uncertainty or {}).get("radius_km")}
            for s in sims]


@router.get("/{incident_id}/attribution", response_model=List[Dict[str, Any]])
def list_incident_attribution(incident_id: str, db: Session = Depends(get_db)):
    """Ranked vessel-candidate scores aggregated across the incident's slicks."""
    incident = IncidentRepository.get_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    from app.models.attribution import VesselCandidate
    from app.repositories.vessel_repo import VesselRepository
    slick_ids = [s.id for s in (incident.slicks or [])]
    if not slick_ids:
        return []
    cands = (db.query(VesselCandidate).filter(VesselCandidate.slick_id.in_(slick_ids))
             .order_by(VesselCandidate.overall_score.desc()).all())
    out = []
    for c in cands[:20]:
        vessel = VesselRepository.get_by_id(db, c.vessel_id)
        out.append({
            "candidate_id": c.id, "slick_id": c.slick_id, "vessel_id": c.vessel_id,
            "vessel_name": vessel.vessel_name if vessel else "Unknown",
            "mmsi": vessel.mmsi if vessel else None,
            "rank": c.rank, "overall_score": c.overall_score, "confidence": c.confidence,
            "factors": {"proximity": c.proximity_score, "temporal": c.temporal_score,
                        "trajectory": c.trajectory_score, "behavior": c.behavior_score},
            "closest_distance_km": (c.metrics or {}).get("closest_distance_km"),
            "recommendation": c.recommendation,
        })
    return out


@router.get("/{incident_id}/origin", response_model=Dict[str, Any])
def get_incident_origin(incident_id: str, db: Session = Depends(get_db)):
    """Probable spill origin from the latest hindcast of the primary slick."""
    incident = IncidentRepository.get_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    slick = _primary_slick(db, incident, require=False)
    if not slick:
        raise HTTPException(status_code=404, detail=(
            f"No slicks detected for incident '{incident_id}' yet - run detection first."))
    from app.models.drift import DriftSimulation
    sim = (db.query(DriftSimulation).filter(DriftSimulation.slick_id == slick.id,
                                            DriftSimulation.direction == "HINDCAST")
           .order_by(DriftSimulation.created_at.desc()).first())
    if not sim:
        raise HTTPException(status_code=202, detail=(
            f"No hindcast run yet for slick '{slick.id}'. POST /api/v1/drift/{slick.id}/simulate "
            "with direction=HINDCAST first (environment quality-gated)."))
    return {
        "slick_id": slick.id,
        "model_name": sim.model_name,
        "probable_origin_centroid": (sim.origin_geometry or {}).get("coordinates", [None])[-1][0]
            if (sim.origin_geometry or {}).get("coordinates") else None,
        "probable_origin_time": sim.end_time.isoformat() if sim.end_time else None,
        "uncertainty_km": (sim.uncertainty or {}).get("radius_km"),
        "status_label": "INFERRED",
        "provenance": {"drift_simulation_id": sim.id, "direction": "HINDCAST",
                       "slick_status_label": slick_status_label(slick)},
    }


def slick_status_label(slick: OilSlick) -> str:
    det = (slick.attributes or {}).get("detection")
    return det.get("status_label", "ML_SEGMENTED") if isinstance(det, dict) else "ML_SEGMENTED"


@router.get("/{incident_id}/report", response_model=Dict[str, Any])
def get_incident_report(incident_id: str, db: Session = Depends(get_db)):
    """Consolidated forensic report for the incident (primary slick, evidence-backed)."""
    incident = IncidentRepository.get_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    slick = _primary_slick(db, incident)
    from app.api.v1.reports import generate_investigation_report
    from app.schemas.report import InvestigationReportGenerateRequest
    report = generate_investigation_report(
        slick_id=slick.id,
        req=InvestigationReportGenerateRequest(analyst_name="System (auto)"),
        db=db,
    )
    return {"incident_id": incident_id, "slick_id": slick.id, "report": report.model_dump()}