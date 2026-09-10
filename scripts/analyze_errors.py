"""
Error Taxonomy + Failure Gallery for the MARINeX final model (SIH26143).
=======================================================================

After all decisions are FROZEN, evaluates the final model on the held-out test
set and classifies each failure mode into an insulating error taxonomy so the
report never just prints an IoU number — it explains *why* and *where*.

Usage:
    .venv\\Scripts\\python scripts/analyze_errors.py \
        --model models/best_model/marinex_unet_v1.pt \
        --threshold 0.70
"""

import argparse
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
from ml.evaluation.object_eval import extract_slick_instances, evaluate_object_detection

PREP = SARPreprocessor(strategy="percentile")


def load_final_model(path, device):
    meta = {}
    model = build_model("unet", in_channels=3, num_classes=1)
    try:
        meta = model.load_weights(path, map_location=device)
    except Exception:
        pass
    model.to(device).eval()
    return model, meta


def inference(model, img_arr, device):
    norm = PREP(img_arr)
    t = torch.from_numpy(np.ascontiguousarray(norm)).permute(2, 0, 1).unsqueeze(0).to(device)
    with torch.no_grad():
        p = torch.sigmoid(model(t)).squeeze().cpu().numpy()
    h, w = img_arr.shape[:2]
    if p.shape != (h, w):
        import cv2
        p = cv2.resize(p, (w, h), interpolation=cv2.INTER_LINEAR)
    return p


def classify_failure(sample_metrics):
    """Rules (interpretable + auditable) that label the dominant failure mode."""
    iou = sample_metrics["iou"]
    fp = sample_metrics["fp_pixels"]
    fn = sample_metrics["fn_pixels"]
    gt_pix = max(sample_metrics["gt_pixels"], 1)
    oil_frac = gt_pix / (256 * 256)

    # Tiny / microscopic slick test
    if oil_frac < 0.002 and fn >= 0.5 * gt_pix:
        return "Tiny/Weak Slick (below detection floor)"
    # Low contrast / under-detection (miss-dominated)
    if fn > fp and fn > 0:
        if iou < 0.5:
            return "False Negative - Large dark anomaly missed"
        return "Partial Coverage - Boundary leakage"
    # False alarm dominated
    if fp >= fn and fp > 0:
        return "False Positive - Look-alike / clutter triggered"
    if gt_pix > 0 and iou >= 0.8:
        return "High-Fidelity Hit"
    return "Neutral / Minor error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/best_model/marinex_unet_v1.pt")
    ap.add_argument("--threshold", type=float, default=0.70)
    ap.add_argument("--split", default="data/splits/split_group_aware_v1.json")
    ap.add_argument("--data", default="data/datasets/sentinel1_primary")
    ap.add_argument("--out", default="reports/error_taxonomy.csv")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, meta = load_final_model(args.model, device)
    th = float(meta.get("optimal_threshold", args.threshold))

    inv = scan_dataset(args.data)
    smap = {s["sample_id"]: s for s in inv["samples"]}
    with open(args.split) as f:
        split = json.load(f)
    test_samples = [smap[sid] for sid in split["splits"]["test"]]

    rows = []
    agg_gt = []; agg_pred = []
    for s in test_samples:
        img = np.array(Image.open(s["image_path"]))
        gt = (np.array(Image.open(s["mask_path"])) == 1).astype(np.uint8)
        prob = inference(model, img, device)
        pred = (prob >= th).astype(np.uint8)

        px = compute_pixel_metrics(gt, pred, prob)
        gt_inst = extract_slick_instances(gt, min_area=10)
        pred_inst = extract_slick_instances(pred, min_area=10)
        n_gt = len(gt_inst); n_pred = len(pred_inst)

        fp = px["fp_pixels"]; fn = px["fn_pixels"]
        # Proportion of FP pixels that sit in a look-alike ground-truth region
        look = np.array(Image.open(s["mask_path"]))
        fp_in_lookalike = int(np.sum((pred == 1) & (look == 2))) if look.max() >= 2 else 0
        fp_total = max(fp, 1)

        failure = classify_failure({"iou": px["iou"], "fp_pixels": fp, "fn_pixels": fn,
                                    "gt_pixels": px["tp_pixels"] + fn,
                                    "pred_pixels": px["tp_pixels"] + fp})

        rows.append({
            "sample_id": s["sample_id"],
            "region": s.get("region", ""),
            "has_oil": s.get("has_oil", ""),
            "has_lookalike": s.get("has_lookalike", ""),
            "iou": round(px["iou"], 4),
            "dice": round(px["dice"], 4),
            "precision": round(px["precision"], 4),
            "recall": round(px["recall"], 4),
            "tp_pixels": px["tp_pixels"],
            "fp_pixels": fp,
            "fn_pixels": fn,
            "fp_px_in_lookalike_region": fp_in_lookalike,
            "fp_share_lookalike": round(fp_in_lookalike / fp_total, 4),
            "n_gt_slicks": n_gt,
            "n_pred_slicks": n_pred,
            "error_category": failure,
        })
        agg_gt.append(gt); agg_pred.append(pred)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Summary breakdown
    from collections import Counter
    counts = Counter(r["error_category"] for r in rows)
    print("= Error taxonomy breakdown =")
    for cat, n in counts.most_common():
        print(f"  {cat}: {n}")
    px_all = compute_pixel_metrics(np.stack(agg_gt), np.stack(agg_pred))
    obj = evaluate_object_detection(np.stack(agg_gt), np.stack(agg_pred))
    print(f"Aggregate test IoU={px_all['iou']:.4f} Dice={px_all['dice']:.4f} "
          f"Object-F1={obj['object_f1']:.4f} Prec={px_all['precision']:.4f} Rec={px_all['recall']:.4f}")
    print(f"Taxonomy written to {args.out}")


if __name__ == "__main__":
    raise SystemExit(main())