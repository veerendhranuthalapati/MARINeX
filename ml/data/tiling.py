"""
Configurable SAR Image Tiling and Sliding-Window Inference Stitcher.
Implements multi-scale patch extraction and cosine/Gaussian blending for border artifact suppression.
"""

import numpy as np
from typing import List, Tuple, Generator, Dict, Any

class SARTiler:
    """
    Extracts overlapping or non-overlapping patches from large SAR scenes.
    """
    def __init__(
        self,
        tile_size: int = 256,
        overlap_ratio: float = 0.25,
    ):
        self.tile_size = tile_size
        self.overlap_ratio = overlap_ratio
        self.stride = int(tile_size * (1.0 - overlap_ratio))

    def get_tile_coordinates(self, img_height: int, img_width: int) -> List[Tuple[int, int, int, int]]:
        """
        Generates (y1, y2, x1, x2) bounding boxes covering the full image dimensions.
        """
        coords = []
        y_starts = list(range(0, max(1, img_height - self.tile_size + 1), self.stride))
        if y_starts[-1] + self.tile_size < img_height:
            y_starts.append(img_height - self.tile_size)

        x_starts = list(range(0, max(1, img_width - self.tile_size + 1), self.stride))
        if x_starts[-1] + self.tile_size < img_width:
            x_starts.append(img_width - self.tile_size)

        for y in y_starts:
            for x in x_starts:
                coords.append((y, min(img_height, y + self.tile_size), x, min(img_width, x + self.tile_size)))
        return coords

    def tile_image(self, image: np.ndarray) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Extracts all tiles and their coordinates.
        """
        h, w = image.shape[:2]
        coords = self.get_tile_coordinates(h, w)
        tiles = []
        for y1, y2, x1, x2 in coords:
            tiles.append((image[y1:y2, x1:x2], (y1, y2, x1, x2)))
        return tiles

class SlidingWindowStitcher:
    """
    Blends overlapping model prediction patches into a seamless full-scene probability map.
    Uses 2D Hann window weighting to suppress seam boundaries.
    """
    def __init__(self, full_height: int, full_width: int, num_classes: int = 1):
        self.full_height = full_height
        self.full_width = full_width
        self.num_classes = num_classes

        self.prob_map = np.zeros((full_height, full_width), dtype=np.float32)
        self.weight_map = np.zeros((full_height, full_width), dtype=np.float32)

    def _get_hann_window(self, height: int, width: int) -> np.ndarray:
        h_win = np.hanning(height)
        w_win = np.hanning(width)
        win = np.outer(h_win, w_win)
        return np.maximum(win, 1e-4).astype(np.float32)

    def add_prediction(self, pred_tile: np.ndarray, coords: Tuple[int, int, int, int]):
        y1, y2, x1, x2 = coords
        th, tw = y2 - y1, x2 - x1
        window = self._get_hann_window(th, tw)

        self.prob_map[y1:y2, x1:x2] += pred_tile * window
        self.weight_map[y1:y2, x1:x2] += window

    def get_stitched_probabilities(self) -> np.ndarray:
        safe_weights = np.where(self.weight_map == 0, 1.0, self.weight_map)
        return self.prob_map / safe_weights
