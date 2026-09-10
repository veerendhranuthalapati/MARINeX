# MARINeX Scientific ML Experiment Protocol (SIH26143)

This document is the *auditable contract* behind every number in
`reports/FINAL_ML_REPORT.md`. It exists so that results can be reproduced,
questioned, and re-checked — not just believed.

Date of freeze: 2026-09-10. Driver: `scripts/run_ml_campaign.py`.

## 1. Scientific commandments (violating any invalidates the campaign)

1. **No test-set tuning.** Model selection, channel/loss/augmentation choices,
   hard-negative mining, threshold selection and temperature calibration all
   happen on the **validation** split. The protected **test** split is touched
   exactly once, after every decision is frozen, and is never re-consulted.
2. **No fabricated numbers.** Every metric in the CSVs is produced by executing
   code against the actual dataset on this machine. Historical rows that were
   broken (e.g. Two-Stage `0.0000`) are marked BROKEN and re-generated.
3. **One preprocessing contract.** All models train and infer with
   `SARPreprocessor(strategy="percentile")` (2-98 percentile clip). `/255.0` is
   a recognized bug pattern and is banned at inference; the hard-negative miner
   and two-stage pipeline use the same preprocessor.
4. **Leakage-free by construction and by test.** The group-aware split
   (`data/splits/split_group_aware_v1.json`) separates parent scenes. The
   `detect_data_leakage` audit (exact-ID, parent-scene, and SHA-256 hash
   collisions) is re-run at campaign start and must PASS before training.
5. **Cross-dataset means no merging.** Evaluating on Dataset B uses a model
   trained only on Dataset A. No fine-tuning, no pseudo-labels, no shared
   preprocessing statistics.

## 2. Data

- All data is **synthetic** (procedural SAR, `ml/data/generate_sar_dataset.py`).
  No real Sentinel-1 imagery was used.
- Dataset A (`sentinel1_primary`, Arabian Sea), Dataset B
  (`sentinel1_external`, Singapore Strait). Each patch is 256×256 px,
  VV/VH dual-pol with optional DIFF channel.
- Split: train/val/test = 80/20/20 (group-aware by `parent_scene_id`).

## 3. Decision funnel (all on validation)

| # | Decision | Search space | Criterion |
|---|---|---|---|
| 1 | Architecture | `unet`, `unet_plus_plus`, `segformer` | val IoU at best validation threshold |
| 2 | Input channels | `VV`, `VH`, `VV_VH`, `VV_VH_DIFF` | val IoU (on chosen arch) |
| 3 | Loss | `bce`, `dice`, `bce_dice`, `focal`, `tversky`, `focal_tversky` | val IoU |
| 4 | Augmentation | none vs physical SAR (`SARAugmentor`) | val IoU |
| 5 | Preprocessing | percentile / robust / min_max / z_score | val IoU |
| 6 | Hard negatives | none vs train+val mining, 3x oversample | val IoU (mining never touches test) |
| 7 | Two-stage | stage-A + stage-B crop classifier | val IoU vs single-stage |
| 8 | Threshold | 0.10-0.95 sweep on val | max val IoU (`calibrate_threshold`) |
| 9 | Calibration | temperature scaling `T` on val (LBFGS, NLL) | reduced ECE/Brier on val |

## 4. Training protocol (frozen)

- Optimizer: AdamW, lr=8e-4, weight-decay=1e-4. Loss: `bce_dice` default.
- Epoch budget (CPU-bounded; UNet/UNet++ ~45-55 s/epoch, SegFormer ~6 s/epoch):
  architecture 8/8/12 epochs, ablations 5, HN retrain 8, multi-seed 6.
- Early stopping patience 4 on validation Dice. Best-checkpoint-by-val-Dice.
- Seed 42 for selection/ablations; 42/123/999 for multi-seed stability.

## 5. Frozen evaluation (single protected test pass)

- Classical (Otsu), UNet, UNet++, final single-stage, final+HN, final two-stage
  each evaluated once on the full test split.
- Metrics: IoU, Dice, Precision, Recall, PR-AUC, FPR, FNR, ECE, Brier
  (pixel-level); object precision/recall/F1 + matched-slick stats
  (instance-level, IoU≥0.3, min-area 10); real latency (warmup + timed passes).
- Robustness: contrast ×2, speckle, resolution, radiometric shift ±3 dB.
- Cross-dataset: Dataset-A-trained final model evaluated on Dataset B.

## 6. After the test pass (no re-tuning allowed)

Only analysis may follow the test pass: error taxonomy
(`scripts/analyze_errors.py`), explainability sanity checks
(`scripts/explain_sanity.py`), report generation, documentation.

## 7. Reproduction commands

```bash
.SCRIPTPATH = ".venv\\Scripts\\python.exe"
& $SCRIPTPATH scripts/run_ml_campaign.py            # full campaign
& $SCRIPTPATH scripts/run_ml_campaign.py --quick    # 3-epoch smoke test
& $SCRIPTPATH scripts/analyze_errors.py --model models/best_model/marinex_segformer_v1.pt
& $SCRIPTPATH scripts/explain_sanity.py --sample patch_0101
& $SCRIPTPATH scripts/data_status.py
```

## 8. Known limitations

- Small synthetic dataset (120 patches); external validity is limited.
- CPU-only training bounds the epoch budget; multi-seed std is an indicator,
  not a full uncertainty analysis.
- Two-stage latency includes per-candidate crop inference; reported as measured.
- ECE/Brier are pixel-distribution statistics; reliability-diagram inspection
  should accompany interpretation (`reports/calibration.json`).