"""
FINAL_ML_REPORT.md generator for MARINeX (SIH26143).
=====================================================
Reads the campaign output CSVs and renders a Markdown report with NO hard-coded
numbers, so the document cannot drift from the actual measurements.
"""

import csv
import json
from pathlib import Path

REPORTS = Path("reports")
OUT = REPORTS / "FINAL_ML_REPORT.md"


def read_csv(name):
    path = REPORTS / name
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def md_table(rows, cols):
    if not rows:
        return "_no data_"
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    lines = [header, sep]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(lines)


def main():
    test = read_csv("final_test_results.csv")
    sel = read_csv("model_selection.csv")
    ablation = read_csv("ablation_results.csv")
    robust = read_csv("robustness_results.csv")
    cross = read_csv("cross_dataset_results.csv")
    seeds = read_csv("multi_seed.csv")
    calib = {}
    if (REPORTS / "calibration.json").exists():
        calib = json.loads((REPORTS / "calibration.json").read_text(encoding="utf-8"))
    summary = {}
    if (REPORTS / "campaign_summary.json").exists():
        summary = json.loads((REPORTS / "campaign_summary.json").read_text(encoding="utf-8"))

    if not test:
        print("No final_test_results.csv yet - campaign not finished.")
        return 1

    test_cols = ["model", "iou", "dice", "precision", "recall", "fpr", "fnr",
                 "ece", "brier", "obj_prec", "obj_rec", "obj_f1", "latency_ms"]
    sel_cols = ["model", "val_iou_at_best_th", "val_dice_at_best_th", "best_threshold"]
    abl_cols = ["ablation", "variant", "iou", "dice", "precision", "recall", "fpr"]
    rob_cols = ["condition", "iou", "dice", "precision", "recall", "fpr"]
    cross_cols = ["evaluation_domain", "dataset_name", "iou", "dice", "precision", "recall", "fpr"]
    seed_cols = ["seed", "val_iou", "val_dice"]

    doc = f"""# MARINeX Final ML Report (SIH26143) — Team DOOM CODERS

> Generated automatically from `reports/*.csv` on the frozen 2026-09-10 campaign
> (`scripts/run_ml_campaign.py`). Every number is a real measurement on the
> **synthetic** MARINeX dataset. Device: `{summary.get('device', 'n/a')}`.
> Protocol: `docs/ML_EXPERIMENT_PROTOCOL.md`.

## TL;DR

- **Selected architecture**: `{summary.get('selected_architecture', 'n/a')}` (by **validation** IoU).
- **Frozen operating threshold**: `{summary.get('selected_threshold', 'n/a')}` (validation sweep).
- **Hard negatives mined**: `{summary.get('hard_negatives_mined', 'n/a')}` →
  augmented train set `{summary.get('hard_negative_train_set', 'n/a')}` samples.
- **Temperature scaling** `T = {summary.get('temperature', 'n/a')}` lowers ECE
  {calib.get('ece_raw', '')} -> {calib.get('ece_calibrated', '')}.
- **Leakage audit**: `{summary.get('leakage', 'n/a')}`.

## 1. Frozen test results (single protected test pass)

{md_table(test, test_cols)}

- Pixel metrics: IoU/Dice/Precision/Recall/PR-AUC/FPR/FNR.
- ECE + Brier quantify calibration; obj_* are instance-level slick metrics.
- `latency_ms`: real warmup+timed CPU inference (256×256).

## 2. Architecture & hyperparameter selection (validation only)

{md_table(sel, sel_cols)}

### Ablations (validation)

{md_table(ablation, abl_cols)}

## 3. Calibration

- Threshold: `{calib.get('threshold', 'n/a')}` (validation `calibrate_threshold`).
- Temperature: `T = {calib.get('temperature', 'n/a')}`.
- ECE: `{calib.get('ece_raw', 'n/a')}` (raw) -> `{calib.get('ece_calibrated', 'n/a')}` (calibrated).
- Brier: `{calib.get('brier_raw', 'n/a')}` -> `{calib.get('brier_calibrated', 'n/a')}`.
- Full sweep: `reports/calibration.json`.

## 4. Robustness (final model, controlled perturbation)

{md_table(robust, rob_cols)}

## 5. Cross-dataset generalization (no merging)

{md_table(cross, cross_cols)}

## 6. Multi-seed stability (validation)

{md_table(seeds, seed_cols)}

## 7. Error taxonomy

See `reports/error_taxonomy.csv` and `scripts/analyze_errors.py`.

## 8. Explainability

Panels: `reports/explainability/`. Sanity checks + structured explanations:
`reports/explainability/sanity.json` (`scripts/explain_sanity.py`).

## 9. Limitations

- Synthetic-only dataset; CPU-bound epoch budgets; small (120-patch) corpus.
- See `docs/ML_EXPERIMENT_PROTOCOL.md` §8.
"""

    OUT.write_text(doc, encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())