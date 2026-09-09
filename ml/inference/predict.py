"""
End-to-End Inference Engine for SAR Oil Spill Detection.
Integrates preprocessing, sliding-window tiling, model forward pass, postprocessing, and GeoJSON export.
"""

import os
import json
import torch
import numpy as np
from PIL import Image
from typing import Dict, Any, Optional, Union
from ml.models.base import BaseSegmentationModel
from ml.data.transforms import SARPreprocessor
from ml.data.tiling import SARTiler, SlidingWindowStitcher
from ml.inference.postprocess import postprocess_probability_map
from ml.inference.geojson_export import mask_to_geojson_features

class SAROilSpillInferenceEngine:
    def __init__(
        self,
        model: BaseSegmentationModel,
        threshold: float = 0.45,
        preprocessor: Optional[SARPreprocessor] = None,
        tile_size: int = 256,
        overlap_ratio: float = 0.25,
        device: Optional[torch.device] = None,
        model_version: str = "marinex-sar-v1.0.0"
    ):
        self.model = model
        self.threshold = threshold
        self.preprocessor = preprocessor or SARPreprocessor(strategy="percentile")
        self.tiler = SARTiler(tile_size=tile_size, overlap_ratio=overlap_ratio)
        self.tile_size = tile_size
        self.overlap_ratio = overlap_ratio
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device).eval()
        self.model_version = model_version

    def predict_image(
        self,
        image_input: Union[str, np.ndarray],
        geo_bounds: Optional[Dict[str, float]] = None,
        scene_id: str = "scene_sar_001"
    ) -> Dict[str, Any]:
        """
        Executes full inference pipeline on input SAR image.
        """
        if isinstance(image_input, str):
            raw_img = np.array(Image.open(image_input))
        else:
            raw_img = image_input

        h, w = raw_img.shape[:2]

        # 1. Normalize
        norm_img = self.preprocessor(raw_img)

        # 2. Sliding window inference if larger than tile_size, or direct pass
        if h > self.tile_size or w > self.tile_size:
            stitcher = SlidingWindowStitcher(h, w)
            tiles = self.tiler.tile_image(norm_img)

            with torch.no_grad():
                for tile, coords in tiles:
                    t_tensor = torch.from_numpy(tile).permute(2, 0, 1).unsqueeze(0).float().to(self.device)
                    probs = torch.sigmoid(self.model(t_tensor)).squeeze().cpu().numpy()
                    stitcher.add_prediction(probs, coords)

            full_prob_map = stitcher.get_stitched_probabilities()
        else:
            t_tensor = torch.from_numpy(norm_img).permute(2, 0, 1).unsqueeze(0).float().to(self.device)
            with torch.no_grad():
                full_prob_map = torch.sigmoid(self.model(t_tensor)).squeeze().cpu().numpy()

        # 3. Postprocess
        binary_mask = postprocess_probability_map(full_prob_map, threshold=self.threshold)

        # 4. Extract GeoJSON slicks
        geojson_res = mask_to_geojson_features(
            binary_mask,
            prob_map=full_prob_map,
            geo_bounds=geo_bounds,
            scene_id=scene_id
        )

        return {
            "scene_id": scene_id,
            "model_version": self.model_version,
            "threshold": self.threshold,
            "slicks_detected": len(geojson_res["features"]),
            "binary_mask": binary_mask,
            "probability_map": full_prob_map,
            "geojson": geojson_res
        }
