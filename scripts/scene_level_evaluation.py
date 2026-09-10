"""
Phase 5: Scene-level generalization evaluation for MARINeX (SIH26143).
=======================================================================
Runs the frozen UNet on all test patches, groups results by parent_scene_id,
and computes per-scene and aggregate segmentation metrics.

Usage:
    & ".venv\\Scripts\\python.exe" scripts/scene_level_evaluation.py
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


def compute_agg_metrics(patch_results):
    all_gt = np.concatenate([r["gt"] for r in patch_results])
    all_pred = np.concatenate([r["pred"] for r in patch_results])
    all_prob = np.concatenate([r["prob"] for r in patch_results])
    return compute_pixel_metrics(all_gt, all_pred, all_prob)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device)

    inv = scan_dataset(DATA_DIR)
    smap = {s["sample_id"]: s for s in inv["samples"]}

    with open(SPLIT_PATH, encoding="utf-8") as f:
        split = json.load(f)
    test_ids = split["splits"]["test"]

    scene_patches = defaultdict(list)
    for sid in test_ids:
        s = smap[sid]
        scene_patches[s["parent_scene_id"]].append(s)

    scene_rows = []
    patch_rows = []
    all_patch_results = []

    for scene_id in sorted(scene_patches.keys()):
        patches = scene_patches[scene_id]
        patch_results = []

        for s in patches:
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
            patch_results.append({"gt": gt, "pred": pred, "prob": prob, "metrics": metrics})

            oil_px = int(np.sum(gt == 1))
            conf = float(np.mean(prob[pred == 1])) if np.any(pred == 1) else 0.0
            patch_rows.append({
                "sample_id": s["sample_id"],
                "scene_id": scene_id,
                "oil_pixels": oil_px,
                "mean_prob": round(float(np.mean(prob)), 6),
                "mean_confidence": round(conf, 6),
                "iou": round(metrics["iou"], 6),
            })

        agg = compute_agg_metrics(patch_results)
        total_oil = sum(int(np.sum(r["gt"] == 1)) for r in patch_results)
        mean_prob = float(np.mean([np.mean(r["prob"]) for r in patch_results]))
        probs_with_conf = [
            float(np.mean(r["prob"][r["pred"] == 1])) if np.any(r["pred"] == 1) else 0.0
            for r in patch_results
        ]
        mean_conf = float(np.mean(probs_with_conf)) if probs_with_conf else 0.0

        scene_rows.append({
            "scene_id": scene_id,
            "n_patches": len(patches),
            "iou": round(agg["iou"], 6),
            "dice": round(agg["dice"], 6),
            "precision": round(agg["precision"], 6),
            "recall": round(agg["recall"], 6),
            "fpr": round(agg["false_positive_rate"], 6),
            "fnr": round(agg["false_negative_rate"], 6),
            "oil_pixel_count": total_oil,
            "mean_prob": round(mean_prob, 6),
            "mean_confidence": round(mean_conf, 6),
        })
        all_patch_results.extend(patch_results)

    csv_path = REPORTS_DIR / "scene_level_results.csv"
    fieldnames = list(scene_rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(scene_rows)

    aggregate = compute_agg_metrics(all_patch_results) if all_patch_results else {}

    metric_keys = ["iou", "dice", "precision", "recall", "fpr", "fnr"]
    stats = {}
    for mk in metric_keys:
        vals = np.array([r[mk] for r in scene_rows], dtype=np.float64)
        stats[mk] = {
            "mean": float(np.mean(vals)),
            "median": float(np.median(vals)),
            "std": float(np.std(vals)),
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
        }

    best_idx = int(np.argmax([r["iou"] for r in scene_rows]))
    worst_idx = int(np.argmin([r["iou"] for r in scene_rows]))
    median_idx = int(np.argsort([r["iou"] for r in scene_rows])[len(scene_rows) // 2])

    md_lines = [
        "# Scene-Level Generalization Report",
        "",
        f"**Model**: `marinex_unet_v1.pt` | **Threshold**: {THRESHOLD} | **Test scenes**: {len(scene_rows)} | **Test patches**: {len(all_patch_results)}",
        "",
        "## Per-Scene Results",
        "",
        "| scene_id | n_patches | IoU | Dice | Precision | Recall | FPR | FNR | oil_px | mean_prob | mean_conf |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in scene_rows:
        md_lines.append(
            f"| {r['scene_id']} | {r['n_patches']} | {r['iou']:.4f} | {r['dice']:.4f} | "
            f"{r['precision']:.4f} | {r['recall']:.4f} | {r['fpr']:.4f} | {r['fnr']:.4f} | "
            f"{r['oil_pixel_count']} | {r['mean_prob']:.4f} | {r['mean_confidence']:.4f} |"
        )

    md_lines += [
        "",
        "## Aggregate Test Metrics",
        "",
    ]
    if aggregate:
        md_lines.append(f"- **IoU**: {aggregate['iou']:.4f}")
        md_lines.append(f"- **Dice**: {aggregate['dice']:.4f}")
        md_lines.append(f"- **Precision**: {aggregate['precision']:.4f}")
        md_lines.append(f"- **Recall**: {aggregate['recall']:.4f}")
        md_lines.append(f"- **FPR**: {aggregate['false_positive_rate']:.4f}")
        md_lines.append(f"- **FNR**: {aggregate['false_negative_rate']:.4f}")

    md_lines += [
        "",
        "## Per-Scene Metric Statistics",
        "",
        "| Metric | Mean | Median | Std Dev | Min | Max |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for mk in metric_keys:
        s = stats[mk]
        md_lines.append(
            f"| {mk.upper()} | {s['mean']:.4f} | {s['median']:.4f} | {s['std']:.4f} | {s['min']:.4f} | {s['max']:.4f} |"
        )

    md_lines += [
        "",
        "## Highlights",
        "",
        f"- **Best scene**: {scene_rows[best_idx]['scene_id']} (IoU={scene_rows[best_idx]['iou']:.4f})",
        f"- **Median scene**: {scene_rows[median_idx]['scene_id']} (IoU={scene_rows[median_idx]['iou']:.4f})",
        f"- **Worst scene**: {scene_rows[worst_idx]['scene_id']} (IoU={scene_rows[worst_idx]['iou']:.4f})",
    ]

    md_path = REPORTS_DIR / "scene_level_report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print("=== Scene-Level Evaluation Summary ===")
    print(f"Test scenes: {len(scene_rows)} | Test patches: {len(all_patch_results)}")
    if aggregate:
        print(f"Aggregate IoU={aggregate['iou']:.4f}  Dice={aggregate['dice']:.4f}  "
              f"Prec={aggregate['precision']:.4f}  Rec={aggregate['recall']:.4f}")
    print(f"Best:  {scene_rows[best_idx]['scene_id']}  IoU={scene_rows[best_idx]['iou']:.4f}")
    print(f"Worst: {scene_rows[worst_idx]['scene_id']}  IoU={scene_rows[worst_idx]['iou']:.4f}")
    for mk in metric_keys:
        s = stats[mk]
        print(f"  {mk.upper():>10s}  mean={s['mean']:.4f}  median={s['median']:.4f}  std={s['std']:.4f}")
    print(f"CSV  -> {csv_path}")
    print(f"MD   -> {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
