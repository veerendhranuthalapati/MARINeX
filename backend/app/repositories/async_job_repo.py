from typing import List, Optional
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from app.models.async_jobs import AsyncJob
from app.schemas.async_job import AsyncJobCreate


class AsyncJobRepository:

    @staticmethod
    def create(db: Session, data: AsyncJobCreate) -> AsyncJob:
        obj = AsyncJob(
            id=f"JOB-{uuid.uuid4().hex[:10].upper()}",
            incident_id=data.incident_id,
            job_type=data.job_type,
            status="PENDING",
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def get_by_id(db: Session, job_id: str) -> Optional[AsyncJob]:
        return db.query(AsyncJob).filter(AsyncJob.id == job_id).first()

    @staticmethod
    def list_for_incident(db: Session, incident_id: str) -> List[AsyncJob]:
        return db.query(AsyncJob).filter(AsyncJob.incident_id == incident_id)\
            .order_by(AsyncJob.created_at.desc()).all()

    @staticmethod
    def update_status(db: Session, job_id: str, status: str, progress_pct: str = None,
                      result: Optional[dict] = None, error: Optional[str] = None) -> Optional[AsyncJob]:
        obj = db.query(AsyncJob).filter(AsyncJob.id == job_id).first()
        if not obj:
            return None
        obj.status = status
        if progress_pct is not None:
            obj.progress_pct = str(progress_pct)
        if result is not None:
            obj.result = result
        if error is not None:
            obj.error = error
        now = datetime.now(timezone.utc)
        if status in ("PENDING", "RUNNING"):
            obj.started_at = obj.started_at or now
        if status in ("COMPLETED", "FAILED"):
            obj.finished_at = now
        obj.updated_at = now
        db.commit()
        db.refresh(obj)
        return obj