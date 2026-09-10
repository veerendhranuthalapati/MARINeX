"""
Two-Stage Oil Spill & Look-alike Refinement Architecture.
Stage A: Segment dark surface anomalies with the trained segmenter.
Stage B: Classify candidate connected components as True Oil vs Look-alike.

Correctness contract:
  * Same SARPreprocessor is applied at train AND inference (both stages).
  * The Stage B classifier is trained on instance crops produced by the SAME
    Stage A segmenter pipeline that it sees at inference (no train/eval skew).
"""

import torch
import numpy as np
import cv2
from typing import Dict, Any, List, Tuple, Optional
from ml.models.base import BaseSegmentationModel
from ml.models.classifier import OilLookalikeClassifier
from ml.evaluation.object_eval import extract_slick_instances
from ml.data.transforms import SARPreprocessor

DEFAULT_CROP_SIZE = 64
DEFAULT_PAD = 16
DEFAULT_MIN_AREA = 15


class TwoStageOilDetector:
    def __init__(
        self,
        segmenter: BaseSegmentationModel,
        classifier: OilLookalikeClassifier,
        seg_threshold: float = 0.40,
        classifier_threshold: float = 0.50,
        device: Optional[torch.device] = None,
        preprocessor: Optional[SARPreprocessor] = None,
    ):
        self.segmenter = segmenter
        self.classifier = classifier
        self.seg_threshold = seg_threshold
        self.classifier_threshold = classifier_threshold
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.preprocessor = preprocessor or SARPreprocessor(strategy="percentile")

        self.segmenter.to(self.device).eval()
        self.classifier.to(self.device).eval()

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Return normalized (H, W, 3) float image in [0, 1] via the shared preprocessor."""
        return self.preprocessor(image)

    def predict(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Takes raw image (H, W, 3) in [0, 255] uint8.
        1. Preprocess (percentile, same as training).
        2. Stage A: Segment anomalous dark features.
        3. Stage B: Classify each connected component as Oil or Look-alike.
        Returns:
            refined_mask: (H, W) uint8 with 1 for validated oil
            probability_map: (H, W) float32
            metadata: Dict with detected instances and classifications
        """
        h, w = image.shape[:2]
        processed = self._preprocess(image)

        # Stage A
        tensor_img = torch.from_numpy(np.ascontiguousarray(processed)).permute(2, 0, 1).unsqueeze(0).to(self.device)
        with torch.no_grad():
            stage_a_probs = torch.sigmoid(self.segmenter(tensor_img)).squeeze().cpu().numpy()

        if stage_a_probs.shape != (h, w):
            stage_a_probs = cv2.resize(stage_a_probs, (w, h), interpolation=cv2.INTER_LINEAR)

        candidate_binary = (stage_a_probs >= self.seg_threshold).astype(np.uint8)
        instances = extract_slick_instances(candidate_binary, min_area=DEFAULT_MIN_AREA)

        refined_mask = np.zeros((h, w), dtype=np.uint8)
        refined_probs = stage_a_probs.copy()
        instance_reports: List[Dict[str, Any]] = []

        # Stage B: classify each candidate crop from the SAME preprocessed image.
        with torch.no_grad():
            for inst in instances:
                x, y, bw, bh = inst["bbox"]
                x1 = max(0, x - DEFAULT_PAD)
                y1 = max(0, y - DEFAULT_PAD)
                x2 = min(w, x + bw + DEFAULT_PAD)
                y2 = min(h, y + bh + DEFAULT_PAD)

                crop = processed[y1:y2, x1:x2]
                crop_resized = cv2.resize(crop, (DEFAULT_CROP_SIZE, DEFAULT_CROP_SIZE))
                tensor_crop = torch.from_numpy(np.ascontiguousarray(crop_resized)).permute(2, 0, 1).unsqueeze(0).to(self.device)

                class_probs = self.classifier.predict_proba(tensor_crop).squeeze().cpu().numpy()
                p_oil = float(class_probs[1]) if class_probs.size == 3 else float(class_probs[1])
                p_look = float(class_probs[2]) if class_probs.size == 3 else 0.0
                is_oil = (p_oil >= self.classifier_threshold) and (p_oil > p_look)

                instance_reports.append({
                    "id": inst["id"],
                    "area_pixels": inst["area"],
                    "centroid": list(inst["centroid"]),
                    "prob_oil": p_oil,
                    "prob_lookalike": p_look,
                    "validated_as_oil": bool(is_oil),
                })

                if is_oil:
                    refined_mask[inst["mask"]] = 1
                else:
                    refined_probs[inst["mask"]] *= 0.1

        metadata = {
            "total_candidates_detected": len(instances),
            "validated_oil_slicks": int(sum(1 for r in instance_reports if r["validated_as_oil"])),
            "suppressed_lookalikes": int(sum(1 for r in instance_reports if not r["validated_as_oil"])),
            "instances": instance_reports,
        }
        return refined_mask, refined_probs, metadata


def prepare_stage_b_crops_for_training(
    segmenter: BaseSegmentationModel,
    sample_records: List[Dict[str, Any]],
    device: Optional[torch.device] = None,
    preprocessor: Optional[SARPreprocessor] = None,
    seg_threshold: float = 0.40,
    crop_size: int = DEFAULT_CROP_SIZE,
    padding: int = DEFAULT_PAD,
    min_area: int = DEFAULT_MIN_AREA,
) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
    """
    Extracts instance crops through the SAME Stage A pipeline used at inference,
    labeling each crop by the dominant ground-truth class within its bbox:
      0 background / unknown, 1 oil, 2 look-alike.

    Returns (crops array (N, 64, 64, 3) float [0,1], labels array (N,), log).
    """
    from PIL import Image
    seg = segmenter.to(device).eval() if device is None or segmenter is not None else segmenter
    if device is not None:
        seg = segmenter.to(device).eval()
    prep = preprocessor or SARPreprocessor(strategy="percentile")

    crops: List[np.ndarray] = []
    labels: List[int] = []
    log: List[Dict[str, Any]] = []

    with torch.no_grad():
        for rec in sample_records:
            img = np.array(Image.open(rec["image_path"]))
            mask = np.array(Image.open(rec["mask_path"]))
            processed = prep(img)
            tensor_img = torch.from_numpy(np.ascontiguousarray(processed)).permute(2, 0, 1).unsqueeze(0).to(device)
            probs = torch.sigmoid(seg(tensor_img)).squeeze().cpu().numpy()

            h, w = mask.shape[:2]
            if probs.shape != (h, w):
                probs = cv2.resize(probs, (w, h), interpolation=cv2.INTER_LINEAR)
            binary = (probs >= seg_threshold).astype(np.uint8)
            instances = extract_slick_instances(binary, min_area=min_area)

            for inst in instances:
                x, y, bw, bh = inst["bbox"]
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(w, x + bw + padding)
                y2 = min(h, y + bh + padding)

                crop = processed[y1:y2, x1:x2]
                if crop.shape[0] < 4 or crop.shape[1] < 4:
                    continue
                crop_resized = cv2.resize(crop, (crop_size, crop_size))

                local_mask = mask[y1:y2, x1:x2]
                n_oil = int(np.sum(local_mask == 1))
                n_look = int(np.sum(local_mask == 2))
                if n_oil > 0 and n_oil >= n_look:
                    label = 1
                elif n_look > 0:
                    label = 2
                else:
                    label = 0

                crops.append(crop_resized.astype(np.float32))
                labels.append(label)
                log.append({
                    "sample_id": rec.get("sample_id"),
                    "bbox": [x1, y1, x2, y2],
                    "label": label,
                    "n_oil": n_oil,
                    "n_look": n_look,
                })

    crops_arr = np.stack(crops, axis=0) if crops else np.zeros((0, crop_size, crop_size, 3), dtype=np.float32)
    labels_arr = np.asarray(labels, dtype=np.int64) if labels else np.zeros((0,), dtype=np.int64)
    return crops_arr, labels_arr, log


def train_stage_b_classifier(
    classifier: OilLookalikeClassifier,
    crops: np.ndarray,
    labels: np.ndarray,
    device: Optional[torch.device] = None,
    epochs: int = 12,
    lr: float = 1e-3,
    batch_size: int = 16,
) -> Dict[str, Any]:
    """
    Trains the look-alike discriminator on Stage A instance crops (already
    normalized identically to inference). Returns loss history summary.
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    classifier = classifier.to(device)
    opt = torch.optim.AdamW(classifier.parameters(), lr=lr, weight_decay=1e-4)
    loss_fn = torch.nn.CrossEntropyLoss()

    n = len(labels)
    history: List[float] = []
    if n == 0:
        return {"epochs": 0, "final_loss": None, "n_crops": 0}
    if n < batch_size:
        batch_size = max(1, n // 2)

    indices = np.arange(n)
    for ep in range(epochs):
        np.random.shuffle(indices)
        ep_loss = 0.0
        steps = 0
        classifier.train()
        for start in range(0, n, batch_size):
            idx = indices[start:start + batch_size]
            xb = torch.from_numpy(crops[idx]).permute(0, 3, 1, 2).to(device)
            yb = torch.from_numpy(labels[idx]).to(device)
            opt.zero_grad()
            logits = classifier(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            ep_loss += loss.item()
            steps += 1
        history.append(ep_loss / max(steps, 1))

    return {"epochs": epochs, "final_loss": history[-1] if history else None, "n_crops": int(n), "history": history}