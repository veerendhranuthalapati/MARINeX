from typing import Any, Dict, List, Tuple, Optional
import numpy as np
from app.services.detection.base import BaseOilSpillDetector


class MockOilSpillDetector(BaseOilSpillDetector):
    """
    Deterministic Mock Detector for integration testing and demo pipelines.
    Generates synthetic geo-referenced oil slick boundaries without invoking heavy neural models.
    """

    def __init__(self, default_confidence: float = 0.94):
        self._confidence = default_confidence

    def segment(self, image_input: Any, **kwargs) -> Tuple[np.ndarray, Dict[str, Any]]:
        # Return a synthetic 512x512 mask with an ellipse
        mask = np.zeros((512, 512), dtype=np.uint8)
        y, x = np.ogrid[:512, :512]
        xr = (x - 256) * np.cos(np.radians(35)) + (y - 256) * np.sin(np.radians(35))
        yr = -(x - 256) * np.sin(np.radians(35)) + (y - 256) * np.cos(np.radians(35))
        slick = ((xr / 120.0) ** 2 + (yr / 30.0) ** 2 <= 1.0)
        mask[slick] = 1

        meta = {
            "algorithm": "MOCK_OIL_SPILL_DETECTOR",
            "is_mock": True,
            "synthetic_area_pixels": int(np.sum(slick)),
            "notes": "Generated for test harness and verification."
        }
        return mask, meta

    def predict(self, image_input: Any, bbox: Optional[List[float]] = None, **kwargs) -> Dict[str, Any]:
        # Realistic Arabian Sea slick polygon
        polygon = [
            [71.385, 19.320],
            [71.402, 19.332],
            [71.425, 19.348],
            [71.450, 19.362],
            [71.462, 19.370],
            [71.458, 19.375],
            [71.438, 19.368],
            [71.415, 19.352],
            [71.392, 19.336],
            [71.380, 19.326],
            [71.385, 19.320]
        ]

        return {
            "detected": True,
            "polygon_count": 1,
            "polygons": [polygon],
            "confidence": self._confidence,
            "metadata": {
                "algorithm": "MOCK_OIL_SPILL_DETECTOR",
                "is_mock": True,
                "notes": "Deterministic geo-referenced polygon for SIH26143 Mumbai Offshore pipeline testing."
            }
        }

    def confidence(self) -> float:
        return self._confidence

    def metadata(self) -> Dict[str, Any]:
        return {
            "algorithm": "MOCK_OIL_SPILL_DETECTOR",
            "is_mock": True,
            "version": "1.0.0"
        }
