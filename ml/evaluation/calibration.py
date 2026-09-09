"""
Threshold Calibration and Probability Uncertainty Calibration Module.
Sweeps validation probabilities to determine optimal operating thresholds and computes ECE.
"""

import numpy as np
from typing import Dict, List, Any, Tuple
from ml.evaluation.metrics import compute_pixel_metrics

def calibrate_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    thresholds: List[float] = None
) -> Dict[str, Any]:
    """
    Sweeps thresholds on the validation set to find the optimal decision boundary.
    Never tunes threshold on the test set.
    """
    if thresholds is None:
        thresholds = [round(t, 2) for t in np.arange(0.10, 0.95, 0.05)]

    results = []
    best_dice = -1.0
    best_dice_th = 0.50

    best_iou = -1.0
    best_iou_th = 0.50

    high_recall_th = 0.50
    min_fpr_th = 0.50

    for th in thresholds:
        pred_bin = (y_prob >= th).astype(np.uint8)
        m = compute_pixel_metrics(y_true, pred_bin, y_prob)
        entry = {
            "threshold": th,
            "iou": m["iou"],
            "dice": m["dice"],
            "precision": m["precision"],
            "recall": m["recall"],
            "fpr": m["false_positive_rate"]
        }
        results.append(entry)

        if m["dice"] > best_dice:
            best_dice = m["dice"]
            best_dice_th = th

        if m["iou"] > best_iou:
            best_iou = m["iou"]
            best_iou_th = th

        if m["recall"] >= 0.85:
            high_recall_th = th

        if m["false_positive_rate"] <= 0.02 and m["precision"] > 0.5:
            min_fpr_th = th

    calibration_summary = {
        "best_dice_threshold": best_dice_th,
        "max_dice": best_dice,
        "best_iou_threshold": best_iou_th,
        "max_iou": best_iou,
        "recommended_operating_threshold": best_dice_th,
        "high_recall_threshold": high_recall_th,
        "low_fpr_threshold": min_fpr_th,
        "sweep_curve": results
    }
    return calibration_summary

def compute_expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    num_bins: int = 10
) -> Dict[str, Any]:
    """
    Computes Expected Calibration Error (ECE) and reliability diagram bins.
    """
    y_true_flat = y_true.flatten().astype(np.float32)
    y_prob_flat = y_prob.flatten().astype(np.float32)

    bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
    ece = 0.0
    bins_data = []

    for i in range(num_bins):
        bin_low = bin_boundaries[i]
        bin_high = bin_boundaries[i + 1]

        in_bin = (y_prob_flat >= bin_low) & (y_prob_flat < bin_high)
        bin_size = np.sum(in_bin)

        if bin_size > 0:
            bin_acc = np.mean(y_true_flat[in_bin])
            bin_conf = np.mean(y_prob_flat[in_bin])
            weight = bin_size / len(y_prob_flat)
            ece += weight * np.abs(bin_acc - bin_conf)

            bins_data.append({
                "bin_range": (bin_low, bin_high),
                "accuracy": float(bin_acc),
                "confidence": float(bin_conf),
                "count": int(bin_size)
            })

    return {
        "expected_calibration_error": float(ece),
        "ece_percentage": float(ece * 100.0),
        "reliability_bins": bins_data
    }
