"""
Model Registry and Factory Module for MARINeX Segmentation and Classification Models.
"""

from typing import Dict, Any, Type
from ml.models.base import BaseSegmentationModel
from ml.models.unet import UNetBaseline
from ml.models.unet_plus_plus import UNetPlusPlus
from ml.models.segformer import SegFormer
from ml.models.classical_baseline import ClassicalSARBaseline
from ml.models.classifier import OilLookalikeClassifier

MODEL_REGISTRY: Dict[str, Type] = {
    "unet": UNetBaseline,
    "unet_plus_plus": UNetPlusPlus,
    "segformer": SegFormer,
    "classifier": OilLookalikeClassifier,
    "classical": ClassicalSARBaseline,
}

def build_model(model_name: str, in_channels: int = 3, num_classes: int = 1, **kwargs) -> Any:
    name = model_name.lower().replace("-", "_")
    if name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model name '{model_name}'. Available: {list(MODEL_REGISTRY.keys())}")

    cls = MODEL_REGISTRY[name]
    if name == "classical":
        return cls(**kwargs)
    elif name == "classifier":
        return cls(in_channels=in_channels, num_classes=num_classes or 3, **kwargs)
    else:
        return cls(in_channels=in_channels, num_classes=num_classes, **kwargs)
