from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.slick_repo import SlickRepository
from app.schemas.slick import SlickResponse, SlickListResponse
from app.schemas.common import GeoJSONFeature

router = APIRouter(prefix="/slicks", tags=["Oil Slicks"])


@router.get("", response_model=SlickListResponse)
def list_slicks(
    scene_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List detected oil slicks with filtering and pagination."""
    slicks = SlickRepository.list_by_scene(db, scene_id=scene_id, skip=skip, limit=limit)
    total = SlickRepository.count(db, scene_id=scene_id)
    items = []
    for s in slicks:
        items.append(
            SlickResponse(
                id=s.id,
                scene_id=s.scene_id,
                geometry=s.geometry,
                area_km2=s.area_km2,
                perimeter_km=s.perimeter_km,
                centroid=s.centroid,
                confidence=s.confidence,
                detection_method=s.detection_method,
                detected_at=s.detected_at,
                length_km=s.length_km,
                width_km=s.width_km,
                orientation_deg=s.orientation_deg,
                compactness=s.compactness,
                attributes=s.attributes or {},
                created_at=s.created_at,
            )
        )
    return SlickListResponse(total=total, slicks=items)


@router.get("/{slick_id}", response_model=SlickResponse)
def get_slick(slick_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed characterization and geometry for a specific oil slick."""
    slick = SlickRepository.get_by_id(db, slick_id)
    if not slick:
        raise HTTPException(status_code=404, detail=f"Slick '{slick_id}' not found.")
    return SlickResponse(
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


@router.get("/{slick_id}/geojson")
def get_slick_geojson(slick_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve oil slick as a standard RFC 7946 GeoJSON Feature."""
    slick = SlickRepository.get_by_id(db, slick_id)
    if not slick:
        raise HTTPException(status_code=404, detail=f"Slick '{slick_id}' not found.")
    return {
        "type": "Feature",
        "id": slick.id,
        "properties": {
            "slick_id": slick.id,
            "scene_id": slick.scene_id,
            "area_km2": slick.area_km2,
            "perimeter_km": slick.perimeter_km,
            "centroid": slick.centroid,
            "confidence": slick.confidence,
            "detection_method": slick.detection_method,
            "detected_at": slick.detected_at.isoformat(),
            "length_km": slick.length_km,
            "width_km": slick.width_km,
            "orientation_deg": slick.orientation_deg,
            "compactness": slick.compactness,
            "attributes": slick.attributes or {},
        },
        "geometry": slick.geometry,
    }
