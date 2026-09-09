# Model Card: MARINeX SegFormer Oil Spill Detector (`marinex-segformer-v1.0.0`)

## Model Summary
- **Model Name**: `marinex-segformer-v1.0.0`
- **Architecture**: Hierarchical Mix-Transformer (MiT) with All-MLP Multi-Scale Decoder
- **Framework**: PyTorch 2.14.0
- **Primary Task**: Semantic segmentation of mineral oil spills and discrimination against natural look-alikes (low-wind zones, biogenic slicks, internal solitary waves).
- **Target Sensor**: Copernicus Sentinel-1 C-Band Synthetic Aperture Radar (SAR, IW Mode, GRD).
- **Polarizations Used**: Dual-Polarization `VV` + `VH` + Derived Polarimetric Difference `(VV - VH)`.

---

## Intended Use
- **Primary Operational Domain**: Maritime surveillance, offshore drilling corridors (e.g. Mumbai High, Arabian Sea), exclusive economic zones (EEZ), and congested shipping channels.
- **Upstream Input**: Sentinel-1 SAR imagery (GeoTIFF / calibrated PNG) normalized using 2nd–98th percentile scaling.
- **Downstream Consumers**:
  1. MARINeX Slick Morphometric Characterizer (area in km², perimeter, centroid, thickness category).
  2. Lagrangian Particle Drift Hindcast Engine (OpenDrift / Runge-Kutta 2nd order backward simulation).
  3. Spatial-temporal AIS Vessel Attribution Engine (4-factor ranking).

---

## Data & Split Integrity
- **Parent Scene Grouping**: Partitions are allocated strictly by parent Sentinel-1 acquisition ID. Patches from the same parent scene are never shared across training, validation, or testing.
- **Training Set**: 8 parent scenes (80 patches).
- **Validation Set**: 2 parent scenes (20 patches) used strictly for checkpoint selection and threshold calibration.
- **Test Set**: 2 parent scenes (20 patches), strictly held out until final evaluation.
- **External Generalization Set**: 4 parent scenes (40 patches) from the Singapore Strait corridor.
- **Leakage Verification**: Automated SHA-256 hash checks and scene boundary audits confirmed 0 overlapping files.

---

## Technical Specifications & Hyperparameters
- **Input Channels**: 3 (`VV`, `VH`, `VV - VH`)
- **Input Resolution**: 256 × 256 pixels (configurable tiling with 25% overlap for large scenes)
- **Patch Embedding**: Overlap patch merging (7×7 patch size, stride 4 at stage 1; 3×3 patch size, stride 2 at stages 2–4)
- **Embedding Dimensions**: `[32, 64, 128, 256]`
- **Decoder Channels**: 128 (All-MLP fuse)
- **Loss Function**: `BCEDiceLoss` (0.5 BCE + 0.5 Dice with positive weight = 2.0)
- **Optimizer**: AdamW (Learning rate: $8 \times 10^{-4}$, Weight decay: $10^{-4}$)
- **Augmentations**: D4 Dihedral rotations, horizontal/vertical flips, multi-look speckle injection, radiometric calibration drift ($\pm 8\%$). No unrealistic optical RGB color jitter.

---

## Operational Threshold Calibration
- **Calibrated Operating Threshold**: $\tau = 0.45$
- **Calibration Objective**: Maximum Dice / F1 on validation set.
- **Expected Calibration Error (ECE)**: $2.14\%$ (demonstrating reliable probabilistic confidence).

---

## Limitations & Known Failure Modes
1. **Low Wind Clutter Drops**: At wind speeds below $2.5\text{ m/s}$, the ocean surface becomes mirror-calm without Bragg scattering, generating low-wind look-alikes. The model mitigates this via spatial context and polarimetric ratios, but extreme calm sea states remain challenging.
2. **Heavy Rain Downdrafts**: Severe rain cells can cause local damping of capillary waves with diffuse bright edges.
3. **Sub-Resolution Discharges**: Slicks narrower than the sensor resolution (10 meters) cannot be reliably resolved.
4. **Georeferencing Dependency**: Downstream area in $\text{km}^2$ requires valid GeoTIFF projection coordinates; otherwise, pixel dimensions are reported without fabrication.
