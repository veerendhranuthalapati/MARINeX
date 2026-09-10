# MARINeX Oil Spill Model Card

| | |
|---|---|
| **Model ID** | `marinex-unet-v1.0.0` |
| **Git commit** | `f764d88` (frozen campaign); re-frozen `8f5a18d`/`6294b78` (metadata/docs only, weights unchanged) |
| **Frozen at** | 2026-09-10 |
| **Team** | DOOM CODERS (SIH China 120462) |
| **Problem statement** | SIH26143 (oil spill detection + AIS vessel correlation) |

## 1. Intended use

- Pixel-level segmentation of mineral-oil dark patches in single-polarization-composite SAR-like imagery (VV/VH/VV−VH) on 256×256 tiles.
- Downstream input to slick morphometry (area, centroid, perimeter), Lagrangian drift hindcasting, and AIS candidate correlation within the MARINeX investigation pipeline.
- Analytics / investigation-priority ranking support — **never** guilt adjudication.

## 2. Not intended use

- Operational Sentinel-1 production deployment without re-evaluation on real acquisitions.
- Legal proof of responsibility; the model only labels imagery.
- Ship or land class segmentation (never generated).
- Classification of look-alike vs oil as a standalone task (see the two-stage experiment).

## 3. Dataset

| Property | Value |
|---|---|
| Name | `sentinel1-oilspill-primary-v1` (120 samples) |
| Source | **Procedural SAR generator** (`ml/data/generate_sar_dataset.py`); no real Sentinel-1 pixels |
| Geography | Arabian Sea (Mumbai High, Goa, Gujarat Gulf, Gulf of Oman) |
| Acquisitions | simulated 2026-03-01..06, 12 parent scenes |
| Classes | background(0), mineral oil(1), look-alike(2); ships/land never generated |
| Channels / size | VV, VH, VV−VH; 256×256 px; 10 m nominal |

External cross-dataset: `sentinel1-oilspill-external-v1` (40 samples, Singapore/Malacca Straits), same generator — used **only** for generalization probing, never for training/tuning.

## 4. Split (leakage-controlled)

- Group-aware by parent scene: **train 80 / val 20 / test 20**, scenes 8/2/2.
- Leakage audit (sample id, parent scene, sha256, near-dup correlation, scene containment): **PASS — zero leakage** (`reports/final_leakage_audit.md`).
- **The final test split was used only once, after all decisions were frozen.**

## 5. Preprocessing

Percentile normalization (`SARPreprocessor(strategy="percentile")`). Validity note:
the validation ablation (`reports/ablation_results.csv` → "Preprocessing") shows
`robust` slightly higher on val IoU (0.9613 vs 0.9459) than the frozen `percentile`.
The frozen configuration was locked with `percentile`; swapping now would invalidate
the entire calibrated artifact chain (threshold 0.70, temperature, downstream
look-alike/scene/geometry reports that were measured with percentile). Retaining the
frozen percentile config and disclosing the validated alternative is the
reproducibility-consistent choice under the frozen-protocol rule.

## 6. Architecture

- UNetBaseline (encoder-decoder with skip connections), `in_channels=3`, `num_classes=1`, base features 32.
- Final conv → logits → sigmoid; operating threshold from validation sweep.
- Framework: PyTorch 2.14 (CPU build during campaign).

## 7. Loss & training

- Loss: **BCE + Dice** (selected on validation among bce/dice/bce+dice/focal/tversky/focal-tversky).
- Augmentation: SAR-appropriate `SARAugmentor` (validated `aug_on` vs `aug_off`).
- Optimizer AdamW (lr 8e-4, wd 1e-4); campaign epochs documented in `scripts/run_ml_campaign.py`.
- Seeds: campaign 42; multi-seed {42,123,999}.

## 8. Operating threshold & calibration

- Threshold: **0.70** (validation sweep; `reports/calibration.json`).
- Temperature scaling **T = 0.2262** (validation NLL, L-BFGS).
- ECE: **0.1735 → 0.0046**; Brier **0.0330 → 0.0025** (measured, `reports/calibration.json`).

## 9. Frozen test metrics (single protected pass)

| Metric | Value |
|---|---|
| IoU | 0.8857 |
| Dice | 0.9394 |
| Precision | 0.9080 |
| Recall | 0.9731 |
| PR-AUC | 0.9939 |
| FPR | 0.0041 |
| FNR | 0.0269 |
| ECE (raw) | 0.1754 |
| Object-F1 | 0.7901 |
| Latency (CPU, 256²) | ~124–130 ms |

## 10. Generalization

- Scene-level: SCENE_02 0.9034 / SCENE_11 0.8743 (mean 0.8889; `reports/scene_level_results.csv`).
- Cross-dataset (external Singapore Strait): IoU 0.8487, Dice 0.9181 (frozen, no tuning).
- Robustness on test (`reports/robustness_results.csv`): clean 0.8857; contrast 0.6× 0.8654; 0.4× 0.8795;
  speckle L=2.0 0.4432; resolution 20 m 0.5786; −3 dB 0.8940; +3 dB 0.3030 → known fragility to
  radiometric boosts and heavy speckle.
- Multi-scale (inference only): native 256 optimal; 224–384 degrade (IoU ≈ 0.66–0.68, FPR ↑) —
  do not feed downsampled scenes without recalibration.

## 11. Look-alike discrimination

- OIL 0.9583 IoU / 0.9738 conf where segmented; LOOKALIKE 0.8145 / 0.6116; CLEAN rejected 0.0.
- Clean false-detection rate 0.0000, look-alike rejection 0.30 at threshold 0.70
  (`reports/lookalike_results.csv`).

## 12. Explainability

- Grad-CAM (final conv) + occlusion sensitivity; panels under `reports/explainability/`.
- Sanity: randomization test **WEAK** (attribution energy 7396 real vs ~48-53k randomized —
  do not over-interpret heatmaps); input-occlusion perturbation **PASS** (conf drop 0.055).
  Limitation documented in `reports/explainability/sanity.json` and
  `docs/ML_EXPLAINABILITY_VALIDATION.md`.

## 13. Limitations & failure modes

1. Synthetic imagery only — no operational Sentinel-1 claims.
2. CPU-bound training budget (8 epochs/U-Net) — gains from longer training not measured.
3. Small corpus (120) → wide error bands.
4. Fragile to radiometric +3 dB and speckle (robustness table).
5. +3 dB shift recovers only 0.303 IoU → automatic gain control mismatch is a real failure mode.
6. WEAK explainability randomization → Grad-CAM must not be presented as causal proof.
7. AIS correlation depends on broadcast AIS only (dark vessels outside envelope).

## 14. Versioning & provenance

- Checkpoint: `models/best_model/marinex_unet_v1.pt` (torch save with `metadata`,
  `frozen_threshold`, `frozen_test`, `calibration`).
- Frozen config JSON: `models/production/metadata.json`.
- Reproduce: `scripts/run_ml_campaign.py` → `scripts/freeze_final_model.py` → `scripts/build_final_report.py`.
- All reports regenerable via the commands listed in `docs/FINAL_EXPERIMENT_PROTOCOL.md`.