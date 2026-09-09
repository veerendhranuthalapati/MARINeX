"""
Base Segmentation Model Abstract Class.
Defines standard inference, probability estimation, and serialization protocols.
"""

from abc import ABC, abstractmethod
import torch
import torch.nn as nn
import os
import json

class BaseSegmentationModel(nn.Module, ABC):
    def __init__(self, model_name: str, in_channels: int = 3, num_classes: int = 1):
        super().__init__()
        self.model_name = model_name
        self.in_channels = in_channels
        self.num_classes = num_classes

    @abstractmethod
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Outputs raw unnormalized logits (B, num_classes, H, W)."""
        pass

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Outputs calibrated probabilities (B, num_classes, H, W) in [0, 1]."""
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            if self.num_classes == 1:
                return torch.sigmoid(logits)
            else:
                return torch.softmax(logits, dim=1)

    def predict_mask(self, x: torch.Tensor, threshold: float = 0.5) -> torch.Tensor:
        """Outputs discrete segmentation mask."""
        probs = self.predict_proba(x)
        if self.num_classes == 1:
            return (probs.squeeze(1) >= threshold).to(torch.uint8)
        else:
            return torch.argmax(probs, dim=1).to(torch.uint8)

    def save_weights(self, path: str, extra_meta: dict = None):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        checkpoint = {
            "model_name": self.model_name,
            "in_channels": self.in_channels,
            "num_classes": self.num_classes,
            "state_dict": self.state_dict(),
            "metadata": extra_meta or {}
        }
        torch.save(checkpoint, path)

    def load_weights(self, path: str, map_location=None):
        checkpoint = torch.load(path, map_location=map_location or torch.device('cpu'))
        self.load_state_dict(checkpoint["state_dict"])
        return checkpoint.get("metadata", {})
