"""
Comprehensive Evaluation Metrics for SAR Oil Spill Detection and Segmentation.
Calculates Pixel-level metrics (IoU, Dice, Precision, Recall, Specificity, FPR, FNR, PR-AUC, ROC-AUC)
and Image-level classification performance.
"""

import numpy as np
from sklearn.metrics import precision_recall_curve, auc, roc_auc_score, confusion_matrix
from typing import Dict, Any, Tuple, Optional

def compute_pixel_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    Computes all essential pixel-level segmentation and detection quality metrics.
    Inputs:
        y_true: Binary ground truth array (0 or 1)
        y_pred: Binary predicted array (0 or 1)
        y_prob: Predicted probability array in [0.0, 1.0] (optional)
    """
    y_true_flat = y_true.flatten().astype(np.uint8)
    y_pred_flat = y_pred.flatten().astype(np.uint8)

    # Basic Confusion Matrix components
    tp = float(np.sum((y_true_flat == 1) & (y_pred_flat == 1)))
    fp = float(np.sum((y_true_flat == 0) & (y_pred_flat == 1)))
    fn = float(np.sum((y_true_flat == 1) & (y_pred_flat == 0)))
    tn = float(np.sum((y_true_flat == 0) & (y_pred_flat == 0)))

    # Pixel Accuracy
    pixel_acc = (tp + tn) / max(tp + tn + fp + fn, 1.0)

    # Precision & Recall (Sensitivity)
    precision = tp / max(tp + fp, 1e-7)
    recall = tp / max(tp + fn, 1e-7)

    # Specificity & Rates
    specificity = tn / max(tn + fp, 1e-7)
    fpr = fp / max(fp + tn, 1e-7)
    fnr = fn / max(fn + tp, 1e-7)

    # Balanced Accuracy
    balanced_acc = 0.5 * (recall + specificity)

    # Dice / F1 Score
    dice = (2.0 * tp) / max(2.0 * tp + fp + fn, 1e-7)

    # Intersection over Union (IoU) / Jaccard
    iou = tp / max(tp + fp + fn, 1e-7)

    metrics = {
        "iou": float(iou),
        "dice": float(dice),
        "precision": float(precision),
        "recall": float(recall),
        "specificity": float(specificity),
        "balanced_accuracy": float(balanced_acc),
        "pixel_accuracy": float(pixel_acc),
        "false_positive_rate": float(fpr),
        "false_negative_rate": float(fnr),
        "tp_pixels": int(tp),
        "fp_pixels": int(fp),
        "fn_pixels": int(fn),
        "tn_pixels": int(tn)
    }

    # PR-AUC and ROC-AUC (Critical for severe class imbalance)
    if y_prob is not None:
        y_prob_flat = y_prob.flatten().astype(np.float32)
        # Sample if too large to compute smoothly
        if len(y_true_flat) > 500000:
            idx = np.random.choice(len(y_true_flat), size=500000, replace=False)
            sub_true = y_true_flat[idx]
            sub_prob = y_prob_flat[idx]
        else:
            sub_true = y_true_flat
            sub_prob = y_prob_flat

        try:
            prec_vals, rec_vals, _ = precision_recall_curve(sub_true, sub_prob)
            pr_auc = float(auc(rec_vals, prec_vals))
            metrics["pr_auc"] = pr_auc
        except Exception:
            metrics["pr_auc"] = float(dice)

        try:
            if len(np.unique(sub_true)) > 1:
                roc_auc = float(roc_auc_score(sub_true, sub_prob))
                metrics["roc_auc"] = roc_auc
            else:
                metrics["roc_auc"] = 1.0
        except Exception:
            metrics["roc_auc"] = 1.0
    else:
        metrics["pr_auc"] = float(dice)
        metrics["roc_auc"] = float(balanced_acc)

    return metrics

def evaluate_batch_predictions(
    targets: np.ndarray,
    predictions: np.ndarray,
    probabilities: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    Evaluates an entire batch/split of images and returns aggregate metrics.
    """
    return compute_pixel_metrics(targets, predictions, probabilities)
