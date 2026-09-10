# MARINeX Final Data Report (SIH26143)

Final-phase data report. Every figure below was produced by a real run of the
referenced script and is reproducible with the given command; nothing is
fabricated.

## 1. Data policy

- **All imagery is synthetic.** SAR-like patches are procedurally generated
  (`ml/data/generate_sar_dataset.py`): dark-polynomial slick morphologies, sea
  clutter Rayleigh noise, wind streaks, instrument speckle. Manifests label the
  generator explicitly; the primary manifest notes "no real Sentinel-1 imagery".
- Reports and presentations must state *synthetic benchmark* and never claim
  real-world satellite-truth generalization.

## 2. Catalog (real, committed)

| dataset_id | samples | status | local_bytes | checksum(sha256:16) |
|---|---|---|---|---|
| sentinel1-oilspill-primary-v1 | 120 | local | 21,612,134 | f25423bf21f0d193 |
| sentinel1-oilspill-external-v1 | 40 | local | 7,202,678 | 279f505e35a0caa3 |

- Format: 256×256 PNG; channel order `[VV, VH, VV_minus_VH]`; masks 8-bit
  grayscale with values `0` background / `1` mineral oil / `2` look-alike
  (low-wind zones / biogenic surfactants). Ships and land labels are never
  generated.
- Registry: `data/manifests/<id>.json`; `scripts/data_status.py` reproduces the
  catalog.

## 3. Dataset statistics (Phase 3 measurement)

`scripts/final_data_audit.py` → `reports/final_dataset_statistics.csv`.
Primary dataset, 120 samples, all 3-channel, all 256×256:

| split | samples | oil-masked | lookalike-masked | no-oil | empty-mask |
|---|---|---|---|---|---|
| train | 80 | 40 | 40 | 40 | 16 |
| val | 20 | 10 | 10 | 10 | 4 |
| test | 20 | 10 | 10 | 10 | 4 |
| **total** | **120** | 60 | 60 | 60 | 24 |

Total foreground coverage: 293,799 oil-class pixels and 657,661 look-alike
pixels across the corpus.

## 4. Split policy (leakage-controlled)

- `data/splits/split_group_aware_v1.json`: train 80 / val 20 / test 20
  (12 parent scenes → 8/2/2), computed on **parent scenes**, never slots, so a
  scene cannot leak across folds; oil vs look-alike vs clean-sea balance kept
  per fold.
- Test fold = SCENE_02 (patch_0011–0020) + SCENE_11 (patch_0101–0110), used
  exactly once after the freeze.

## 5. Leakage audit (Phase 3, PASS)

`scripts/final_data_audit.py` (sample-id scan, parent-scene containment,
sha256, 32×32 near-duplicate correlation at 0.98 threshold):

- `leakage_detected = false`; three-level check **PASS**.
- Parent-scene containment violations: **0**; cross-split near-duplicates
  (train/val, train/test, val/test): **0**; duplicate feature groups: **0**;
  corrupted files: **0**.
- Artifacts: `reports/final_leakage_audit.json` / `.md`.

## 6. Secondary datasets

- **External** (`sentinel1-oilspill-external-v1`, Singapore/Malacca Straits,
  40 samples): generalization probe only — inference on the frozen production
  checkpoint (IoU 0.8487 / Dice 0.9181); never used for training or tuning.
- **AIS sample archive**: `data/samples/sample_ais_trajectories.csv`
  (20 reports, 5 vessels) → partitioned parquet (`data/processed/ais/partitions/`,
  gitignored bulk) consumed by `ml/ais` DuckDB engine.
- **Demo environmental snapshot**: sample wind/current forcing used by the drift
  service.

## 7. Honest limitations

1. Small corpus (120) ⇒ wide error bands; treat all numbers as benchmark
   indicators, not operational performance.
2. Synthetic-only: no real Sentinel-1, no real ground truth of real spills.
3. AIS archive is broadcast-only and sample-sized; dark vessels are absent by
   construction.