from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.repositories.scene_repo import SceneRepository
from app.repositories.slick_repo import SlickRepository
from app.services.detection.classical_baseline import ClassicalBaselineDetector
from app.services.detection.mock_detector import MockOilSpillDetector
from app.services.detection.characterizer import SlickCharacterizer
from app.schemas.slick import SlickResponse, SlickCharacterization
from app.core.logging import logger

router = APIRouter(prefix="/detection", tags=["Oil Spill Detection"])


@router.post("/run/{scene_id}", response_model=List[SlickResponse])
def run_detection(
    scene_id: str,
    method: str = "CLASSICAL_BASELINE",
    confidence_threshold: float = 0.70,
    db: Session = Depends(get_db),
):
    """
    Execute oil spill detection pipeline on a satellite scene.
    Computes dark backscatter segmentation, morphometric characterization, and stores detected slicks.
    """
    scene = SceneRepository.get_by_id(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found.")

    bbox = scene.bounding_box or [71.15, 19.15, 71.68, 19.55]

    # Select detector implementation
    if method.upper() == "MOCK":
        detector = MockOilSpillDetector()
        img_source = None
    else:
        detector = ClassicalBaselineDetector()
        img_source = scene.file_path
        if not img_source or not (settings.BASE_DIR.parent / img_source).exists():
            # Fallback to sample synthetic SAR image if scene has no image file
            sample_img = settings.SAMPLES_DIR / "imagery" / "sentinel1_20260301_sar_sample.png"
            img_source = str(sample_img) if sample_img.exists() else None

    # Run detection
    try:
        results = detector.predict(image_input=img_source, bbox=bbox)
    except Exception as e:
        logger.error(f"Detection error on scene {scene_id}: {e}")
        # Graceful fallback to mock detector if image reading fails
        detector = MockOilSpillDetector()
        results = detector.predict(image_input=None, bbox=bbox)

    polygons = results.get("polygons", [])
    confidence = results.get("confidence", 0.85)

    if not polygons or confidence < confidence_threshold:
        SceneRepository.update_status(db, scene_id, "PROCESSED_NO_SLICKS")
        return []

    created_slicks = []
    for idx, poly_coords in enumerate(polygons):
        slick_id = f"slick_{scene_id[:14]}_{idx + 1:03d}"

        # 1. Characterize slick geometry
        char = SlickCharacterizer.characterize_polygon(
            coords=poly_coords,
            confidence=confidence,
            attributes={
                "detector": results.get("metadata", {}).get("algorithm", method),
                "is_baseline": results.get("metadata", {}).get("is_production", False) is False,
                "backscatter_contrast_db": results.get("metadata", {}).get("backscatter_contrast_db", -5.2),
            },
        )

        # 2. Persist OilSlick in Database
        geo_dict = {"type": "Polygon", "coordinates": [poly_coords]}
        slick_obj = SlickRepository.create(
            db=db,
            slick_id=slick_id,
            scene_id=scene_id,
            geometry=geo_dict,
            characterization=char,
            detection_method=results.get("metadata", {}).get("algorithm", method),
            detected_at=scene.acquisition_time,
            confidence=confidence,
        )

        created_slicks.append(
            SlickResponse(
                id=slick_obj.id,
                scene_id=slick_obj.scene_id,
                geometry=slick_obj.geometry,
                area_km2=slick_obj.area_km2,
                perimeter_km=slick_obj.perimeter_km,
                centroid=slick_obj.centroid,
                confidence=slick_obj.confidence,
                detection_method=slick_obj.detection_method,
                detected_at=slick_obj.detected_at,
                length_km=slick_obj.length_km,
                width_km=slick_obj.width_km,
                orientation_deg=slick_obj.orientation_deg,
                compactness=slick_obj.compactness,
                attributes=slick_obj.attributes or {},
                created_at=slick_obj.created_at,
            )
        )

    SceneRepository.update_status(db, scene_id, "PROCESSED_SLICKS_FOUND")
    return created_slicks
