# Model Card: MARINeX U-Net Oil Spill Detector (`marinex-unet-v1.0.0`)

## Model Summary
- **Model Name**: `marinex-unet-v1.0.0`
- **Artifact**: `models/best_model/marinex_unet_v1.pt` (frozen by `scripts/freeze_final_model.py`)
- **Architecture**: U-Net baseline (convolutional encoder–decoder with skip connections)
- **Framework**: PyTorch 2.14.0 (CPU inference)
- **Primary Task**: Semantic segmentation of mineral oil spills and discrimination against natural look-alikes (low-wind zones, biogenic slicks, internal solitary waves).
- **Target Sensor**: Copernicus Sentinel-1 C-Band Synthetic Aperture Radar (SAR, IW Mode, GRD).
- **Polarizations Used**: Dual-Polarization `VV` + `VH` + Derived Polarimetric Difference `(VV - VH)`.

## Selection Rationale (all frozen on validation)
- Chosen over U-Net++ and SegFormer by validation IoU; robust under contrast + radiometric −3 dB perturbation; lowest calibration ECE among leaders; the cheapest latency on CPU.
- Frozen operating threshold: **0.70** (`reports/calibration.json` best_iou_threshold).
- Temperature scaling (log-space): **T = 0.226** brings ECE 17.35% → **0.46%** (Brier 0.0330 → 0.0025).

## Frozen Test (single protected pass, threshold 0.70)
| metric | value |
| --- | --- |
| IoU | 0.8857 |
| Dice | 0.9394 |
| Precision | 0.9080 |
| Recall | 0.9731 |
| FPR | 0.0041 |
| ECE (raw at threshold) | 0.1754 |
| Object-level F1 | 0.7901 |
| Latency (CPU) | ~163 ms / 256² patch |

## Generalization & Robustness
- **Cross-dataset (Singapore Strait, no merging)**: IoU 0.8487, Dice 0.9181.
- **Multi-seed stability (val)**: seed 42 IoU 0.9459, 123 → 0.9358, 999 → 0.9265.
- **Controlled perturbation**: robust to contrast (×0.4 → IoU 0.8795) and −3 dB radiometric shift (0.8940); degrades under heavy speckle (L=2.0 → 0.4424), 20 m resolution loss (0.5786) and +3 dB shift (0.3030) — flagged as operating-condition limits, not covered claims.

## Data & Split Integrity
- **Parent Scene Grouping**: partitions allocated strictly by parent Sentinel-1 acquisition ID; patches from the same scene never span splits.
- Train 80 / Val 20 / Test 20 / External 40 patches. Leakage audit: **PASSED** (zero overlap, scene-boundary verified).

## Intended Use & Downstream Consumers
1. MARINeX Slick Morphometric Characterizer (area km², perimeter, centroid, compactness).
2. Lagrangian Particle Drift Hindcast/Forecast Engine (95% origin uncertainty hull).
3. Spatial-temporal AIS Vessel Attribution Engine (4-factor evidence scoring, no guilt claims).
4. Explainability service (occlusion + Grad-CAM heatmaps with provenance).

## Known Limitations
- Trained on synthetic SAR patches (120 primary); not validated on real incidents.
- CPU-budgeted epochs; small corpus — absolute numbers are on this dataset only.
- Speckle/radiometric-stress ranges above are the reliable operating envelope.
- Attribution/explanation sanity: randomization test rated **WEAK** (perturbation test PASS) — explanations are indicative, not causal.