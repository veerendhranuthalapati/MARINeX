"""
Detection orchestration service (Phase 3 / 5 / 38-41).

Runs the production ML detector, classical baseline, or mock detector, preserves
raw + post-processed masks via DetectionArtifactStore and DetectionRun records,
characterizes every polygon into a SlickCharacterization, and returns the slicks
plus a full provenance dict.

Honesty contract:
  * PRODUCTION_ML   -> raw soft probabilities + raw mask + post-processed mask,
                       all three preserved.
  * CLASSICAL_BASELINE / MOCK -> there is no separate ML soft output; raw and
                       post are the same mask (documented as such in attributes).
  * If the model checkpoints or the detector errors, no fabricated slicks are
    produced and the DetectionRun is recorded as ERROR.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.core.status import StatusLabel, make_provenance
from app.utils.artifacts import DetectionArtifactStore
from app.utils.image import mask_to_polygon_coordinates
from app.services.detection.production_ml import ProductionMLDetector
from app.services.detection.classical_baseline import ClassicalBaselineDetector
from app.services.detection.mock_detector import MockOilSpillDetector
from app.services.detection.characterizer import SlickCharacterizer
from app.repositories.slick_repo import SlickRepository
from app.repositories.scene_repo import SceneRepository
from app.repositories.detection_run_repo import DetectionRunRepository
from app.schemas.slick import SlickResponse
from app.services.evidence import EvidenceService


class DetectionService:
    NO_SLICKS = "NO_SLICKS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    SLICKS_FOUND = "SLICKS_FOUND"
    ERROR = "ERROR"

    def __init__(self, artifact_store: Optional[DetectionArtifactStore] = None):
        self.artifact_store = artifact_store or DetectionArtifactStore()

    # ------------------------------------------------------------------ #
    def _select_detector(self, method: str):
        m = method.upper()
        if m == "PRODUCTION_ML":
            return ProductionMLDetector()
        if m == "CLASSICAL_BASELINE":
            return ClassicalBaselineDetector()
        if m == "MOCK":
            return MockOilSpillDetector()
        raise ValueError(f"Unknown detection method '{method}'. Use PRODUCTION_ML, CLASSICAL_BASELINE or MOCK.")

    def run_on_scene(
        self,
        db: Session,
        scene_id: str,
        bbox: List[float],
        image_source: Optional[str],
        method: str = "PRODUCTION_ML",
        incident_id: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> Tuple[List[SlickResponse], Dict[str, Any]]:
        method_u = method.upper()
        detector = self._select_detector(method_u)
        detector_meta = detector.metadata()

        # Detection is timestamped to the scene acquisition time, not server "now",
        # so downstream drift/AIS temporal correlation uses the observation time.
        scene = SceneRepository.get_by_id(db, scene_id)
        observed_at = scene.acquisition_time if scene and scene.acquisition_time \
            else datetime.now(timezone.utc)

        # Resolve image array (for artifact persistence).
        img_arr = None
        if image_source and isinstance(image_source, str):
            import os
            from PIL import Image
            if os.path.exists(image_source):
                img_arr = np.array(Image.open(image_source))

        try:
            pred = detector.predict(image_input=img_arr if img_arr is not None else image_source,
                                    bbox=bbox)
        except Exception as e:
            logger.error(f"Detection {method_u} failed on scene {scene_id}: {e}")
            DetectionRunRepository.create(
                db=db, scene_id=scene_id, incident_id=incident_id,
                model_id=detector_meta.get("adapter", detector_meta.get("algorithm", method_u)),
                status=self.ERROR,
                metadata_json={"error": str(e)},
                threshold=None, confidence=None,
            )
            return [], {"status": self.ERROR, "message": "Detection pipeline failed. No slicks produced.",
                        "model": detector_meta.get("architecture", detector_meta.get("algorithm", method_u))}

        confidence = float(pred.get("confidence", 0.0))

        # --- Determine masks: PRODUCTION_ML exposes raw+post; classical/mock reuse same mask ---
        raw_mask = pred.get("raw_mask")
        post_mask = pred.get("post_mask")
        probs = pred.get("probs")
        if raw_mask is not None and post_mask is None:
            post_mask = raw_mask  # classical/mock: raw == post, documented
        elif method_u == "CLASSICAL_BASELINE" and raw_mask is None:
            seg_mask, seg_meta = detector.segment(
                img_arr if img_arr is not None else image_source, bbox=bbox)
            raw_mask = seg_mask
            post_mask = seg_mask

        # --- Extract polygons from the POST-processed mask (Phase 5 boundary) ---
        polygons = pred.get("polygons", [])
        if not polygons and post_mask is not None and isinstance(post_mask, np.ndarray) and post_mask.size:
            min_px = (detector.postprocess.get("min_area_px", 20)
                      if method_u == "PRODUCTION_ML" else getattr(detector, "min_cluster_pixels", 50))
            polygons = mask_to_polygon_coordinates(post_mask, bbox=bbox, min_pixels=int(min_px))

        # --- Preserve raw + post outputs for evidence ---
        artifact_path = None
        if raw_mask is not None and isinstance(raw_mask, np.ndarray) and raw_mask.size:
            probs_arr = probs if probs is not None else raw_mask.astype(np.float32)
            artifact_path = self.artifact_store.save(
                scene_id=scene_id,
                probs=probs_arr,
                raw_mask=raw_mask,
                post_mask=post_mask if post_mask is not None else raw_mask,
                meta={
                    **pred.get("meta", pred.get("metadata", {})),
                    "method": method_u,
                    "incident_id": incident_id or "",
                    "raw_equals_post": str(raw_mask is post_mask),
                },
            )

        # --- Failure / empty / low-confidence handling (Phase 38-40) ---
        model_id = detector_meta.get("adapter", detector_meta.get("algorithm", method_u))
        model_version = pred.get("metadata", {}).get("algorithm") or detector_meta.get("architecture", method_u)
        threshold = None

        if confidence <= 0.0 or not polygons:
            status = self.NO_SLICKS
            if confidence < 0.5:
                status = self.LOW_CONFIDENCE
            DetectionRunRepository.create(
                db=db, scene_id=scene_id, incident_id=incident_id,
                model_id=model_id, model_version=model_version,
                threshold=threshold, status=status,
                artifact_path=artifact_path, confidence=confidence,
                metadata_json={"polygon_count": len(polygons), **pred.get("metadata", {})})
            return [], {
                "status": status,
                "message": (
                    "Detection ran but confidence is below operational threshold - flagging for "
                    "analyst review, NO automatic attribution (Phase 40)."
                    if status == self.LOW_CONFIDENCE else
                    "No oil slicks detected in this scene."
                ),
                "model": model_version,
                "confidence": confidence,
                "artifact_path": artifact_path,
            }

        # --- Characterize + persist slicks ---
        created: List[SlickResponse] = []
        post_cfg = getattr(detector, "postprocess", {}) if method_u == "PRODUCTION_ML" else {
            "morph_open_kernel": getattr(detector, "morph_kernel_size", 3),
            "min_area_px": getattr(detector, "min_cluster_pixels", 50),
        }
        for idx, poly_coords in enumerate(polygons):
            if len(poly_coords) < 3:
                continue
            slick_id = f"slick_{scene_id[:14]}_{idx + 1:03d}"
            char = SlickCharacterizer.characterize_polygon(
                coords=poly_coords,
                confidence=confidence,
                attributes={
                    "detector": model_id,
                    "model_id": model_version,
                    "threshold": threshold,
                    "preprocessing_version": detector_meta.get("preprocessing"),
                    "postprocessing": post_cfg,
                    "detection_run_artifact": artifact_path,
                    "status_label": StatusLabel.ML_SEGMENTED.value if method_u == "PRODUCTION_ML"
                                   else StatusLabel.EXPERIMENTAL.value,
                    "raw_output_preserved": raw_mask is not None,
                    "raw_equals_post": str(raw_mask is post_mask),
                },
            )
            slick = SlickRepository.create(
                db=db,
                slick_id=slick_id,
                scene_id=scene_id,
                geometry={"type": "Polygon", "coordinates": [poly_coords]},
                characterization=char,
                detection_method=model_version,
                detected_at=observed_at,
                confidence=confidence,
            )
            if incident_id:
                slick.incident_id = incident_id
                db.commit()
                db.refresh(slick)
            created.append(self._to_response(slick))

        DetectionRunRepository.create(
            db=db, scene_id=scene_id, incident_id=incident_id,
            model_id=model_id, model_version=model_version,
            threshold=threshold,
            status=self.SLICKS_FOUND, artifact_path=artifact_path, confidence=confidence,
            metadata_json={
                "polygon_count": len(created),
                "provenance": make_provenance(
                    source="SAR Sentinel-1",
                    source_version="v1",
                    processing_stage="detection.characterization",
                    model_id=model_id,
                    model_version=model_version,
                    config={"method": method_u, "postprocess": post_cfg},
                    preprocessing_version=detector_meta.get("preprocessing")),
                **pred.get("metadata", {}),
            })

        # Phase 21: record incident evidence ledger (detection + characterization).
        if incident_id:
            EvidenceService.record_detection(
                db, incident_id=incident_id, scene_id=scene_id, model_id=model_id,
                model_version=model_version, confidence=confidence,
                oil_pixel_count=pred.get("oil_pixels_raw", len(created)),
                artifact_path=artifact_path or "",
                status_label=StatusLabel.ML_SEGMENTED.value if method_u == "PRODUCTION_ML"
                             else StatusLabel.EXPERIMENTAL.value,
                slick_ids=[s.id for s in created],
                extra={"postprocessed_oil_pixels": post_mask.sum().item()
                       if isinstance(post_mask, np.ndarray) else None,
                       "raw_equals_post": str(raw_mask is post_mask)},
                timestamp=observed_at,
            )
            for s in created:
                slick_db = SlickRepository.get_by_id(db, s.id)
                if slick_db:
                    EvidenceService.record_characterization(
                        db, incident_id=incident_id, slick_id=s.id, area_km2=s.area_km2,
                        confidence=confidence,
                        char_value={"area_km2": s.area_km2, "perimeter_km": s.perimeter_km,
                                    "centroid": s.centroid,
                                    "length_km": s.length_km, "width_km": s.width_km,
                                    "orientation_deg": s.orientation_deg,
                                    "eccentricity": s.eccentricity,
                                    "compactness": s.compactness},
                        timestamp=observed_at)

        return created, {
            "status": self.SLICKS_FOUND,
            "model": model_version,
            "confidence": confidence,
            "slick_count": len(created),
            "artifact_path": artifact_path,
        }

    @staticmethod
    def _to_response(slick) -> SlickResponse:
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
            eccentricity=slick.eccentricity or 0.0,
            attributes=slick.attributes or {},
            created_at=slick.created_at,
        )