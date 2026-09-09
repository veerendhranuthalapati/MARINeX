"""
Instance and Object-Level Evaluation for Connected Oil Slicks.
Measures discrete slick detection rates, false alarm slicks, matched region IoU, and centroid distances.
"""

import numpy as np
import cv2
from typing import Dict, List, Any, Tuple

def extract_slick_instances(mask: np.ndarray, min_area: int = 10) -> List[Dict[str, Any]]:
    """Extracts connected component regions from binary mask."""
    binary = (mask > 0).astype(np.uint8)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

    instances = []
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area:
            component_mask = (labels == i)
            instances.append({
                "id": i,
                "area": area,
                "centroid": (float(centroids[i][0]), float(centroids[i][1])), # (x, y)
                "mask": component_mask,
                "bbox": (
                    stats[i, cv2.CC_STAT_LEFT],
                    stats[i, cv2.CC_STAT_TOP],
                    stats[i, cv2.CC_STAT_WIDTH],
                    stats[i, cv2.CC_STAT_HEIGHT]
                )
            })
    return instances

def evaluate_object_detection(
    gt_mask: np.ndarray,
    pred_mask: np.ndarray,
    iou_threshold: float = 0.3,
    min_area: int = 10
) -> Dict[str, Any]:
    """
    Evaluates instance-level oil spill detection by matching predicted slicks with ground truth slicks.
    Supports both single 2D image masks (H, W) and 3D image batches (N, H, W).
    """
    if gt_mask.ndim == 3:
        # Aggregate across batch
        all_tp = 0
        all_fp = 0
        all_fn = 0
        all_num_gt = 0
        all_num_pred = 0
        all_ious = []
        all_dists = []

        for i in range(gt_mask.shape[0]):
            res = evaluate_object_detection(gt_mask[i], pred_mask[i], iou_threshold, min_area)
            all_tp += res["true_positives"]
            all_fp += res["false_positives"]
            all_fn += res["false_negatives"]
            all_num_gt += res["num_gt_slicks"]
            all_num_pred += res["num_pred_slicks"]
            if res["num_gt_slicks"] > 0 and res["true_positives"] > 0:
                all_ious.append(res["mean_matched_iou"])
                all_dists.append(res["mean_centroid_dist"])

        prec = all_tp / max(all_tp + all_fp, 1e-7)
        rec = all_tp / max(all_tp + all_fn, 1e-7)
        f1 = (2.0 * prec * rec) / max(prec + rec, 1e-7)

        return {
            "num_gt_slicks": all_num_gt,
            "num_pred_slicks": all_num_pred,
            "true_positives": all_tp,
            "false_positives": all_fp,
            "false_negatives": all_fn,
            "object_precision": float(prec),
            "object_recall": float(rec),
            "object_f1": float(f1),
            "mean_matched_iou": float(np.mean(all_ious)) if all_ious else 0.0,
            "mean_centroid_dist": float(np.mean(all_dists)) if all_dists else 0.0
        }

    gt_instances = extract_slick_instances(gt_mask, min_area=min_area)
    pred_instances = extract_slick_instances(pred_mask, min_area=min_area)

    num_gt = len(gt_instances)
    num_pred = len(pred_instances)

    if num_gt == 0 and num_pred == 0:
        return {
            "num_gt_slicks": 0,
            "num_pred_slicks": 0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "object_precision": 1.0,
            "object_recall": 1.0,
            "object_f1": 1.0,
            "mean_matched_iou": 1.0,
            "mean_centroid_dist": 0.0
        }

    matched_gt = set()
    matched_pred = set()
    matched_ious = []
    centroid_dists = []

    # Greedy IoU matching
    for p_idx, p_inst in enumerate(pred_instances):
        best_iou = 0.0
        best_gt_idx = -1
        for g_idx, g_inst in enumerate(gt_instances):
            if g_idx in matched_gt:
                continue
            intersection = np.sum(p_inst["mask"] & g_inst["mask"])
            union = np.sum(p_inst["mask"] | g_inst["mask"])
            iou = intersection / max(union, 1)
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = g_idx

        if best_iou >= iou_threshold and best_gt_idx != -1:
            matched_gt.add(best_gt_idx)
            matched_pred.add(p_idx)
            matched_ious.append(best_iou)

            # Centroid distance
            g_cent = gt_instances[best_gt_idx]["centroid"]
            p_cent = p_inst["centroid"]
            dist = np.sqrt((g_cent[0] - p_cent[0])**2 + (g_cent[1] - p_cent[1])**2)
            centroid_dists.append(dist)

    tp = len(matched_gt)
    fp = num_pred - len(matched_pred)
    fn = num_gt - len(matched_gt)

    prec = tp / max(tp + fp, 1e-7)
    rec = tp / max(tp + fn, 1e-7)
    f1 = (2.0 * prec * rec) / max(prec + rec, 1e-7)

    return {
        "num_gt_slicks": num_gt,
        "num_pred_slicks": num_pred,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "object_precision": float(prec),
        "object_recall": float(rec),
        "object_f1": float(f1),
        "mean_matched_iou": float(np.mean(matched_ious)) if matched_ious else 0.0,
        "mean_centroid_dist": float(np.mean(centroid_dists)) if centroid_dists else 0.0
    }
