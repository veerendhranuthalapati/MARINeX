import numpy as np
import pytest
from app.services.detection.classical_baseline import ClassicalBaselineDetector
from app.services.detection.mock_detector import MockOilSpillDetector


def test_classical_baseline_detector_on_synthetic_array():
    detector = ClassicalBaselineDetector(min_cluster_pixels=20)

    # Create a 100x100 synthetic array: bright background ~150, dark spot ~30 in center
    img = np.full((100, 100), 150.0, dtype=np.float32)
    img[40:60, 40:60] = 30.0

    mask, meta = detector.segment(img)
    assert mask.shape == (100, 100)
    assert np.sum(mask) > 0  # detected dark region
    assert meta["algorithm"] == "CLASSICAL_BASELINE_ADAPTIVE_THRESHOLD"
    assert meta["is_production"] is False
    assert meta["backscatter_contrast_db"] < 0.0

    preds = detector.predict(img, bbox=[71.15, 19.15, 71.68, 19.55])
    assert preds["detected"] is True
    assert preds["polygon_count"] >= 1
    assert len(preds["polygons"][0]) >= 3


def test_mock_oil_spill_detector():
    detector = MockOilSpillDetector(default_confidence=0.95)
    assert detector.confidence() == 0.95

    preds = detector.predict(None)
    assert preds["detected"] is True
    assert preds["confidence"] == 0.95
    assert len(preds["polygons"]) == 1
    assert len(preds["polygons"][0]) > 5
