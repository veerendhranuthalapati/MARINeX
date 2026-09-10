"""ML validation card & robustness APIs (Phases 4, 47-48, 52).

Serves the frozen production-model card, model comparison, calibration, and the
full scientific validation suite produced by the ML campaign. Every value comes
from validated reports/artifacts on disk - the UI never fabricates metrics.
"""

from typing import Dict, Any
from fastapi import APIRouter
from app.services.ml_validation.service import ml_service

router = APIRouter(prefix="/ml", tags=["ML Validation Bundle"])


@router.get("/card", response_model=Dict[str, Any])
def get_ml_card():
    """Production model card + frozen test metrics + calibration."""
    return ml_service.card()


@router.get("/validation", response_model=Dict[str, Any])
def get_ml_validation():
    """Robustness, scene-level, size, look-alike, geometry, drift, AIS validation."""
    return ml_service.validation()