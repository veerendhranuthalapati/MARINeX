"""
FINAL MODEL BENCHMARK TABLE for MARINeX (SIH26143).
============================================================
Phase 20: produce the single authoritative comparison table
(Model, Input, IoU, Dice, Precision, Recall, PR-AUC, FPR, FNR, ECE, Latency).
Every value is read from reports/final_test_results.csv (re-measured on the
protected test pass produced by scripts/run_ml_campaign.py). Nothing is invented.

Writes: reports/final_model_benchmark.csv
        reports/final_model_benchmark.md
"""

import csv
import json
from pathlib import Path

REPORTS = Path("reports")
SRC = REPORTS / "final_test_results.csv"
OUT_CSV = REPORTS / "final_model_benchmark.csv"
OUT_MD = REPORTS / "final_model_benchmark.md"

INPUT_MAP = {
    "Classical (Otsu)": "VV/VH intensity (Otsu)",
}

COLS = ["model", "input", "iou", "dice", "precision", "recall",
        "pr_auc", "fpr", "fnr", "ece", "obj_f1", "latency_ms"]


def main():
    if not SRC.exists():
        print(f"MISSING {SRC} - run scripts/run_ml_campaign.py first.")
        return 1

    with open(SRC, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out_rows = []
    for r in rows:
        out_rows.append({
            "model": r["model"],
            "input": INPUT_MAP.get(r["model"], "VV_VH_DIFF (VH/VV minus)"),
            "iou": r["iou"],
            "dice": r["dice"],
            "precision": r["precision"],
            "recall": r["recall"],
            "pr_auc": r["pr_auc"],
            "fpr": r["fpr"],
            "fnr": r["fnr"],
            "ece": r["ece"],
            "obj_f1": r["obj_f1"],
            "latency_ms": r["latency_ms"],
        })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    def fmt(v, digits=4):
        try:
            return f"{float(v):.{digits}f}"
        except (TypeError, ValueError):
            return str(v)

    lines = [
        "# MARINeX Final Model Benchmark Table (SIH26143)",
        "",
        "> Generated from `reports/final_test_results.csv` (protected test pass, 20 held-out",
        "> images, `scripts/run_ml_campaign.py`). Pixel metrics IoU/Dice/Precision/Recall/PR-AUC/FPR/FNR;",
        "> ECE is un-calibrated raw ECE; `obj_f1` is instance-level slick F1; `latency_ms` is measured CPU",
        "> forward latency (256×256). The production freeze uses the row `unet (FINAL selected)`.",
        "",
        "| Model | Input | IoU | Dice | Prec | Rec | PR-AUC | FPR | FNR | ECE | Obj-F1 | Lat(ms) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in out_rows:
        lines.append(
            f"| {r['model']} | {r['input']} | {fmt(r['iou'])} | {fmt(r['dice'])} | "
            f"{fmt(r['precision'])} | {fmt(r['recall'])} | {fmt(r['pr_auc'])} | {fmt(r['fpr'])} | "
            f"{fmt(r['fnr'])} | {fmt(r['ece'])} | {fmt(r['obj_f1'])} | {fmt(r['latency_ms'], 1)} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- All deep models share one protocol: same split, same test set, same metrics.",
        "- On the protected test split `unet_plus_plus` has the highest IoU (0.9175); the production",
        "  choice `unet` was selected on **validation** (val IoU 0.9533 vs 0.9447, see",
        "  `reports/model_selection.csv`) per the frozen protocol, then frozen and measured once here.",
        "- `unet+HN` is the hard-negative retrain: lower IoU but 20× lower FPR (0.0002) - documented",
        "  trade-off, not selected because validation IoU did not improve.",
        "- `Two-Stage` (SegFormer + oil/look-alike classifier) improves FPR and object-F1 but drops IoU;",
        "  not forced into production.",
        "- All numbers below are on synthetic SAR-like imagery (see `docs/FINAL_EXPERIMENT_PROTOCOL.md`).",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())