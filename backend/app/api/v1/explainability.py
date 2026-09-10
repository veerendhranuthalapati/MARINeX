"""
Explainability API (Phase 25). Attribution maps for production UNet detections:
OcclusionSensitivity (model-agnostic) + GradCAM (conv-backed). Results are
persisted heatmaps + provenance JSON; no causal claims in the response.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.services.detection.explainability import explain_service
from app.services.ml_validation.service import ml_service
from app.core.config import settings


class ExplainabilityRunRequest(BaseModel):
    methods: List[str] = Field(default_factory=lambda: ["occlusion", "gradcam"])
    image_path: Optional[str] = None


class ExplainabilityRunResponse(BaseModel):
    run_id: str
    image: str
    created_at: str
    methods: List[None]
    provenance: dict
    disclaimer: str
    metadata_path: str


router = APIRouter(prefix="/explainability", tags=["Explainability"])


@router.post("/run", response_model=dict)
def run_explainability(req: ExplainabilityRunRequest):
    """Compute attribution maps for an image with the production model.

    image_path: absolute path to a SAR scene raster (defaults to the SIH26143
    demo sample). methods: occlusion, gradcam, attention (attention is a
    documented SegFormer decoder proxy; not applicable to the UNet).
    """
    img = req.image_path or str(settings.DEMO_SAMPLE_PATH)
    if not Path(img).exists():
        raise HTTPException(status_code=404, detail=f"Image '{img}' not found.")
    try:
        return explain_service.explain(img, methods=req.methods)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Explainability failed: {e}") from e


@router.get("/validation", response_model=dict)
def get_validation_summary():
    """Validated explainability artifacts from the ML campaign (sanity + examples)."""
    return ml_service.explainability()