"""
Config-Driven Evaluation Entrypoint (Phase 46/47).

Evaluates a trained checkpoint ONCE on the held-out test set with a calibrated
threshold, exporting reports/final_ml_benchmark.csv and provenance metadata.

Usage:
    python ml/evaluate.py --checkpoint models/checkpoints/unetpp_best.pt \
                          --threshold 0.40 --model unet_plus_plus
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import torch
import numpy as np
from torch.utils.data import DataLoader

from ml.data.dataset import Sentinel1SARSpillDataset, sar_collate_fn
from ml.models.registry import build_model
from ml.evaluation.metrics import compute_pixel_metrics
from ml.evaluation.calibration import compute_expected_calibration_error
from ml.evaluation.object_eval import evaluate_object_detection


def evaluate_checkpoint(
    checkpoint: str,
    model_name: str,
    threshold: float,
    channels: str = "VV_VH_DIFF",
    split_path: str = "data/splits/split_group_aware_v1.json",
    dataset_root: str = "data/datasets/sentinel1_primary",
    export_csv: str = "reports/final_ml_benchmark.csv",
) -> dict:
    from ml.data_audit.dataset_inventory import scan_dataset

    with open(split_path, "r", encoding="utf-8") as f:
        split = json.load(f)
    inv = scan_dataset(dataset_root)
    sample_map = {s["sample_id"]: s for s in inv["samples"]}
    test_ids = split["splits"]["test"]
    test_samples = [sample_map[sid] for sid in test_ids]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ds_test = Sentinel1SARSpillDataset(test_samples, channels=channels, is_training=False)
    loader = DataLoader(ds_test, batch_size=len(test_samples), shuffle=False, collate_fn=sar_collate_fn)

    model = build_model(model_name, in_channels=3, num_classes=1)
    ckpt = torch.load(checkpoint, map_location="cpu")
    model.load_state_dict(ckpt["state_dict"])
    model.to(device).eval()

    images, masks, _ = next(iter(loader))
    images = images.to(device)

    # Measure single-image inference latency (mean over a warm-up + timed passes).
    model.eval()
    with torch.no_grad():
        _ = model(images[:1])  # warm-up
    import time as _time
    t_acc = 0.0
    n_timed = min(images.size(0), 5)
    with torch.no_grad():
        for i in range(n_timed):
            t0 = _time.perf_counter()
            _ = model(images[i:i + 1])
            t_acc += _time.perf_counter() - t0
    latency_ms = t_acc / n_timed * 1000.0

    with torch.no_grad():
        probs = torch.sigmoid(model(images)).squeeze(1).cpu().numpy()
    preds = (probs >= threshold).astype(np.uint8)
    targets = masks.numpy().astype(np.uint8)

    px = compute_pixel_metrics(targets, preds, probs)
    ece = compute_expected_calibration_error(targets, probs)
    brier = 0.0
    try:
        from ml.evaluation.calibration import compute_brier_score
        brier = compute_brier_score(targets, probs)
    except Exception:
        pass
    obj = evaluate_object_detection(targets, preds)

    result = {
        "model": model_name,
        "checkpoint": checkpoint,
        "dataset": dataset_root,
        "input": channels,
        "threshold": float(threshold),
        "IoU": px["iou"],
        "Dice": px["dice"],
        "precision": px["precision"],
        "recall": px["recall"],
        "PR-AUC": px["pr_auc"],
        "FPR": px["false_positive_rate"],
        "FNR": px["false_negative_rate"],
        "ECE": ece["expected_calibration_error"],
        "Brier": brier,
        "latency_ms": latency_ms,
        "object_precision": obj["object_precision"],
        "object_recall": obj["object_recall"],
        "object_f1": obj["object_f1"],
    }

    if export_csv:
        Path(export_csv).parent.mkdir(parents=True, exist_ok=True)
        cols = ["model", "dataset", "input", "IoU", "Dice", "precision", "recall",
                "PR-AUC", "FPR", "FNR", "ECE", "Brier", "threshold", "latency_ms"]
        exists = Path(export_csv).exists()
        with open(export_csv, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if not exists:
                w.writeheader()
            w.writerow({c: result[c] for c in cols})
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--threshold", type=float, default=0.4)
    ap.add_argument("--channels", default="VV_VH_DIFF")
    ap.add_argument("--split-path", default="data/splits/split_group_aware_v1.json")
    ap.add_argument("--dataset-root", default="data/datasets/sentinel1_primary")
    ap.add_argument("--no-csv", action="store_true")
    args = ap.parse_args()

    res = evaluate_checkpoint(
        checkpoint=args.checkpoint,
        model_name=args.model,
        threshold=args.threshold,
        channels=args.channels,
        split_path=args.split_path,
        dataset_root=args.dataset_root,
        export_csv=None if args.no_csv else "reports/final_ml_benchmark.csv",
    )
    print(json.dumps(res, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())