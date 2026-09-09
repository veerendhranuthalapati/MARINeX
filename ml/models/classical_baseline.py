"""
Classical Image Processing Baseline for SAR Oil Spill Detection.
Implements adaptive Otsu thresholding, connected component analysis, morphological cleanup,
and minimum region area filtering.
"""

import numpy as np
import cv2
from typing import Tuple, Dict, Any

class ClassicalSARBaseline:
    def __init__(
        self,
        min_region_pixels: int = 15,
        morph_kernel_size: int = 3,
        damping_multiplier: float = 0.92,
    ):
        self.min_region_pixels = min_region_pixels
        self.morph_kernel_size = morph_kernel_size
        self.damping_multiplier = damping_multiplier

    def predict(self, image: np.ndarray, threshold_override: float = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Accepts SAR image (H, W, C) or (H, W).
        Returns:
            binary_mask: (H, W) uint8 with 1 for detected slick, 0 for background
            confidence_map: (H, W) float32 in [0, 1]
        """
        if image.ndim == 3:
            # Use VV channel (index 0) where damping contrast is strongest
            vv = image[:, :, 0]
        else:
            vv = image

        # 1. Mild median filtering for SAR speckle noise reduction
        smoothed = cv2.medianBlur(vv.astype(np.uint8), 3)

        # 2. Otsu adaptive global threshold
        otsu_val, _ = cv2.threshold(smoothed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        active_thresh = otsu_val * self.damping_multiplier if threshold_override is None else threshold_override

        # Dark pixels are candidates for oil spill
        dark_pixels = (smoothed <= active_thresh).astype(np.uint8)

        # 3. Morphological opening and closing
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.morph_kernel_size, self.morph_kernel_size))
        opened = cv2.morphologyEx(dark_pixels, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

        # 4. Connected Components & Minimum Region Area Filtering
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
        binary_mask = np.zeros_like(cleaned, dtype=np.uint8)

        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= self.min_region_pixels:
                binary_mask[labels == i] = 1

        # 5. Continuous Probability Map estimation based on inverted intensity relative to Otsu
        norm_dist = np.clip((active_thresh - smoothed.astype(np.float32)) / max(active_thresh, 1.0), 0.0, 1.0)
        confidence_map = norm_dist * binary_mask.astype(np.float32)

        return binary_mask, confidence_map
