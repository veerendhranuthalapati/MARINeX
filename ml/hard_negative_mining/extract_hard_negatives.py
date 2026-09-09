"""
Hard Negative Mining Module for Look-alike False Alarm Reduction.
Identifies false positive predictions on training/validation splits and compiles hard negative pools.
Never mines from the test set.
"""

import os
import json
import torch
import numpy as np
from PIL import Image
from typing import List, Dict, Any
from ml.models.base import BaseSegmentationModel
from ml.evaluation.metrics import compute_pixel_metrics

def extract_hard_negatives(
    model: BaseSegmentationModel,
    candidate_samples: List[Dict[str, Any]],
    threshold: float = 0.50,
    fp_pixel_threshold: int = 50,
    output_path: str = "data/hard_negatives/hard_negatives_manifest.json"
) -> List[Dict[str, Any]]:
    """
    Runs model inference over non-test samples to identify look-alikes that cause false positives.
    """
    model.eval()
    hard_negatives = []

    for s in candidate_samples:
        img_arr = np.array(Image.open(s["image_path"]))
        mask_arr = np.array(Image.open(s["mask_path"]))
        gt_binary = (mask_arr == 1).astype(np.uint8)

        # Run inference
        tensor_img = torch.from_numpy(img_arr.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
        with torch.no_grad():
            probs = torch.sigmoid(model(tensor_img)).squeeze().cpu().numpy()

        pred_bin = (probs >= threshold).astype(np.uint8)

        # False positives are where model predicted oil (1) but GT is not oil (0)
        fp_mask = (pred_bin == 1) & (gt_binary == 0)
        fp_count = int(np.sum(fp_mask))

        if fp_count >= fp_pixel_threshold:
            # This is a hard negative (likely a look-alike or high clutter)
            hard_negatives.append({
                "sample_id": s["sample_id"],
                "image_path": s["image_path"],
                "mask_path": s["mask_path"],
                "fp_pixels": fp_count,
                "has_lookalike": s.get("has_lookalike", False),
                "fp_ratio": float(fp_count / gt_binary.size)
            })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(hard_negatives, f, indent=2)

    print(f"Extracted {len(hard_negatives)} hard negative samples (saved to {output_path}).")
    return hard_negatives

if __name__ == "__main__":
    pass
