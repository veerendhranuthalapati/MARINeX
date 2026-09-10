# MARINeX Final Experiment Protocol (SIH26143 — Team DOOM CODERS)

> Frozen protocol for the research-grade validation phase. Every number published
> in `reports/*` must be reproducible by executing the command in the corresponding
> "Reproduce" line below. Nothing is retrofitted after the final test pass.

## 1. Data

| Property | Value |
|---|---|
| Primary dataset | `data/datasets/sentinel1_primary` (``sentinel1-oilspill-primary-v1``) |
| External dataset | `data/datasets/sentinel1_external` (``sentinel1-oilspill-external-v1``) |
| Provenance | Procedural SAR generator `ml/data/generate_sar_dataset.py` — **synthetic**, NOT operational Sentinel-1 |
| Resolution | 256×256 px, 10 m nominal ground sample distance |
| Channels | VV, VH, VV−VH (derived) |
| Classes | background (0), mineral oil (1), look-alike (2); ships/land never generated |
| Samples | 120 primary (oil/look-alike/clean balance 40/40/16 → per split 10/10/4 on val+test), 40 external |

**Honesty clause.** The corpus is procedurally generated. All reported metrics are
real measurements, but they measure the model on synthetic SAR-like imagery and
**must not** be presented as operational Sentinel-1 performance. Cross-dataset
results (Dataset B) likewise come from the same generator (different geography)
and must be labelled as such.

## 2. Splitting & Leakage Control

- Split strategy: **group-aware by parent scene** (`data/splits/split_group_aware_v1.json`).
- Train / validation / final-test: **80 / 20 / 20** images across **8 / 2 / 2** parent scenes.
- Test scenes are untouched by every development decision below (architecture,
  channels, loss, augmentation, preprocessing, threshold, temperature, hard-negative
  mining, two-stage classifier).
- Leakage checks enforced **before** any metric is published:
  - identical sample-id overlap across splits,
  - parent-scene overlap across splits,
  - SHA-256 fingerprint collision (duplicate / near-duplicate images) across splits,
  - spatial adjacency of patch tiles within the same acquisition is confined to one split.
- Reproduce: `& ".venv\Scripts\python.exe" scripts/final_data_audit.py` →
  `reports/final_leakage_audit.{json,md}`.

## 3. Preprocessing & Augmentation

- Preprocessing: **percentile normalization** (`SARPreprocessor(strategy="percentile")`),
  per-image 2nd/98th percentile estimate, channel layout `VV, VH, VV−VH` stacked last-axis.
  Selected on validation among percentile / robust / min_max / z_score
  (`reports/ablation_results.csv` → "Preprocessing").
- Augmentation (training only): SAR-appropriate `SARAugmentor` — flips, rotations,
  scale jitter, Gaussian noise, speckle, contrast shift. No geometric transforms that
  change the physical SAR semantics (no arbitrary warps). Augmented training proven
  on validation over "No Augmentation" (`reports/ablation_results.csv` → "Augmentation").
- Validation and test use the identical preprocessing; **no augmentation** at inference.

## 4. Models Benchmarked

| Model | Registry key | Notes |
|---|---|---|
| Classical baseline | `classical` | Otsu threshold baseline (no learning) |
| U-Net baseline | `unet` | UNetBaseline, 3 ch, base 32 |
| U-Net++ | `unet_plus_plus` | same data protocol |
| SegFormer | `segformer` | lightweight transformer (validation only, CPU budget) |
| Two-stage | SegFormer stage-A + `oil/look-alike` classifier (stage-B) | Phase 11 comparison |

DeepLabV3+ was **not** included: the CPU-only budget and the existing four models
already cover the required classical + U-Net + advanced-model comparison; adding a
fifth architecture without a demonstrated validation advantage is not scientifically
justified here.

## 5. Metric Definitions (test/lookup, all deterministic)

- Pixel: **IoU, Dice, Precision, Recall, Specificity, FPR, FNR, PR-AUC, ROC-AUC**
  (`ml/evaluation/metrics.py`, sklearn).
- Object-level: connected components (8-connectivity, min area 10 px), greedy IoU
  matching at IoU ≥ 0.3 → `obj_precision / obj_recall / obj_f1`
  (`ml/evaluation/object_eval.py`).
- Calibration: **ECE** (10 bins), **Brier** score, reliability curve,
  temperature scaling (`ml/evaluation/calibration.py`).
- Latency: warm-up excluded, 8 forward passes, 256×256, CPU (real measured time).

## 6. Selection Rules (validation-only)

1. Architecture → max **validation IoU** at the validation-threshold sweep.
2. Operating threshold → `calibrate_threshold` **on validation** (sweep 0.10–0.90 step 0.05).
3. Calibration temperature → **fitted on validation** by NLL minimization (L-BFGS).
4. Hard-negative retrained model competes against base model **on validation IoU only**.
5. Two-stage competes on the **protected test set**, reported as an alternative, never
   silently replacing the production model.

**The final test set is used only after all development decisions are frozen.**
The freeze is recorded in `models/production/metadata.json` (`git_commit`, `frozen_at`,
`threshold`, `calibration.temperature`, `frozen_test_metrics`).

## 7. Frozen Configuration (production)

- Model: `marinex-unet-v1.0.0` (UNetBaseline, in_channels=3, num_classes=1).
- Checkpoint: `models/best_model/marinex_unet_v1.pt` (= `models/campaign/arch_unet_best.pt` + metadata).
- Threshold: **0.70**; Temperature: **0.2262**; Preprocessing: percentile.
- Reproduce freeze: `& ".venv\Scripts\python.exe" scripts/freeze_final_model.py`.

## 8. Final Test Protocol (single guarded pass)

- Evaluate the frozen configuration on the 20-image held-out test split,
  computing pixel, object, calibration and latency metrics **once**.
- Reproduce: `& ".venv\Scripts\python.exe" scripts/run_ml_campaign.py` (resumes on
  existing `.done` flags; forces the same network) then `scripts/build_final_report.py`.
- Guard: `scripts/run_ml_campaign.py` asserts `leak["leakage_detected"] == False` and
  raises `STOP: leakage detected` otherwise.

## 9. Multi-Seed Stability

- Final architecture trained from 3 seeds {42, 123, 999} on the **same** train split,
  validation-level IoU/Dice reported for **all** seeds with mean ± std.
- Reproduce: `reports/multi_seed.csv` via the campaign.

## 10. Robustness, Generalization, Look-alike, Geometry, Errors

| Experiment | Method | Report |
|---|---|---|
| Robustness | 7 controlled perturbations on test (contrast 0.6/0.4×, speckle L=2, res. 20 m, radiometric ±3 dB) | `reports/robustness_results.csv` |
| Cross-dataset | Frozen model, Dataset B (Singapore Strait), no merging/tuning | `reports/cross_dataset_results.csv` |
| Scene-level | Per parent-scene (SCENE_02 / SCENE_11) IoU | `reports/scene_level_results.csv` |
| Slick size | IoU by slick area quartile | `reports/slick_size_results.csv` |
| Look-alike | OIL / LOOKALIKE / CLEAN benchmark incl. rejection rate | `reports/lookalike_results.csv` |
| Slick geometry | Area MAE/rel-err, centroid dist, perimeter err on matched slicks | `reports/slick_geometry_results.csv` |
| Error taxonomy | FP/FN classes, tiny-slick, low-contrast, fragmentation, boundary | `reports/error_taxonomy.csv` |
| Channel / loss / augmentation / preprocessing | Validation-only ablations | `reports/ablation_results.csv` |

## 11. Explainability (Phase 17–18)

- Method: Grad-CAM (final conv) + occlusion sensitivity sweep (the UNet's native
  attribution technique; no assumption that it is universally valid).
- Sanity: (a) randomized-weights perturbation — attributes should degrade; result
  reported honestly (WEAK), (b) input-perturbation occlusion — confidence should drop; PASS.
- Reproduce: `& ".venv\Scripts\python.exe" scripts/explain_sanity.py --sample patch_0101` →
  `reports/explainability/sanity.json`.
- Limitation is documented, not hidden.

## 12. Random Seeds & Reproducibility

- Campaign seed: 42 (default), multi-seed {42,123,999}; preprocessor deterministic;
  temperature fit deterministic on fixed probs.
- Version pins: Python 3.13, torch 2.14.0 (CPU build), numpy/sklearn/opencv per
  `ml/requirements.txt`. Environment snapshot recorded in the final report.

## 13. Known Limitations (must be repeated in every downstream artifact)

1. Synthetic-only imagery; no operational Sentinel-1 claims.
2. CPU-bound training budgets (epoch counts documented in `scripts/run_ml_campaign.py`).
3. Small corpus (120 patches) → wide error bands.
4. WEAK explainability randomization result → attribution maps not over-interpreted.
5. AIS = archived broadcast CSV (MarineCadastre-style); vessels with AIS off are
   outside the correlation envelope.
6. Drift engine is a deterministic mock over analytic current/wind fields (not yet
   reanalysis-fed); ERA5/CMEMS adapters are stubbed.