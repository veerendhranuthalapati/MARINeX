"""
Feature extraction module for oil slick characterization and look-alike discrimination.
Extracts geometric, physical, and radar backscatter texture features.
"""

from typing import Dict, Any, List
import numpy as np


def extract_slick_features(
    area_km2: float,
    perimeter_km: float,
    length_km: float,
    width_km: float,
    contrast_db: float,
    compactness: float,
) -> Dict[str, float]:
    """
    Compute tabular features used by downstream look-alike classification models
    (e.g., Random Forest, XGBoost) to distinguish mineral oil spills from natural biogenic films.
    """
    aspect_ratio = length_km / max(0.01, width_km)
    complexity = perimeter_km / max(0.01, np.sqrt(area_km2))

    return {
        "area_km2": float(area_km2),
        "perimeter_km": float(perimeter_km),
        "aspect_ratio": float(round(aspect_ratio, 2)),
        "compactness": float(round(compactness, 4)),
        "boundary_complexity": float(round(complexity, 2)),
        "backscatter_contrast_db": float(round(contrast_db, 2)),
    }
