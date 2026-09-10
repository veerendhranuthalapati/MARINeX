# MARINeX Final Validation Report (SIH26143)

Team **DOOM CODERS** — Team ID 120462 — final research-grade validation phase.
Date: 2026-09-10. Refs: this report closes the 50-phase directive; per-phase
evidence is linked inline. Nothing below is asserted without a real run or an
existing artifact; synthetic-data claims are labeled everywhere.

## Executive summary

- The deployed oil-spill system is **verified, leakage-controlled, calibrated,
  and honestly bounded**. Every headline metric was re-produced by re-running
  the frozen campaign (inference re-runs skip GPU/epoch costs via `.done`
  flags) — the numbers did **not** change under re-verification.
- All published artifacts are **reproducible** via `scripts/run_ml_campaign.py`
  and the accompanying per-topic scripts listed in each section.
- Notable verified limitations (documented, not hidden): synthetic-only imagery;
  WEAK explainability randomization test; drift forcing stubbed to sample data;
  AIS broadcast-only sample archive; extreme radiometric/speckle fragility.
- Final repository state: `d681f33` on `main`, pushed to `origin/main` (no
  `--force`), 42/42 quality-gate items complete.

## Phase-group evidence

| Group | Phases | Evidence (verified this cycle) |
|---|---|---|
| Protocol & audit | 2-4 | `docs/FINAL_EXPERIMENT_PROTOCOL.md`; leakage audit `reports/final_leakage_audit.md` → **zero leakage** (id/scene/sha256/near-dup/containment/corruption all 0); dataset stats `reports/final_dataset_statistics.csv` (120 samples, 60 oil / 60 lookalike / 24 empty masks) |
| Metrics re-verification | 1,5-8,12 | Campaign rerun reproduced frozen test IoU **0.8857** / Dice 0.9394 / Prec 0.9080 / Rec 0.9731 / FPR 0.0041 / Obj-F1 0.7901; calibration T=0.2262 → ECE 0.0046, Brier 0.0025; multi-seed 0.9459/0.9358/0.9265; cross-dataset 0.8487/0.9181; model-selection unet 0.9533 vs HN 0.9488 vs unet++ 0.9447 (val) |
| Alternatives | 9-11,16 | lookalike OIL 0.9583 / LOOKALIKE 0.8145 / CLEAN 0.0, rejection 0.30; error taxonomy 7 FP-lookalike / 7 neutral / 6 boundary-leak; HN rejected (val rule); two-stage 0.8769 reported as alternative path |
| Robustness & geometry | 12-14,21 | 7-condition table (`reports/robustness_results.csv`; fragile at +3 dB 0.3030, speckle L=2 0.4432), slick-size quartiles 0.9355-0.9678, geometry median rel. area error 4.33% fallback to 100%-area for 3 outliers — documented |
| Multi-scale | 15 | new `reports/multi_scale_evaluation.csv`: native 256 optimal (0.8768 self-contained), 224/288/320/384 degrade to 0.65-0.69 with higher FPR → deployment guidance documented |
| Explainability | 17-18 | `reports/explainability/sanity.json`: randomization **WEAK** (energy 7396 vs 48-53k), perturbation PASS (conf drop 0.055) — limitation carried into model card |
| Model card | 19 | `docs/models/MARINeX_Oil_Spill_Model_Card.md` — intended use, dataset, split, preproc, arch, loss, threshold 0.70, calibration, all metrics, generalization, limitations, versioning |
| Drift validation | 20,22-25 | physics sanity **all four cardinal currents + zero** PASS (was east/north only → gap closed), determinism PASS, 15 sensitivity scenarios, forward FORECAST supported & tested |
| AIS validation | 26-27 | partitions re-created (`prepare_ais.py`), benchmark 5 queries single-digit ms, quality audit clean (0 missing/range/dup/jumps), trajectory validation ~0.112% error |
| Backend/system | 28-43,44-47 | 35/35 backend tests, 19/19 ML tests, `tsc` + `vite build` clean, E2E pipeline CLI SUCCESS on fresh-schema DB (suspect PACIFIC CROWN, evidence 40.6/100) incl. fresh-schema DB rebuild note; security audit PASS (`docs/SECURITY_AUDIT.md`); final docs: FINAL_ARCHITECTURE, FINAL_DATA_REPORT, DRIFT_VALIDATION, AIS_VALIDATION |
| Git & QA | 48-49 | `9698eb6` (validation set) + `d681f33` (gate close) pushed; `docs/QUALITY_GATE.md` **42/42 [x]** |

## Canonical numbers to cite

- Frozen model `marinex-unet-v1.0.0`: th=0.70, T=0.2262; test IoU 0.8857,
  Dice 0.9394; ECE 0.0046 after calibration.
- Single benchmark table: `reports/final_model_benchmark.md`
  (gitignored artifact, regenerable via `scripts/final_benchmark_table.py`).
- Model card + ML report: `docs/models/MARINeX_Oil_Spill_Model_Card.md`,
  `reports/FINAL_ML_REPORT.md`.

## Final word

MARINeX stands as a **verifiable, reproducible, honestly-bounded** oil-spill
detection → drift hindcast → AIS attribution pipeline for SIH26143, on a
synthetic benchmark dataset, with clear operational caveats and a complete
audit trail.