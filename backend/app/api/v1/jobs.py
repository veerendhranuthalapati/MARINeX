"""
Async job API (Phase 26-28). Heavy pipeline stages (detection, drift, attribution,
report, environment) are launched as jobs so the frontend can poll progress.
"""

import threading
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.logging import logger
from app.repositories.async_job_repo import AsyncJobRepository
from app.repositories.incident_repo import IncidentRepository
from app.schemas.async_job import AsyncJobCreate, AsyncJobResponse

router = APIRouter(prefix="/jobs", tags=["Async Jobs"])


def _execute_stage(odb: Session, job_type: str, scene_id: Optional[str],
                   slick_id: Optional[str]) -> Dict[str, Any]:
    if job_type == "detection":
        from app.services.detection.service import DetectionService
        slicks, meta = DetectionService().run_on_scene(
            db=odb, scene_id=scene_id or "", bbox=[71.15, 19.15, 71.68, 19.55],
            image_source=None, method="PRODUCTION_ML", incident_id=None)
        return meta
    if job_type == "attribution":
        if not slick_id:
            raise ValueError("attribution job requires slick_id")
        from app.api.v1.attribution import run_vessel_attribution
        from app.schemas.attribution import AttributionRunRequest
        res = run_vessel_attribution(slick_id=slick_id, req=AttributionRunRequest(), db=odb)
        return {"candidate_count": len(res.candidates),
                "top": res.candidates[0].vessel.vessel_name if res.candidates else None}
    if job_type == "drift":
        from app.api.v1.drift import run_drift_simulation
        from app.schemas.drift import DriftSimulationRequest
        res = run_drift_simulation(slick_id=slick_id or "",
                                   req=DriftSimulationRequest(direction="HINDCAST"), db=odb)
        return {"sim_id": res.id, "direction": res.direction,
                "probable_origin": res.probable_origin_centroid}
    if job_type == "report":
        from app.api.v1.reports import generate_investigation_report
        from app.schemas.report import InvestigationReportGenerateRequest
        rep = generate_investigation_report(
            slick_id=slick_id or "",
            req=InvestigationReportGenerateRequest(analyst_name="Automated Job Runner"), db=odb)
        return {"report_id": rep.report_id}
    raise ValueError(f"Unsupported job_type {job_type}")


@router.post("", response_model=AsyncJobResponse, status_code=201)
def create_job(
    data: AsyncJobCreate,
    db: Session = Depends(get_db),
):
    """Create a PENDING job for a stage. Job types: detection, drift, attribution, report, environment."""
    if data.incident_id and not IncidentRepository.get_by_id(db, data.incident_id):
        raise HTTPException(status_code=404, detail=f"Incident '{data.incident_id}' not found.")
    allowed = {"detection", "drift", "attribution", "report", "environment"}
    if data.job_type not in allowed:
        raise HTTPException(status_code=422, detail=f"Unknown job_type '{data.job_type}'. Allowed: {sorted(allowed)}.")
    return AsyncJobRepository.create(db, data)


@router.get("/{job_id}", response_model=AsyncJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Poll the job status (PENDING / RUNNING / COMPLETED / FAILED) and progress."""
    job = AsyncJobRepository.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@router.post("/{job_id}/run", response_model=AsyncJobResponse)
def run_job(job_id: str, scene_id: Optional[str] = Query(None),
            slick_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Execute a job stage in a background thread and record progress/results."""
    job = AsyncJobRepository.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.status in ("RUNNING", "COMPLETED"):
        return job
    jt = job.job_type
    job = AsyncJobRepository.update_status(db, job_id, "RUNNING", progress_pct="5")

    from app.core.database import get_engine_url

    def _worker(jid: str, db_url: str):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        odb = SessionLocal()
        try:
            res = _execute_stage(odb, jt, scene_id, slick_id)
            AsyncJobRepository.update_status(odb, jid, "COMPLETED", progress_pct="100", result=res)
        except Exception as e:
            logger.error(f"Async job {jid} failed: {e}")
            AsyncJobRepository.update_status(odb, jid, "FAILED", progress_pct="100", error=str(e))
        finally:
            odb.close()

    threading.Thread(target=_worker, args=(job_id, get_engine_url()), daemon=True).start()
    return AsyncJobRepository.get_by_id(db, job_id)


@router.get("", response_model=List[Dict[str, Any]])
def list_jobs(
    incident_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if incident_id:
        jobs = AsyncJobRepository.list_for_incident(db, incident_id)
    else:
        from app.models.async_jobs import AsyncJob
        jobs = db.query(AsyncJob).order_by(AsyncJob.created_at.desc()).limit(100).all()
    return [{"id": j.id, "incident_id": j.incident_id, "job_type": j.job_type,
             "status": j.status, "progress_pct": j.progress_pct,
             "started_at": j.started_at, "finished_at": j.finished_at,
             "error": j.error, "created_at": j.created_at} for j in jobs]