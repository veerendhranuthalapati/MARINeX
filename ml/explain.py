"""
Explainability CLI (Phase 25/26).

Usage:
    python ml/explain.py --checkpoint models/checkpoints/segformer_primary_best.pt \
                         --model segformer \
                         --image data/datasets/sentinel1_primary/images/patch_0101.png \
                         --mask data/datasets/sentinel1_primary/masks/patch_0101.png \
                         --methods occlusion,gradcam,attention \
                         --out reports/explainability/patch_0101_panel.png

Generates a panel: original SAR | predicted mask | confidence | attribution maps
| ground truth | error map, plus reports/explainability/<id>.json metadata.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch
import cv2
from PIL import Image

from ml.models.registry import build_model
from ml.data.transforms import SARPreprocessor
from ml.evaluation.metrics import compute_pixel_metrics
from ml.explainability.methods import compute_explainability


def make_panel(cells, row_labels, out_path, cell_size=280):
    n_rows = len(cells)
    n_cols = max(len(r) for r in cells)
    h, w = cell_size, cell_size
    canvas = np.full((n_rows * h, n_cols * w, 3), 22, dtype=np.uint8)
    for r, row in enumerate(cells):
        for c, cell in enumerate(row):
            if cell is None:
                continue
            if cell.dtype != np.uint8:
                cell = (np.clip(cell, 0, 1) * 255).astype(np.uint8)
            if cell.ndim == 2:
                cell = np.stack([cell] * 3, axis=-1)
            cell = cv2.resize(cell, (w, h))
            canvas[r * h:(r + 1) * h, c * w:(c + 1) * w] = cell
    for r, label in enumerate(row_labels):
        cv2.putText(canvas, label, (8, r * h + 22), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 255, 255), 1, cv2.LINE_AA)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), canvas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--model", default="segformer")
    ap.add_argument("--image", required=True)
    ap.add_argument("--mask", default=None)
    ap.add_argument("--methods", default="occlusion,gradcam,attention")
    ap.add_argument("--threshold", type=float, default=0.4)
    ap.add_argument("--out", default="reports/explainability/panel.png")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(args.model, in_channels=3, num_classes=1)
    ckpt = torch.load(args.checkpoint, map_location="cpu")
    model.load_state_dict(ckpt["state_dict"])
    model.to(device).eval()

    raw = np.array(Image.open(args.image))
    prep = SARPreprocessor(strategy="percentile")
    norm = prep(raw)
    image_id = Path(args.image).stem

    tensor = torch.from_numpy(np.ascontiguousarray(norm)).permute(2, 0, 1).unsqueeze(0).float().to(device)
    with torch.no_grad():
        prob = torch.sigmoid(model(tensor)).squeeze().cpu().numpy()
    pred = (prob >= args.threshold).astype(np.uint8)

    row_labels = [f"Original {image_id}", "Attributions", "Metrics"]
    rows = []

    # Row 0: original, prediction, confidence
    rows.append([raw / 255.0, (pred * 255).astype(np.uint8), (prob * 255).astype(np.uint8), None])

    # Row 1: each attribution map
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    exp = compute_explainability(model, device, norm, methods=methods)
    attr_cells = []
    for r in exp:
        if r.attribution.size == 0:
            attr_cells.append(np.full((1, 1, 3), 40, dtype=np.uint8))
        else:
            attr_cells.append(r.attribution)
    rows.append(attr_cells)

    # Row 2: ground truth and error map if mask provided
    if args.mask:
        gt = (np.array(Image.open(args.mask)) == 1).astype(np.uint8)
        err = np.zeros_like(gt)
        err[(gt == 1) & (pred == 0)] = 2   # false negative
        err[(gt == 0) & (pred == 1)] = 1   # false positive
        rows.append([gt, err, None, None])
    else:
        rows.append([None])

    row_labels = row_labels[:len(rows)]
    make_panel(rows, row_labels, args.out)

    metrics = {}
    if args.mask:
        gt = (np.array(Image.open(args.mask)) == 1).astype(np.uint8)
        metrics = compute_pixel_metrics(gt, pred, prob)

    meta = {
        "image": args.image,
        "id": image_id,
        "checkpoint": args.checkpoint,
        "model": args.model,
        "threshold": args.threshold,
        "panel": str(args.out),
        "explanations": [e.to_dict() for e in exp],
        "single_image_metrics": metrics,
    }
    meta_path = Path(args.out).with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(json.dumps(meta, indent=2, default=float))
    for e in exp:
        if e.notes:
            print(f"[warn] {e.method}: {e.notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())