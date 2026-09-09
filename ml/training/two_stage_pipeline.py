"""
Two-Stage Oil Spill & Look-alike Refinement Architecture.
Stage A: Segment dark surface anomalies.
Stage B: Classify candidate connected components as True Oil vs Look-alike.
"""

import torch
import numpy as np
import cv2
from typing import Dict, Any, Tuple
from ml.models.base import BaseSegmentationModel
from ml.models.classifier import OilLookalikeClassifier
from ml.evaluation.object_eval import extract_slick_instances

class TwoStageOilDetector:
    def __init__(
        self,
        segmenter: BaseSegmentationModel,
        classifier: OilLookalikeClassifier,
        seg_threshold: float = 0.40,
        classifier_threshold: float = 0.50,
        device: torch.device = None
    ):
        self.segmenter = segmenter
        self.classifier = classifier
        self.seg_threshold = seg_threshold
        self.classifier_threshold = classifier_threshold
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.segmenter.to(self.device).eval()
        self.classifier.to(self.device).eval()

    def predict(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Takes raw image (H, W, 3).
        1. Stage A: Run Segmentation to find candidate anomalies.
        2. Stage B: For each connected component, classify whether it is Oil or Look-alike.
        Returns:
            refined_mask: (H, W) uint8 with 1 for validated oil
            probability_map: (H, W) float32
            metadata: Dict with detected instances and classifications
        """
        h, w = image.shape[:2]

        # Stage A: Segmentation
        tensor_img = torch.from_numpy(image.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0).to(self.device)
        with torch.no_grad():
            stage_a_probs = torch.sigmoid(self.segmenter(tensor_img)).squeeze().cpu().numpy()

        candidate_binary = (stage_a_probs >= self.seg_threshold).astype(np.uint8)
        instances = extract_slick_instances(candidate_binary, min_area=15)

        refined_mask = np.zeros((h, w), dtype=np.uint8)
        refined_probs = stage_a_probs.copy()
        instance_reports = []

        # Stage B: Classify each candidate connected component
        with torch.no_grad():
            for inst in instances:
                x, y, bw, bh = inst["bbox"]
                # Add context padding around bounding box
                pad = 16
                x1 = max(0, x - pad)
                y1 = max(0, y - pad)
                x2 = min(w, x + bw + pad)
                y2 = min(h, y + bh + pad)

                crop = image[y1:y2, x1:x2]
                # Resize crop to 64x64 for classifier
                crop_resized = cv2.resize(crop, (64, 64))
                tensor_crop = torch.from_numpy(crop_resized.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0).to(self.device)

                class_probs = self.classifier.predict_proba(tensor_crop).squeeze().cpu().numpy()
                # Classes: 0: Background, 1: True Oil, 2: Lookalike
                p_oil = float(class_probs[1])
                p_look = float(class_probs[2])

                is_oil = (p_oil >= self.classifier_threshold) and (p_oil > p_look)

                instance_reports.append({
                    "id": inst["id"],
                    "area_pixels": inst["area"],
                    "centroid": inst["centroid"],
                    "prob_oil": p_oil,
                    "prob_lookalike": p_look,
                    "validated_as_oil": is_oil
                })

                if is_oil:
                    # Keep this instance in refined mask
                    refined_mask[inst["mask"]] = 1
                else:
                    # Suppress look-alike false alarm!
                    refined_probs[inst["mask"]] *= 0.1

        metadata = {
            "total_candidates_detected": len(instances),
            "validated_oil_slicks": sum(1 for r in instance_reports if r["validated_as_oil"]),
            "suppressed_lookalikes": sum(1 for r in instance_reports if not r["validated_as_oil"]),
            "instances": instance_reports
        }

        return refined_mask, refined_probs, metadata
