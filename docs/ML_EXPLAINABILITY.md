# MARINeX Model Explainability

Attribution for the deep segmentation models — required for defensible forensic
evidence in the SIH26143 problem scope.

## Methods

Implemented in `ml/explainability/methods.py`:

| Method | Type | Notes |
|---|---|---|
| `occlusion` | Perturbation-based | Sliding 32×32 neutral-gray patches; attribute = drop in predicted oil presence **within the occluded cell** (global-mean drops diluted to ~0 on sparse slicks, so the loss is measured cell-locally) |
| `gradcam` | Gradient-based | Channel-weighted average of gradients on the fused decoder conv |
| `attention` | Feature-attribution proxy | Mean channel activation of the SegFormer `linear_fuse` decoder conv projected to input resolution. A documented proxy, NOT raw transformer attention (which is spatially downsampled with no single canonical layout) |

Each returns an `ExplanationResult` (array + method + model name + notes).

## CLI usage

```bash
.venv\Scripts\python ml/explain.py \
  --checkpoint models/checkpoints/segformer_primary_best.pt \
  --model segformer \
  --image data/datasets/sentinel1_primary/images/patch_0101.png \
  --mask  data/datasets/sentinel1_primary/masks/patch_0101.png \
  --methods occlusion,gradcam,attention \
  --out reports/explainability/patch_0101_panel.png
```

Outputs:
- `reports/explainability/patch_0101_panel.png` — original SAR | prediction |
  confidence | attribution maps | ground truth | error map
- `reports/explainability/patch_0101_panel.json` — attribution ranges + single-image
  metrics

## Verified output (patch_0101, SegFormer, REAL)

| Method | Attribution range (normalized) |
|---|---|
| `occlusion` | 0.0 → 1.0 |
| `gradcam` | 0.0 → 0.982 |
| `attention` | 0.0 → 0.995 |

Single-image metrics on that patch: IoU 0.966, Dice 0.983, Precision 0.972,
Recall 0.994, PR-AUC 0.999.

> Occlusion uses `fill_value=0.5`, not black — a `0.0` fill reads as a dark slick to
> SegFormer and yields empty attribution (measured empirically).

## Integration

Backend detection services currently run the classical baseline / mock detector
(`backend/app/services/detection/adapters.py`). Wiring the PyTorch checkpoints into
the backend service layer and surfacing attribution maps on the dashboard is the
next integration step (not yet implemented).