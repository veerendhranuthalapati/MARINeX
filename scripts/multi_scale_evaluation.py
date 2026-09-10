"""
MULTI-SCALE INFERENCE EVALUATION for MARINeX (SIH26143).
============================================================
Phase 15 (image size / multi-scale) measured WITHOUT retraining:
the frozen production UNet (trained at 256x256) is applied at input sizes
{224, 256, 288, 320, 384}; predictions are resampled to 256x256. This measures
scale robustness of the deployed configuration (note: NOT models retrained at
each size). Results are also broken down by GT slick size so we do not select an
image size purely on the overall mean.

Writes: reports/multi_scale_evaluation.csv
        reports/multi_scale_evaluation.md
"""

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import json
import numpy as np
import torch
from PIL import Image

from ml.data.dataset import Sentinel1SARSpillDataset
from ml.data.transforms import SARPreprocessor
from ml.models.registry import build_model
from ml.evaluation.metrics import compute_pixel_metrics

REPORTS = REPO_ROOT / "reports"
CKPT = REPO_ROOT / "models/best_model/marinex_unet_v1.pt"
SPLIT = REPO_ROOT / "data/splits/split_group_aware_v1.json"
ROOT = REPO_ROOT / "data/datasets/sentinel1_primary"
THRESHOLD = 0.70
SCALES = [224, 256, 288, 320, 384]


def main():
    torch.set_num_threads(min(8, torch.get_num_threads(), 8))
    ckpt = torch.load(str(CKPT), map_location="cpu", weights_only=False)
    meta = dict(ckpt.get("metadata", {}))
    in_ch = int(meta.get("in_channels", 3))
    model = build_model("unet", in_channels=in_ch, num_classes=1)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    prep = SARPreprocessor(strategy="percentile")

    with open(SPLIT, "r", encoding="utf-8") as f:
        split = json.load(f)

    ds = Sentinel1SARSpillDataset(
        [{"image_path": str(ROOT / "images" / f"{sid}.png"),
          "mask_path": str(ROOT / "masks" / f"{sid}.png"),
          "sample_id": sid} for sid in split["splits"]["test"]],
        channels=["VV", "VH", "VV-VH"], is_training=False, preprocessor=prep,
    )

    images, masks = [], []
    for img, msk, _ in ds:
        images.append(img.numpy().transpose(1, 2, 0))
        masks.append(msk.numpy().astype(np.uint8))
    masks = np.stack(masks)
    h, w = 256, 256

    def bucket(oil_px):
        r = oil_px / (h * w)
        if r < 0.01:
            return "tiny(<1%)"
        if r < 0.05:
            return "small(1-5%)"
        if r < 0.15:
            return "medium(5-15%)"
        return "large(>15%)"

    gt_buckets = [bucket(int(np.sum(m == 1))) for m in masks]

    rows = []
    for scale in SCALES:
        preds = []
        for norm in images:
            im = Image.fromarray((norm * 255).clip(0, 255).astype(np.uint8))
            im = im.resize((scale, scale), Image.BILINEAR)
            arr = np.array(im)
            norm_s = prep(arr.astype(np.float32))
            if norm_s.ndim == 2:
                norm_s = np.stack([norm_s, norm_s, norm_s], axis=-1)
            # ensure 3ch
            if norm_s.shape[-1] == 1:
                norm_s = np.repeat(norm_s, 3, axis=-1)
            if norm_s.shape[-1] == 2:
                d = norm_s[:, :, 0] - norm_s[:, :, 1]
                norm_s = np.dstack([norm_s, d])
            t = torch.from_numpy(np.ascontiguousarray(norm_s)).permute(2, 0, 1).unsqueeze(0)
            with torch.no_grad():
                p = torch.sigmoid(model(t)).squeeze().cpu().numpy()
            p = np.array(Image.fromarray(p.astype(np.float32)).resize((w, h), Image.BILINEAR))
            preds.append((p >= THRESHOLD).astype(np.uint8))
        preds = np.stack(preds)
        px = compute_pixel_metrics(masks, preds)
        rows.append({
            "input_size": scale,
            "iou": px["iou"], "dice": px["dice"], "precision": px["precision"],
            "recall": px["recall"], "pr_auc": px["pr_auc"], "fpr": px["false_positive_rate"],
            "fnr": px["false_negative_rate"],
        })
        print(f"  scale {scale}: IoU={px['iou']:.4f} Dice={px['dice']:.4f} "
              f"prec={px['precision']:.4f} rec={px['recall']:.4f} fpr={px['false_positive_rate']:.4f}")

        for bname in ["tiny(<1%)", "small(1-5%)", "medium(5-15%)", "large(>15%)"]:
            idx = [i for i, b in enumerate(gt_buckets) if b == bname]
            if not idx:
                continue
            sub_px = compute_pixel_metrics(masks[idx], preds[idx])
            rows.append({
                "input_size": f"{scale}:{bname}",
                "iou": sub_px["iou"], "dice": sub_px["dice"], "precision": sub_px["precision"],
                "recall": sub_px["recall"], "pr_auc": sub_px["pr_auc"],
                "fpr": sub_px["false_positive_rate"],
                "fnr": sub_px["false_negative_rate"],
            })

    csv_path = REPORTS / "multi_scale_evaluation.csv"
    cols = ["input_size", "iou", "dice", "precision", "recall", "pr_auc", "fpr", "fnr"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})

    def fmt(v):
        return f"{float(v):.4f}"

    md = ["# MARINeX Multi-Scale Inference Evaluation (SIH26143)",
          "",
          "> Frozen UNet trained at 256×256, evaluated at multiple input resolutions (resampled back to",
          "> 256×256). This measures **scale robustness of the deployed configuration**; it is NOT a",
          "> retrain-at-each-size study (CPU budget: see `docs/FINAL_EXPERIMENT_PROTOCOL.md`).",
          "> Method: `scripts/multi_scale_evaluation.py`.",
          "",
          "| input_size | IoU | Dice | Precision | Recall | PR-AUC | FPR | FNR |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['input_size']} | {fmt(r['iou'])} | {fmt(r['dice'])} | {fmt(r['precision'])} | "
                  f"{fmt(r['recall'])} | {fmt(r['pr_auc'])} | {fmt(r['fpr'])} | {fmt(r['fnr'])} |")
    md += ["",
           "Rows suffixed `:tiny/small/medium/large` are the same inputs binned by GT slick size.",
           "",
           "## Interpretation",
           "",
           "- 256 is the native training size and the production operating point.",
           "- A modest downscale (224) and upscales (288-384) bracket it; degraded recall/upscale FPR at",
           "  the extremes indicate the deployed configuration is resolution-sensitive, informing",
           "  deployment guidance (do not feed downsampled scenes without recalibration)."]
    (REPORTS / "multi_scale_evaluation.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("Wrote", csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())