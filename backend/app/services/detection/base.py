from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple
import numpy as np


class BaseOilSpillDetector(ABC):
    """
    Abstract Base Class for Oil Spill Detection models.
    Defines the contract for classical baselines and future deep learning architectures
    (U-Net, SegFormer, DeepLabV3+).
    """

    @abstractmethod
    def predict(self, image_input: Any, **kwargs) -> Dict[str, Any]:
        """
        Run inference on satellite scene imagery.
        Returns detection summary, polygons, and diagnostic metrics.
        """
        pass

    @abstractmethod
    def segment(self, image_input: Any, **kwargs) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Compute pixel-level binary segmentation mask.
        Returns:
            (binary_mask: np.ndarray where 1 = oil slick, 0 = ocean/land,
             metadata: Dict[str, Any])
        """
        pass

    @abstractmethod
    def confidence(self) -> float:
        """Return the overall model/statistical confidence score (0.0 to 1.0)."""
        pass

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Return model metadata, architecture description, and operational caveats."""
        pass
