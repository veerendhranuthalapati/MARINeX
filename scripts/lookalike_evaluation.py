"""
Phase 7: Look-alike evaluation for MARINeX (SIH26143).
=======================================================
Runs the frozen UNet on all test patches and evaluates performance on
oil-only, look-alike, and clean patches separately. Measures the model's
ability to reject look-alike confusion and avoid false alarms on clean water.

Usage:
    & ".venv\\Scripts\\python.exe" scripts/lookalike_evaluation.py
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
from collections import defaultdict

from ml.data.transforms import SARPreprocessor
from ml.data_audit.dataset_inventory import scan_dataset
from ml.models.registry import build_model
from ml.evaluation.metrics import compute_pixel_metrics

THRESHOLD = 0.70
REJECTION_CONF_THRESHOLD = 0.30
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


def classify_patch(sample):
    has_oil = sample.get("has_oil", False)
    has_lookalike = sample.get("has_lookalike", False)
    if has_lookalike:
        return "lookalike"
    if has_oil:
        return "oil"
    return "clean"


def group_label(patch_list):
    if not patch_list:
        return {"n_patches": 0, "iou": float("nan"), "dice": float("nan"),
                "precision": float("nan"), "recall": float("nan"),
                "fpr": float("nan"), "fnr": float("nan"), "mean_confidence": float("nan")}
    agg = compute_agg_metrics(patch_list)
    mean_conf = float(np.mean([r["mean_confidence"] for r in patch_list]))
    return {
        "n_patches": len(patch_list),
        "iou": round(agg["iou"], 6),
        "dice": round(agg["dice"], 6),
        "precision": round(agg["precision"], 6),
        "recall": round(agg["recall"], 6),
        "fpr": round(agg["false_positive_rate"], 6),
        "fnr": round(agg["false_negative_rate"], 6),
        "mean_confidence": round(mean_conf, 6),
    }


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lookalike_dir = REPORTS_DIR / "lookalikes"
    lookalike_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device)

    inv = scan_dataset(DATA_DIR)
    smap = {s["sample_id"]: s for s in inv["samples"]}

    with open(SPLIT_PATH, encoding="utf-8") as f:
        split = json.load(f)
    test_ids = split["splits"]["test"]

    groups = {"oil": [], "lookalike": [], "clean": []}
    all_patch_rows = []

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

        metrics = compute_pixel_metrics(gt, pred, prob)
        mean_conf = float(np.mean(prob[pred == 1])) if np.any(pred == 1) else 0.0
        max_prob = float(np.max(prob))

        group = classify_patch(s)
        groups[group].append({
            "gt": gt, "pred": pred, "prob": prob,
            "metrics": metrics, "mean_confidence": mean_conf,
            "sample_id": sid,
        })

        all_patch_rows.append({
            "sample_id": sid,
            "group": group,
            "has_oil": s.get("has_oil", False),
            "has_lookalike": s.get("has_lookalike", False),
            "iou": round(metrics["iou"], 6),
            "dice": round(metrics["dice"], 6),
            "precision": round(metrics["precision"], 6),
            "recall": round(metrics["recall"], 6),
            "fpr": round(metrics["false_positive_rate"], 6),
            "fnr": round(metrics["false_negative_rate"], 6),
            "mean_confidence": round(mean_conf, 6),
            "max_probability": round(max_prob, 6),
        })

    group_summaries = {}
    for gname in ["oil", "lookalike", "clean"]:
        group_summaries[gname] = group_label(groups[gname])

    lookalike_patches = groups["lookalike"]
    if lookalike_patches:
        rejected = sum(1 for p in lookalike_patches if p["mean_confidence"] < REJECTION_CONF_THRESHOLD)
        rejection_rate = rejected / len(lookalike_patches)
    else:
        rejection_rate = float("nan")

    clean_patches = groups["clean"]
    if clean_patches:
        false_detections = sum(1 for p in clean_patches if p["metrics"]["fp_pixels"] > 0)
        false_detection_rate = false_detections / len(clean_patches)
    else:
        false_detection_rate = float("nan")

    csv_path = REPORTS_DIR / "lookalike_results.csv"
    fieldnames = list(all_patch_rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_patch_rows)

    md_lines = [
        "# Look-alike Evaluation Report",
        "",
        f"**Model**: `marinex_unet_v1.pt` | **Threshold**: {THRESHOLD} | "
        f"**Rejection conf threshold**: {REJECTION_CONF_THRESHOLD}",
        f"**Test patches**: {len(test_ids)}",
        "",
        "## Patch Group Counts",
        "",
        f"- **OIL** (pure oil, no look-alike): {len(groups['oil'])}",
        f"- **LOOK-ALIKE** (may also have oil): {len(groups['lookalike'])}",
        f"- **CLEAN** (neither oil nor look-alike): {len(groups['clean'])}",
        "",
        "## Per-Group Metrics",
        "",
        "| Group | n_patches | IoU | Dice | Precision | Recall | FPR | FNR | mean_conf |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    def _f(v):
        if isinstance(v, float) and np.isnan(v):
            return "N/A"
        return f"{v:.4f}" if isinstance(v, float) else str(v)

    for gname in ["oil", "lookalike", "clean"]:
        s = group_summaries[gname]
        md_lines.append(
            f"| {gname.upper()} | {s['n_patches']} | {_f(s['iou'])} | {_f(s['dice'])} | "
            f"{_f(s['precision'])} | {_f(s['recall'])} | {_f(s['fpr'])} | {_f(s['fnr'])} | "
            f"{_f(s['mean_confidence'])} |"
        )

    md_lines += [
        "",
        "## Look-alike Rejection Rate",
        "",
        f"Patches with mean confidence < {REJECTION_CONF_THRESHOLD} (model correctly ignoring): "
        f"**{_f(rejection_rate)}** ({rejected if lookalike_patches else 0}/{len(lookalike_patches)})",
        "",
        "## Clean Patch False Detection Rate",
        "",
        f"Clean patches with any FP pixel: **{_f(false_detection_rate)}** "
        f"({false_detections if clean_patches else 0}/{len(clean_patches)})",
    ]

    md_path = REPORTS_DIR / "lookalike_report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print("=== Look-alike Evaluation Summary ===")
    for gname in ["oil", "lookalike", "clean"]:
        s = group_summaries[gname]
        iou_s = "N/A" if np.isnan(s["iou"]) else f"{s['iou']:.4f}"
        print(f"  {gname.upper():>10s}  n={s['n_patches']:3d}  IoU={iou_s}  "
              f"mean_conf={s['mean_confidence']:.4f}")
    rej_s = "N/A" if np.isnan(rejection_rate) else f"{rejection_rate:.4f}"
    fd_s = "N/A" if np.isnan(false_detection_rate) else f"{false_detection_rate:.4f}"
    print(f"  Look-alike rejection rate: {rej_s}")
    print(f"  Clean false detection rate: {fd_s}")
    print(f"  CSV  -> {csv_path}")
    print(f"  MD   -> {md_path}")
    print(f"  Dir  -> {lookalike_dir}/ (prepared for future examples)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
