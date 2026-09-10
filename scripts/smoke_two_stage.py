"""
Smoke validation of the fixed two-stage pipeline (train/eval normalization aligned).
Loads the existing SegFormer checkpoint, trains the Stage-B classifier on Stage-A
instance crops, and evaluates on the held-out test split. Exits nonzero on failure.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
import numpy as np
from PIL import Image

from ml.data_audit.dataset_inventory import scan_dataset
from ml.models.registry import build_model
from ml.training.two_stage_pipeline import (
    TwoStageOilDetector,
    prepare_stage_b_crops_for_training,
    train_stage_b_classifier,
)
from ml.data.transforms import SARPreprocessor
from ml.evaluation.metrics import compute_pixel_metrics


def main() -> int:
    device = torch.device("cpu")
    split = json.load(open("data/splits/split_group_aware_v1.json", encoding="utf-8"))
    inv = scan_dataset("data/datasets/sentinel1_primary")
    sample_map = {s["sample_id"]: s for s in inv["samples"]}
    train_samples = [sample_map[sid] for sid in split["splits"]["train"]]
    test_samples = [sample_map[sid] for sid in split["splits"]["test"]]

    seg = build_model("segformer", in_channels=3, num_classes=1)
    ckpt = torch.load("models/checkpoints/segformer_primary_best.pt", map_location="cpu")
    seg.load_state_dict(ckpt["state_dict"])
    print("loaded segformer checkpoint OK")

    crops, labels, log = prepare_stage_b_crops_for_training(
        seg, train_samples, device=device, seg_threshold=0.40, min_area=15
    )
    print(f"stage-b crops: {len(labels)} (labels oil={int((labels==1).sum())}, lookalike={int((labels==2).sum())}, bg={int((labels==0).sum())})")
    if len(labels) == 0:
        print("FAIL: no stage-b crops generated")
        return 1

    clf = build_model("classifier", in_channels=3, num_classes=3)
    history = train_stage_b_classifier(clf, crops, labels, device=device, epochs=12)
    print(f"classifier trained: final_loss={history['final_loss']:.4f}")

    twostage = TwoStageOilDetector(seg, clf, device=device, preprocessor=SARPreprocessor(strategy="percentile"))

    targets, preds, probs = [], [], []
    for s in test_samples:
        img = np.array(Image.open(s["image_path"]))
        mask = (np.array(Image.open(s["mask_path"])) == 1).astype(np.uint8)
        rm, rp, meta = twostage.predict(img)
        targets.append(mask)
        preds.append(rm)
        probs.append(rp)
        print(f"  {s['sample_id']}: candidates={meta['total_candidates_detected']} oil={meta['validated_oil_slicks']} suppressed={meta['suppressed_lookalikes']}")

    m = compute_pixel_metrics(np.stack(targets), np.stack(preds), np.stack(probs))
    print(f"TWO-STAGE TEST IoU={m['iou']:.4f} Dice={m['dice']:.4f} Prec={m['precision']:.4f} Rec={m['recall']:.4f}")

    if m["iou"] <= 0.05:
        print("FAIL: two-stage metrics are still degenerate")
        return 1
    print("PASS: two-stage pipeline produces real metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())