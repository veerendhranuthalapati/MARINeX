"""
Slick Geometry Validation.

Loads frozen UNet, runs inference on test-split patches, computes geometry
properties from both predicted and ground-truth masks, then reports per-patch
and aggregate geometry errors.
"""

from __future__ import annotations

import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import cv2
import numpy as np
import pandas as pd
import torch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "best_model" / "marinex_unet_v1.pt"
SPLIT_PATH = ROOT / "data" / "splits" / "split_group_aware_v1.json"
IMAGES_DIR = ROOT / "data" / "datasets" / "sentinel1_primary" / "images"
MASKS_DIR = ROOT / "data" / "datasets" / "sentinel1_primary" / "masks"
REPORTS_DIR = ROOT / "reports"

PIXEL_SCALE_M = 30.0
PIXEL_AREA_KM2 = (PIXEL_SCALE_M / 1000.0) ** 2
THRESHOLD = 0.70

sys.path.insert(0, str(ROOT))
from ml.models.unet import UNetBaseline
from ml.data.transforms import SARPreprocessor

PREP = SARPreprocessor(strategy="percentile")


def _load_model() -> UNetBaseline:
    model = UNetBaseline(in_channels=3, num_classes=1, base_features=32)
    model.load_weights(str(MODEL_PATH), map_location=torch.device("cpu"))
    model.eval()
    return model


def _load_test_patches() -> list[str]:
    with open(SPLIT_PATH, "r", encoding="utf-8") as f:
        splits = json.load(f)
    return sorted(splits["splits"]["test"])


def _predict_mask(model: UNetBaseline, image: np.ndarray) -> np.ndarray:
    """image: HWC uint8 -> binary mask H W uint8 (percentile preprocessing)."""
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 and image.shape[2] == 3 else image
    norm = PREP(rgb)
    tensor = torch.from_numpy(np.ascontiguousarray(norm)).permute(2, 0, 1).unsqueeze(0).float()
    with torch.no_grad():
        mask = model.predict_mask(tensor, threshold=THRESHOLD)
    return mask.squeeze().cpu().numpy().astype(np.uint8)


def _geometry_contours(mask: np.ndarray):
    """Compute geometry from a binary mask using cv2.findContours + minAreaRect."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    area_px = cv2.contourArea(largest)
    if area_px < 1.0:
        return None
    rect = cv2.minAreaRect(largest)
    (cx, cy), (w, h), angle = rect
    perimeter_px = cv2.arcLength(largest, True)
    hull = cv2.convexHull(largest)
    hull_area = cv2.contourArea(hull)
    hull_perim = cv2.arcLength(hull, True)
    compactness = (4.0 * np.pi * area_px) / (perimeter_px ** 2) if perimeter_px > 0 else 0.0
    return {
        "area_px": area_px,
        "centroid_x": cx,
        "centroid_y": cy,
        "perimeter_px": perimeter_px,
        "angle_deg": angle,
        "compactness": compactness,
        "hull_area_px": hull_area,
        "hull_perimeter_px": hull_perim,
    }


def _geometry_numpy(mask: np.ndarray):
    """Fallback: numpy boundary + PCA for geometry."""
    boundary = np.argwhere(mask > 0)
    if len(boundary) < 3:
        return None
    area_px = float(len(boundary))
    cy, cx = boundary.mean(axis=0)
    diffs = boundary - boundary.mean(axis=0)
    cov = np.cov(diffs.T) if diffs.shape[0] > 1 else np.eye(2) * 0.001
    eigvals, eigvecs = np.linalg.eigh(cov)
    principal = eigvecs[:, np.argmax(eigvals)]
    angle_deg = float(np.degrees(np.arctan2(principal[1], principal[0])))
    perimeter_px = float(len(boundary))
    compactness = (4.0 * np.pi * area_px) / (perimeter_px ** 2) if perimeter_px > 0 else 0.0
    return {
        "area_px": area_px,
        "centroid_x": float(cx),
        "centroid_y": float(cy),
        "perimeter_px": perimeter_px,
        "angle_deg": angle_deg,
        "compactness": compactness,
        "hull_area_px": area_px,
        "hull_perimeter_px": perimeter_px,
    }


def compute_geometry(mask: np.ndarray):
    try:
        return _geometry_contours(mask)
    except Exception:
        return _geometry_numpy(mask)


def _angle_diff(a: float, b: float) -> float:
    diff = abs(a - b) % 180.0
    return diff if diff <= 90.0 else 180.0 - diff


def _relative_error(pred: float, gt: float) -> float:
    if abs(gt) < 1e-9:
        return 0.0 if abs(pred) < 1e-9 else float("inf")
    return abs(pred - gt) / abs(gt) * 100.0


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    model = _load_model()
    patches = _load_test_patches()
    print(f"Loaded model from {MODEL_PATH}")
    print(f"Test patches: {len(patches)}")

    rows = []
    for patch_id in patches:
        img_path = IMAGES_DIR / f"{patch_id}.png"
        mask_path = MASKS_DIR / f"{patch_id}.png"
        if not img_path.exists() or not mask_path.exists():
            print(f"  SKIP {patch_id} (missing file)")
            continue

        image = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        gt_mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image is None or gt_mask is None:
            print(f"  SKIP {patch_id} (read error)")
            continue

        gt_binary = (gt_mask > 0).astype(np.uint8)
        pred_mask = _predict_mask(model, image)

        gt_geom = compute_geometry(gt_binary)
        pred_geom = compute_geometry(pred_mask)

        if gt_geom is None or pred_geom is None:
            area_rel_err = float("inf") if (gt_geom is None and pred_geom is not None or gt_geom is not None and pred_geom is None) else 0.0
            centroid_dist_m = float("inf") if (gt_geom is None) != (pred_geom is None) else 0.0
            perim_rel_err = area_rel_err
            orient_err = float("inf") if (gt_geom is None) != (pred_geom is None) else 0.0
            compact_err = area_rel_err
        else:
            area_rel_err = _relative_error(pred_geom["area_px"] * PIXEL_AREA_KM2, gt_geom["area_px"] * PIXEL_AREA_KM2)
            dx = (pred_geom["centroid_x"] - gt_geom["centroid_x"]) * PIXEL_SCALE_M
            dy = (pred_geom["centroid_y"] - gt_geom["centroid_y"]) * PIXEL_SCALE_M
            centroid_dist_m = float(np.sqrt(dx ** 2 + dy ** 2))
            perim_rel_err = _relative_error(pred_geom["perimeter_px"] * PIXEL_SCALE_M, gt_geom["perimeter_px"] * PIXEL_SCALE_M)
            orient_err = _angle_diff(pred_geom["angle_deg"], gt_geom["angle_deg"])
            compact_err = abs(pred_geom["compactness"] - gt_geom["compactness"])

        rows.append({
            "patch": patch_id,
            "gt_area_km2": round(gt_geom["area_px"] * PIXEL_AREA_KM2, 6) if gt_geom else None,
            "pred_area_km2": round(pred_geom["area_px"] * PIXEL_AREA_KM2, 6) if pred_geom else None,
            "area_rel_err_pct": round(area_rel_err, 2) if np.isfinite(area_rel_err) else None,
            "centroid_dist_m": round(centroid_dist_m, 2) if np.isfinite(centroid_dist_m) else None,
            "perim_rel_err_pct": round(perim_rel_err, 2) if np.isfinite(perim_rel_err) else None,
            "orient_err_deg": round(orient_err, 2) if np.isfinite(orient_err) else None,
            "compactness_error": round(compact_err, 4) if np.isfinite(compact_err) else None,
        })
        print(f"  {patch_id}: area_err={area_rel_err:.1f}% cent={centroid_dist_m:.1f}m orient={orient_err:.1f}deg")

    df = pd.DataFrame(rows)
    csv_path = REPORTS_DIR / "slick_geometry_results.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"\nWrote {csv_path}")

    finite_mask = {
        "area_rel_err_pct": df["area_rel_err_pct"].replace([np.inf, -np.inf], np.nan).dropna(),
        "centroid_dist_m": df["centroid_dist_m"].replace([np.inf, -np.inf], np.nan).dropna(),
        "perim_rel_err_pct": df["perim_rel_err_pct"].replace([np.inf, -np.inf], np.nan).dropna(),
        "orient_err_deg": df["orient_err_deg"].replace([np.inf, -np.inf], np.nan).dropna(),
        "compactness_error": df["compactness_error"].replace([np.inf, -np.inf], np.nan).dropna(),
    }

    report_lines = [
        "# Slick Geometry Validation Report\n",
        f"Model: `{MODEL_PATH.name}`",
        f"Threshold: {THRESHOLD}",
        f"Pixel scale: {PIXEL_SCALE_M} m/pixel",
        f"Test patches evaluated: {len(df)}\n",
        "## Per-Patch Results\n",
        df.to_string(index=False),
        "\n## Aggregate Metrics\n",
    ]

    agg_rows = []
    for metric, series in finite_mask.items():
        if len(series) == 0:
            continue
        agg_rows.append({
            "metric": metric,
            "MAE": round(float(series.mean()), 4),
            "median": round(float(series.median()), 4),
            "mean_rel_err_pct": round(float(series.mean()), 4),
            "std": round(float(series.std()), 4),
            "n_valid": int(len(series)),
        })

    agg_df = pd.DataFrame(agg_rows)
    if len(agg_df) > 0:
        report_lines.append(agg_df.to_string(index=False))
    else:
        report_lines.append("No valid finite metrics to aggregate.")

    report_lines.append("")
    md_path = REPORTS_DIR / "slick_geometry_report.md"
    md_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
