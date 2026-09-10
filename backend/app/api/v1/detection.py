from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.repositories.scene_repo import SceneRepository
from app.repositories.slick_repo import SlickRepository
from app.services.detection.service import DetectionService
from app.schemas.slick import SlickResponse
from app.core.logging import logger

router = APIRouter(prefix="/detection", tags=["Oil Spill Detection"])


@router.post("/run/{scene_id}", response_model=List[SlickResponse])
def run_detection(
    scene_id: str,
    method: str = "PRODUCTION_ML",
    confidence_threshold: float = 0.50,
    incident_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Execute oil spill detection pipeline on a satellite scene (Phase 3).

    - PRODUCTION_ML: validated UNet (VV_VH_DIFF, percentile preproc). Raises instead
      of fabricating output if the checkpoint is missing.
    - CLASSICAL_BASELINE: explainable Otsu/adaptive-threshold baseline.
    - MOCK: deterministic demo geometry (DEMO_DATA only).

    Every run is recorded as a DetectionRun with raw + post-processed masks
    preserved to disk (never silently overwritten).
    """
    scene = SceneRepository.get_by_id(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found.")

    bbox = scene.bounding_box or [71.15, 19.15, 71.68, 19.55]
    img_source = scene.file_path
    if not img_source or not (settings.BASE_DIR.parent / img_source).exists():
        sample_img = settings.SAMPLES_DIR / "imagery" / "sentinel1_20260301_sar_sample.png"
        img_source = str(sample_img) if sample_img.exists() else None

    service = DetectionService()
    slicks, run_meta = service.run_on_scene(
        db=db,
        scene_id=scene_id,
        bbox=bbox,
        image_source=img_source,
        method=method,
        incident_id=incident_id,
        confidence_threshold=confidence_threshold,
    )

    status = run_meta.get("status", "NO_SLICKS")
    if status == DetectionService.ERROR:
        SceneRepository.update_status(db, scene_id, "PROCESSED_ERROR")
        raise HTTPException(status_code=502, detail=run_meta)
    if status == DetectionService.SLICKS_FOUND:
        SceneRepository.update_status(db, scene_id, "PROCESSED_SLICKS_FOUND")
    else:
        SceneRepository.update_status(db, scene_id, "PROCESSED_NO_SLICKS")
    return slicks


@router.get("/run/{scene_id}/details", response_model=Dict[str, Any])
def get_detection_details(scene_id: str, db: Session = Depends(get_db)):
    """Return the latest detection run details for a scene (provenance + status)."""
    from app.repositories.detection_run_repo import DetectionRunRepository
    run = DetectionRunRepository.latest_for_scene(db, scene_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"No detection run recorded for scene '{scene_id}'.")
    return {
        "run_id": run.id,
        "scene_id": run.scene_id,
        "incident_id": run.incident_id,
        "model_id": run.model_id,
        "status": run.status,
        "confidence": run.confidence,
        "artifact_path": run.artifact_path,
        "metadata": run.metadata_json,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }