from typing import Any, Dict, List, Tuple, Optional
import numpy as np
from scipy.ndimage import binary_opening, binary_closing, generate_binary_structure
from app.services.detection.base import BaseOilSpillDetector
from app.utils.image import load_image_to_grayscale_array, otsu_threshold, mask_to_polygon_coordinates
from app.core.logging import logger


class ClassicalBaselineDetector(BaseOilSpillDetector):
    """
    Classical image processing baseline detector.
    Uses adaptive Otsu / percentile dark spot thresholding, morphological filtering,
    and connected component analysis on SAR backscatter or optical imagery.

    IMPORTANT:
    This is an explainable classical baseline and NOT a production deep learning model.
    It does not account for complex meteorological look-alikes (low wind areas, internal waves,
    biogenic slicks) without multi-temporal verification.
    """

    def __init__(
        self,
        contrast_threshold_db: float = -3.0,
        min_cluster_pixels: int = 50,
        morph_kernel_size: int = 3
    ):
        self.contrast_threshold_db = contrast_threshold_db
        self.min_cluster_pixels = min_cluster_pixels
        self.morph_kernel_size = morph_kernel_size
        self._last_confidence = 0.78
        self._last_metadata: Dict[str, Any] = {}

    def segment(self, image_input: Any, **kwargs) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Segment dark radar backscatter patches corresponding to candidate oil slicks.
        """
        gray = load_image_to_grayscale_array(image_input)
        thresh_val = otsu_threshold(gray)

        # In SAR images, oil dampens capillary waves, appearing as dark spots (lower intensity)
        # Slicks are significantly darker than ocean background mean
        ocean_mean = float(np.mean(gray))
        ocean_std = float(np.std(gray))

        # Dark spot candidate mask: pixels below or equal to threshold
        dark_cutoff = min(thresh_val, ocean_mean - 0.3 * ocean_std)
        raw_mask = gray <= dark_cutoff

        # Morphological opening (remove small speckle noise) and closing (fill holes)
        struct = generate_binary_structure(2, 2)
        cleaned_mask = binary_opening(raw_mask, structure=struct, iterations=1)
        cleaned_mask = binary_closing(cleaned_mask, structure=struct, iterations=2)

        slick_pixels = int(np.sum(cleaned_mask))
        total_pixels = gray.size

        # Compute backscatter contrast if slicks detected
        if slick_pixels > 0:
            mean_slick = max(1.0, float(np.mean(gray[cleaned_mask])))
            mean_bg = max(1.0, float(np.mean(gray[~cleaned_mask])))
            contrast_db = 10.0 * np.log10(mean_slick / mean_bg)
        else:
            mean_slick = 0.0
            mean_bg = ocean_mean
            contrast_db = 0.0

        # Heuristic confidence calculation based on contrast suppression and minimum area
        if slick_pixels >= self.min_cluster_pixels and contrast_db < -2.0:
            confidence = min(0.92, 0.65 + abs(contrast_db) * 0.04)
        else:
            confidence = 0.40

        self._last_confidence = float(confidence)
        self._last_metadata = {
            "algorithm": "CLASSICAL_BASELINE_ADAPTIVE_THRESHOLD",
            "is_production": False,
            "threshold_value": thresh_val,
            "ocean_mean_intensity": ocean_mean,
            "slick_mean_intensity": mean_slick,
            "backscatter_contrast_db": round(contrast_db, 2),
            "slick_pixel_count": slick_pixels,
            "slick_area_ratio": round(slick_pixels / max(1, total_pixels), 4),
            "caveat": "Classical baseline: prone to false positives from low-wind areas and natural biogenic films.",
        }

        return cleaned_mask.astype(np.uint8), self._last_metadata

    def predict(self, image_input: Any, bbox: Optional[List[float]] = None, **kwargs) -> Dict[str, Any]:
        """
        Run detection and extract geo-referenced candidate polygons.
        """
        mask, meta = self.segment(image_input, **kwargs)
        default_bbox = bbox or [71.15, 19.15, 71.68, 19.55]

        polygons = mask_to_polygon_coordinates(
            binary_mask=(mask > 0),
            bbox=default_bbox,
            min_pixels=self.min_cluster_pixels
        )

        return {
            "detected": len(polygons) > 0,
            "polygon_count": len(polygons),
            "polygons": polygons,
            "confidence": self._last_confidence,
            "metadata": meta,
        }

    def confidence(self) -> float:
        return self._last_confidence

    def metadata(self) -> Dict[str, Any]:
        return self._last_metadata or {
            "algorithm": "CLASSICAL_BASELINE_ADAPTIVE_THRESHOLD",
            "is_production": False,
        }
