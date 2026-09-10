"""Light ML tests: metrics correctness, model registry, single-image inference."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from ml.evaluation.metrics import compute_pixel_metrics
from ml.models.registry import build_model, MODEL_REGISTRY


def test_metrics_perfect_match():
    y = np.ones((4, 4), dtype=np.uint8)
    y[0, 0] = 0
    m = compute_pixel_metrics(y, y.copy(), y.astype(np.float32))
    assert m["iou"] == 1.0
    assert m["dice"] == 1.0
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["false_positive_rate"] == 0.0
    assert m["false_negative_rate"] == 0.0


def test_metrics_all_wrong():
    y = np.ones((4, 4), dtype=np.uint8)
    p = np.zeros((4, 4), dtype=np.uint8)
    m = compute_pixel_metrics(y, p, np.zeros((4, 4), dtype=np.float32))
    assert m["iou"] == 0.0
    assert m["recall"] == 0.0
    assert m["false_negative_rate"] == 1.0


def test_metrics_imbalanced_pr_auc():
    y = np.zeros((100, 100), dtype=np.uint8)
    y[10:15, 10:15] = 1
    p = y.copy()
    prob = np.zeros((100, 100), dtype=np.float32)
    prob[10:15, 10:15] = 0.9
    m = compute_pixel_metrics(y, p, prob)
    assert m["pr_auc"] > 0.9


def test_registry_models_build():
    for name in ["unet", "unet_plus_plus", "segformer", "classical", "classifier"]:
        model = build_model(name, in_channels=3, num_classes=1)
        assert model is not None
        assert getattr(model, "model_name", None) is not None or name in ("classical", "classifier")


def test_registry_unknown_model():
    import pytest
    with pytest.raises(ValueError):
        build_model("does_not_exist")


def test_single_image_inference():
    import torch
    from PIL import Image
    ckpt = Path("models/checkpoints/segformer_primary_best.pt")
    if not ckpt.exists():
        return  # trained checkpoint absent (CI without training); metrics still tested
    img = Image.open("data/datasets/sentinel1_primary/images/patch_0101.png")
    arr = np.array(img)
    model = build_model("segformer", in_channels=3, num_classes=1)
    model.load_state_dict(torch.load(ckpt, map_location="cpu")["state_dict"])
    model.eval()
    # Percentile preprocessing equivalent to training-time transform.
    from ml.data.transforms import SARPreprocessor
    norm = SARPreprocessor(strategy="percentile")(arr)
    x = torch.from_numpy(norm).permute(2, 0, 1).unsqueeze(0)
    with torch.no_grad():
        probs = torch.sigmoid(model(x)).squeeze().numpy()
    assert probs.shape == (256, 256)
    assert probs.min() >= 0.0 and probs.max() <= 1.0