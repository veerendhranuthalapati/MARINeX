from app.services.detection.base import BaseOilSpillDetector
from app.services.detection.classical_baseline import ClassicalBaselineDetector
from app.services.detection.mock_detector import MockOilSpillDetector
from app.services.detection.characterizer import SlickCharacterizer
from app.services.detection.adapters import (
    UNetDetectorAdapter,
    SegFormerDetectorAdapter,
    DeepLabDetectorAdapter,
)

__all__ = [
    "BaseOilSpillDetector",
    "ClassicalBaselineDetector",
    "MockOilSpillDetector",
    "SlickCharacterizer",
    "UNetDetectorAdapter",
    "SegFormerDetectorAdapter",
    "DeepLabDetectorAdapter",
]
