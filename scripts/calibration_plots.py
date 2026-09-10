r"""Calibration Plots: reliability curve + confidence histogram (Phase 8).

Reads the frozen UNet, runs inference on all 20 test patches, computes
reliability curve data (10-bin) and confidence histogram with/without
temperature scaling (T=0.2262).

Usage:
    .venv/Scripts/python scripts/calibration_plots.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))

from ml.data.transforms import SARPreprocessor
from ml.models.registry import build_model

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

CKPT_PATH = ROOT / "models" / "best_model" / "marinex_unet_v1.pt"
SPLIT_PATH = ROOT / "data" / "splits" / "split_group_aware_v1.json"
DATASET_ROOT = ROOT / "data" / "datasets" / "sentinel1_primary"
NUM_BINS = 10
TEMPERATURE = 0.2262389063835144


def load_test_samples():
    with open(SPLIT_PATH, "r", encoding="utf-8") as f:
        splits = json.load(f)
    test_ids = splits["splits"]["test"]
    samples = []
    for pid in test_ids:
        meta_path = DATASET_ROOT / "metadata" / f"{pid}.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        img_path = DATASET_ROOT / "images" / f"{pid}.png"
        mask_path = DATASET_ROOT / "masks" / f"{pid}.png"
        samples.append({
            "sample_id": pid,
            "image_path": str(img_path),
            "mask_path": str(mask_path),
            "has_oil": meta.get("has_oil", False),
        })
    return samples


def build_and_load_model(device):
    model = build_model("unet", in_channels=3, num_classes=1)
    model.load_weights(str(CKPT_PATH), map_location=device)
    model.to(device).eval()
    return model


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def temperature_scale(probs, T):
    logits = np.log(np.clip(probs, 1e-7, 1 - 1e-7) / (1 - np.clip(probs, 1e-7, 1 - 1e-7)))
    return sigmoid(logits / T)


def compute_reliability_and_histogram(all_probs, all_gt):
    edges = np.linspace(0, 1, NUM_BINS + 1)
    reliability_rows = []
    raw_counts = np.zeros(NUM_BINS, dtype=int)

    for i in range(NUM_BINS):
        lo, hi = edges[i], edges[i + 1]
        if i < NUM_BINS - 1:
            mask = (all_probs >= lo) & (all_probs < hi)
        else:
            mask = (all_probs >= lo) & (all_probs <= hi)
        count = int(mask.sum())
        raw_counts[i] = count
        if count > 0:
            mean_pred = float(all_probs[mask].mean())
            obs_freq = float(all_gt[mask].mean())
        else:
            mean_pred = float((lo + hi) / 2)
            obs_freq = 0.0
        reliability_rows.append({
            "bin_lower": round(lo, 1),
            "bin_upper": round(hi, 1),
            "mean_predicted": round(mean_pred, 6),
            "observed_frequency": round(obs_freq, 6),
            "count": count,
        })

    calibrated_probs = temperature_scale(all_probs, TEMPERATURE)
    cal_counts = np.zeros(NUM_BINS, dtype=int)
    for i in range(NUM_BINS):
        lo, hi = edges[i], edges[i + 1]
        if i < NUM_BINS - 1:
            mask = (calibrated_probs >= lo) & (calibrated_probs < hi)
        else:
            mask = (calibrated_probs >= lo) & (calibrated_probs <= hi)
        cal_counts[i] = int(mask.sum())

    hist_rows = []
    for i in range(NUM_BINS):
        lo, hi = edges[i], edges[i + 1]
        hist_rows.append({
            "bin_lower": round(lo, 1),
            "bin_upper": round(hi, 1),
            "raw_count": int(raw_counts[i]),
            "calibrated_count": int(cal_counts[i]),
        })

    return reliability_rows, hist_rows, calibrated_probs


def main() -> int:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    samples = load_test_samples()
    print(f"Loaded {len(samples)} test patches")

    model = build_and_load_model(device)
    prep = SARPreprocessor(strategy="percentile")

    all_probs = []
    all_gt = []

    with torch.no_grad():
        for s in samples:
            from PIL import Image
            img = np.array(Image.open(s["image_path"]))
            gt = (np.array(Image.open(s["mask_path"])) >= 1).astype(np.float32)

            norm = prep(img)
            t = torch.from_numpy(np.ascontiguousarray(norm)).permute(2, 0, 1).unsqueeze(0).to(device)
            prob = torch.sigmoid(model(t)).squeeze().cpu().numpy()

            all_probs.append(prob.flatten())
            all_gt.append(gt.flatten())

    all_probs = np.concatenate(all_probs)
    all_gt = np.concatenate(all_gt)
    print(f"Total pixels: {len(all_probs)}")

    reliability_rows, hist_rows, cal_probs = compute_reliability_and_histogram(all_probs, all_gt)

    print("\nReliability Curve Data:")
    print(f"{'Bin':>12s}  {'Mean Pred':>10s}  {'Obs Freq':>10s}  {'Count':>6s}")
    print("-" * 46)
    for r in reliability_rows:
        print(f"[{r['bin_lower']:.1f}-{r['bin_upper']:.1f}]  {r['mean_predicted']:10.6f}  {r['observed_frequency']:10.6f}  {r['count']:6d}")

    with open(REPORTS / "reliability_curve.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["bin_lower", "bin_upper", "mean_predicted", "observed_frequency", "count"])
        w.writeheader()
        w.writerows(reliability_rows)
    print(f"\nWrote {REPORTS / 'reliability_curve.csv'}")

    with open(REPORTS / "confidence_histogram.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["bin_lower", "bin_upper", "raw_count", "calibrated_count"])
        w.writeheader()
        w.writerows(hist_rows)
    print(f"Wrote {REPORTS / 'confidence_histogram.csv'}")

    calib = json.loads((REPORTS / "calibration.json").read_text())
    detailed = {
        "temperature": TEMPERATURE,
        "num_test_patches": len(samples),
        "total_pixels": int(len(all_probs)),
        "threshold": calib["threshold"],
        "ece_raw": calib["ece_raw"],
        "ece_calibrated": calib["ece_calibrated"],
        "brier_raw": calib["brier_raw"],
        "brier_calibrated": calib["brier_calibrated"],
        "reliability_curve": reliability_rows,
        "confidence_histogram": hist_rows,
        "raw_prob_stats": {
            "mean": round(float(all_probs.mean()), 6),
            "std": round(float(all_probs.std()), 6),
            "min": round(float(all_probs.min()), 6),
            "max": round(float(all_probs.max()), 6),
        },
        "calibrated_prob_stats": {
            "mean": round(float(cal_probs.mean()), 6),
            "std": round(float(cal_probs.std()), 6),
            "min": round(float(cal_probs.min()), 6),
            "max": round(float(cal_probs.max()), 6),
        },
    }

    with open(REPORTS / "calibration_detailed.json", "w", encoding="utf-8") as f:
        json.dump(detailed, f, indent=2)
    print(f"Wrote {REPORTS / 'calibration_detailed.json'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
