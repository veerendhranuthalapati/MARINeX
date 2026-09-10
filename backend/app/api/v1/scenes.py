import json
import os
import re
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.repositories.scene_repo import SceneRepository
from app.schemas.scene import SceneResponse, SceneCreate, SceneListResponse
from datetime import datetime


def _sanitize_upload_component(value: str) -> str:
    """Reject path separators and traversal sequences; keep safe identifier chars."""
    name = os.path.basename(value.replace("\\", "/"))
    name = re.sub(r"[^\w.\-]+", "_", name)
    name = re.sub(r"\.{2,}", "_", name)
    name = name.strip(" .")
    if not name:
        raise HTTPException(status_code=422, detail="Invalid file/identifier name.")
    return name


router = APIRouter(prefix="/scenes", tags=["Satellite Scenes"])


@router.get("", response_model=SceneListResponse)
def list_scenes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve ingested satellite scenes."""
    scenes = SceneRepository.list_all(db, skip=skip, limit=limit)
    total = SceneRepository.count(db)
    items = []
    for s in scenes:
        items.append(
            SceneResponse(
                id=s.id,
                source=s.source,
                sensor=s.sensor,
                acquisition_time=s.acquisition_time,
                latitude=s.latitude,
                longitude=s.longitude,
                bounding_box=s.bounding_box,
                resolution=s.resolution,
                status=s.status,
                metadata_json=s.metadata_json or {},
                file_path=s.file_path,
                created_at=s.created_at,
                slick_count=len(s.slicks) if s.slicks else 0,
            )
        )
    return SceneListResponse(total=total, scenes=items)


@router.get("/{scene_id}", response_model=SceneResponse)
def get_scene(scene_id: str, db: Session = Depends(get_db)):
    """Retrieve metadata for a specific satellite scene."""
    scene = SceneRepository.get_by_id(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found.")
    return SceneResponse(
        id=scene.id,
        source=scene.source,
        sensor=scene.sensor,
        acquisition_time=scene.acquisition_time,
        latitude=scene.latitude,
        longitude=scene.longitude,
        bounding_box=scene.bounding_box,
        resolution=scene.resolution,
        status=scene.status,
        metadata_json=scene.metadata_json or {},
        file_path=scene.file_path,
        created_at=scene.created_at,
        slick_count=len(scene.slicks) if scene.slicks else 0,
    )


@router.post("/upload", response_model=SceneResponse)
async def upload_scene(
    scene_id: str = Form(...),
    source: str = Form("Sentinel-1"),
    sensor: str = Form("C-SAR"),
    acquisition_time: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    min_lon: float = Form(...),
    min_lat: float = Form(...),
    max_lon: float = Form(...),
    max_lat: float = Form(...),
    resolution: float = Form(10.0),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Upload or register a new satellite scene raster."""
    scene_id = _sanitize_upload_component(scene_id)
    existing = SceneRepository.get_by_id(db, scene_id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Scene '{scene_id}' already exists.")

    saved_path = None
    if file:
        os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
        safe_filename = _sanitize_upload_component(file.filename or "scene.bin")
        # Confine writes to UPLOADS_DIR (defense-in-depth against traversal).
        saved_path = str((settings.UPLOADS_DIR / f"{scene_id}_{safe_filename}").resolve())
        if os.path.commonpath([saved_path, str(settings.UPLOADS_DIR.resolve())]) != str(settings.UPLOADS_DIR.resolve()):
            raise HTTPException(status_code=422, detail="Unsafe upload path.")
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    try:
        acq_dt = datetime.fromisoformat(acquisition_time.replace("Z", "+00:00"))
    except ValueError:
        acq_dt = datetime.utcnow()

    scene_data = SceneCreate(
        id=scene_id,
        source=source,
        sensor=sensor,
        acquisition_time=acq_dt,
        latitude=latitude,
        longitude=longitude,
        bounding_box=[min_lon, min_lat, max_lon, max_lat],
        resolution=resolution,
        file_path=saved_path,
        status="INGESTED",
        metadata_json={"uploaded_by": "API", "original_filename": file.filename if file else None},
    )

    created = SceneRepository.create(db, scene_data)
    return SceneResponse(
        id=created.id,
        source=created.source,
        sensor=created.sensor,
        acquisition_time=created.acquisition_time,
        latitude=created.latitude,
        longitude=created.longitude,
        bounding_box=created.bounding_box,
        resolution=created.resolution,
        status=created.status,
        metadata_json=created.metadata_json or {},
        file_path=created.file_path,
        created_at=created.created_at,
        slick_count=0,
    )
