"""
Explainability service (Phase 25). Attribution maps for production-model detections.

Reuses the validated production model + the EXACT training preprocessing through
ProductionMLDetector, runs architecture-appropriate attribution methods
(OcclusionSensitivity - any model; GradCAM - conv-backed U-Net/U-Net++), and
persists normalized heatmap PNGs + provenance JSON under reports/explainability/.

SciGuard: attribution maps are faithful model post-hoc explanations. No causal
claim is attached - results carry model + method + timestamp provenance and a
trust note per method (see ml/explainability/methods.py).
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional
import numpy as np

from app.core.config import settings
from app.core.logging import logger


def _ml_on_path():
    ml_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))
    if ml_root not in sys.path:
        sys.path.insert(0, ml_root)
    return ml_root


class ExplainabilityService:
    def __init__(self):
        self._detector = None  # lazy: ProductionMLDetector
        self._device = None

    def _load(self):
        from app.services.detection.production_ml import ProductionMLDetector
        import torch
        self._detector = ProductionMLDetector()
        self._detector.load_model()
        self._device = torch.device("cpu")

    def explain(self, image_path: str,
                methods: Optional[List[str]] = None,
                out_dir: Optional[str] = None) -> Dict:
        """Compute attribution maps for an image, persist heatmaps + provenance."""
        if not image_path or not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: '{image_path}'")
        self._load()

        from ml.explainability.methods import compute_explainability
        from PIL import Image
        import uuid

        arr = np.array(Image.open(image_path))
        if arr.ndim == 3 and arr.shape[-1] == 3:
            # RGB panels (e.g. sample PNG) are converted to intensity just like
            # the detector pipeline: production prefers single-band ophrtho.
            arr = arr.mean(axis=-1).astype(np.float32)

        # Mirror training preprocessing (percentile + VV_VH_DIFF).
        img_norm = self._detector._preprocess(arr)

        methods = (methods or ["occlusion", "gradcam"])
        results = compute_explainability(self._detector._model, self._device, img_norm, methods=methods)

        out_dir = out_dir or str(settings.REPORTS_DIR / "explainability")
        os.makedirs(out_dir, exist_ok=True)

        run_id = f"EXP-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        provenance = self._detector.metadata()
        provenance["detector_model_name"] = self._detector._model_meta.get("architecture")
        provenance["checkpoint"] = self._detector.model_weights_path
        provenance["image"] = os.path.basename(image_path)

        entries = []
        for r in results:
            heat_name = f"{run_id}_{r.method}.png"
            heat_path = os.path.join(out_dir, heat_name)
            self._save_heatmap(r.attribution, heat_path)
            entries.append({
                "method": r.method,
                "model": r.model_name,
                "heatmap": heat_path,
                **r.to_dict(),
            })

        summary = {
            "run_id": run_id,
            "image": os.path.basename(image_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "methods": entries,
            "provenance": provenance,
            "disclaimer": "Attribution maps are post-hoc model explanations, not causal proof.",
        }
        meta_path = os.path.join(out_dir, f"{run_id}.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            import json
            json.dump(summary, f, indent=2, default=str)
        summary["metadata_path"] = meta_path
        return summary

    def _save_heatmap(self, attr: np.ndarray, path: str) -> None:
        import cv2
        cm = np.clip(attr, 0, 1)
        vis = (cm * 255).astype(np.uint8)
        vis = cv2.applyColorMap(vis, cv2.COLORMAP_JET)
        cv2.imwrite(path, vis)


explain_service = ExplainabilityService()