"""
Phase 6: Slick size bucketing analysis for MARINeX (SIH26143).
===============================================================
Runs the frozen UNet on all test patches, buckets patches by oil slick size,
and computes per-bucket segmentation metrics.

Usage:
    & ".venv\\Scripts\\python.exe" scripts/slick_size_analysis.py
"""

import csv
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from PIL import Image
import torch

from ml.data.transforms import SARPreprocessor
from ml.data_audit.dataset_inventory import scan_dataset
from ml.models.registry import build_model
from ml.evaluation.metrics import compute_pixel_metrics

THRESHOLD = 0.70
MODEL_PATH = "models/best_model/marinex_unet_v1.pt"
DATA_DIR = "data/datasets/sentinel1_primary"
SPLIT_PATH = "data/splits/split_group_aware_v1.json"
REPORTS_DIR = Path("reports")

PREP = SARPreprocessor(strategy="percentile")


def load_model(device):
    model = build_model("unet", in_channels=3, num_classes=1)
    model.load_weights(MODEL_PATH, map_location=device)
    model.to(device).eval()
    return model


def run_inference(model, img_arr, device):
    norm = PREP(img_arr)
    t = torch.from_numpy(np.ascontiguousarray(norm)).permute(2, 0, 1).unsqueeze(0).to(device)
    with torch.no_grad():
        prob = torch.sigmoid(model(t)).squeeze().cpu().numpy()
    return prob


def compute_agg_metrics(patch_list):
    all_gt = np.concatenate([r["gt"] for r in patch_list])
    all_pred = np.concatenate([r["pred"] for r in patch_list])
    all_prob = np.concatenate([r["prob"] for r in patch_list])
    return compute_pixel_metrics(all_gt, all_pred, all_prob)


def classify_bucket(gt_oil_px, thresholds):
    for i, (lo, hi, label) in enumerate(thresholds):
        if lo <= gt_oil_px < hi:
            return label
    return thresholds[-1][2]


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device)

    inv = scan_dataset(DATA_DIR)
    smap = {s["sample_id"]: s for s in inv["samples"]}

    with open(SPLIT_PATH, encoding="utf-8") as f:
        split = json.load(f)
    test_ids = split["splits"]["test"]

    oil_patches = []
    all_results = []

    for sid in test_ids:
        s = smap[sid]
        img = np.array(Image.open(s["image_path"]))
        gt = (np.array(Image.open(s["mask_path"])) == 1).astype(np.uint8)
        prob = run_inference(model, img, device)
        pred = (prob >= THRESHOLD).astype(np.uint8)

        h, w = gt.shape
        if prob.shape != (h, w):
            import cv2
            prob = cv2.resize(prob, (w, h), interpolation=cv2.INTER_LINEAR)
            pred = (prob >= THRESHOLD).astype(np.uint8)

        gt_oil = int(np.sum(gt == 1))
        pred_oil = int(np.sum(pred == 1))
        conf = float(np.mean(prob[pred == 1])) if np.any(pred == 1) else 0.0
        metrics = compute_pixel_metrics(gt, pred, prob)

        entry = {
            "sample_id": sid,
            "gt_oil_pixels": gt_oil,
            "pred_oil_pixels": pred_oil,
            "mean_confidence": conf,
            "metrics": metrics,
            "gt": gt,
            "pred": pred,
            "prob": prob,
        }
        all_results.append(entry)
        if gt_oil > 0:
            oil_patches.append(entry)

    if not oil_patches:
        print("No oil patches found in test set. Cannot perform size analysis.")
        return 1

    gt_oil_sizes = np.array([e["gt_oil_pixels"] for e in oil_patches], dtype=np.float64)
    q25, q50, q75 = np.percentile(gt_oil_sizes, [25, 50, 75])

    default_thresholds = [
        (0, 50, "TINY"),
        (50, 200, "SMALL"),
        (200, 1000, "MEDIUM"),
        (1000, float("inf"), "LARGE"),
    ]

    covered = sum(1 for lo, hi, _ in default_thresholds if lo < q75 <= hi)
    if covered < 2:
        thresholds = [
            (0, max(int(q25), 1), "TINY"),
            (int(q25), max(int(q50), int(q25) + 1), "SMALL"),
            (int(q50), max(int(q75), int(q50) + 1), "MEDIUM"),
            (int(q75), float("inf"), "LARGE"),
        ]
        print("Default buckets poorly match distribution; using quartile-based thresholds.")
    else:
        thresholds = default_thresholds

    print(f"\nOil pixel distribution: min={int(gt_oil_sizes.min())}  "
          f"q25={int(q25)}  median={int(q50)}  q75={int(q75)}  max={int(gt_oil_sizes.max())}")
    print(f"Buckets: {[(lo, hi, lbl) for lo, hi, lbl in thresholds]}")

    bucket_map = {lbl: [] for _, _, lbl in thresholds}
    for entry in oil_patches:
        label = classify_bucket(entry["gt_oil_pixels"], thresholds)
        bucket_map[label].append(entry)

    bucket_rows = []
    for lo, hi, label in thresholds:
        patches = bucket_map[label]
        n = len(patches)
        if n == 0:
            bucket_rows.append({
                "bucket": label,
                "n_patches": 0,
                "iou": float("nan"),
                "dice": float("nan"),
                "precision": float("nan"),
                "recall": float("nan"),
                "fpr": float("nan"),
                "fnr": float("nan"),
                "mean_gt_oil_px": float("nan"),
                "mean_pred_oil_px": float("nan"),
                "mean_confidence": float("nan"),
            })
            continue

        agg = compute_agg_metrics(patches)
        mean_gt = float(np.mean([e["gt_oil_pixels"] for e in patches]))
        mean_pred = float(np.mean([e["pred_oil_pixels"] for e in patches]))
        mean_conf = float(np.mean([e["mean_confidence"] for e in patches]))

        bucket_rows.append({
            "bucket": label,
            "n_patches": n,
            "iou": round(agg["iou"], 6),
            "dice": round(agg["dice"], 6),
            "precision": round(agg["precision"], 6),
            "recall": round(agg["recall"], 6),
            "fpr": round(agg["false_positive_rate"], 6),
            "fnr": round(agg["false_negative_rate"], 6),
            "mean_gt_oil_px": round(mean_gt, 2),
            "mean_pred_oil_px": round(mean_pred, 2),
            "mean_confidence": round(mean_conf, 6),
        })

    csv_path = REPORTS_DIR / "slick_size_results.csv"
    fieldnames = list(bucket_rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in bucket_rows:
            w.writerow({k: ("" if isinstance(v, float) and np.isnan(v) else v) for k, v in row.items()})

    md_lines = [
        "# Slick Size Bucketing Report",
        "",
        f"**Model**: `marinex_unet_v1.pt` | **Threshold**: {THRESHOLD}",
        f"**Test patches**: {len(all_results)} | **Oil patches**: {len(oil_patches)}",
        "",
        "## Size Distribution",
        "",
        f"- Min GT oil pixels: {int(gt_oil_sizes.min())}",
        f"- Q25: {int(q25)} | Median: {int(q50)} | Q75: {int(q75)} | Max: {int(gt_oil_sizes.max())}",
        "",
        "## Per-Bucket Metrics",
        "",
        "| Bucket | n_patches | IoU | Dice | Precision | Recall | FPR | FNR | mean_gt_px | mean_pred_px | mean_conf |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in bucket_rows:
        def _f(v):
            if isinstance(v, float) and np.isnan(v):
                return "N/A"
            return f"{v:.4f}" if isinstance(v, float) else str(v)
        md_lines.append(
            f"| {row['bucket']} | {row['n_patches']} | {_f(row['iou'])} | {_f(row['dice'])} | "
            f"{_f(row['precision'])} | {_f(row['recall'])} | {_f(row['fpr'])} | {_f(row['fnr'])} | "
            f"{_f(row['mean_gt_oil_px'])} | {_f(row['mean_pred_oil_px'])} | {_f(row['mean_confidence'])} |"
        )

    active = [r for r in bucket_rows if r["n_patches"] > 0]
    if active:
        md_lines += [
            "",
            "## Summary",
            "",
            f"- Best bucket by IoU: **{max(active, key=lambda r: r['iou'])['bucket']}** "
            f"(IoU={max(active, key=lambda r: r['iou'])['iou']:.4f})",
            f"- Worst bucket by IoU: **{min(active, key=lambda r: r['iou'])['bucket']}** "
            f"(IoU={min(active, key=lambda r: r['iou'])['iou']:.4f})",
        ]

    md_path = REPORTS_DIR / "slick_size_report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print("\n=== Slick Size Analysis Summary ===")
    for row in bucket_rows:
        iou_s = "N/A" if np.isnan(row["iou"]) else f"{row['iou']:.4f}"
        print(f"  {row['bucket']:>8s}  n={row['n_patches']:3d}  IoU={iou_s}")
    print(f"CSV  -> {csv_path}")
    print(f"MD   -> {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
