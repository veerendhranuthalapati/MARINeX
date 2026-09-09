"""
SAR Segmentation Postprocessing Module.
Applies probability thresholding, morphological smoothing, and minimum area filtering.
"""

import numpy as np
import cv2
from typing import Tuple

def postprocess_probability_map(
    prob_map: np.ndarray,
    threshold: float = 0.50,
    min_area_pixels: int = 15,
    morph_cleanup: bool = True
) -> np.ndarray:
    """
    Cleans raw model probability maps into high-fidelity binary slick masks.
    """
    binary = (prob_map >= threshold).astype(np.uint8)

    if morph_cleanup:
        # Small elliptical kernel to remove isolated 1-2 pixel noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        binary = closed

    # Filter out spurious micro-regions below minimum physical area
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    clean_mask = np.zeros_like(binary)

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area_pixels:
            clean_mask[labels == i] = 1

    return clean_mask
