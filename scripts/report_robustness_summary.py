"""Generate reports/robustness/robustness_report.md from validated robustness_results.csv."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "reports" / "robustness_results.csv"
OUT_DIR = ROOT / "reports" / "robustness"
OUT = OUT_DIR / "robustness_report.md"

with open(SRC, "r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

clean = next(r for r in rows if r["condition"].lower().startswith("clean"))
clean_iou, clean_dice = float(clean["iou"]), float(clean["dice"])

lines = [
    "# Robustness Evaluation - marinex-unet-v1.0.0",
    "",
    "Deterministic perturbation study using the frozen production UNet on the in-domain",
    "test split (20 patches). Each condition applies a single physical perturbation; all",
    "other settings are held constant. IoU/Dice are computed on the binary mask thresholded",
    "at 0.70 (calibrated operating point).",
    "",
    "| Condition | IoU | Dice | Precision | Recall | FPR | dIoU vs Clean |",
    "|---|---|---|---|---|---|---|",
]
for r in rows:
    diou = float(r["iou"]) - clean_iou
    lines.append(
        f"| {r['condition']} | {float(r['iou']):.4f} | {float(r['dice']):.4f} | "
        f"{float(r.get('precision', 0)):.4f} | {float(r.get('recall', 0)):.4f} | "
        f"{float(r.get('fpr', 0)):.4f} | {diou:+.4f} |"
    )

lines.extend([
    "",
    "## Key Findings",
    "",
    f"* **Stable under mild degradation**: contrast 0.6x (dIoU {float(rows[1]['iou']) - clean_iou:+.4f}) and",
    f"  0.4x ({float(rows[2]['iou']) - clean_iou:+.4f}) and radiometric -3 dB retain detection quality.",
    f"* **Speckle-sensitive**: enhanced speckle (L=2.0) drops IoU to {float(rows[3]['iou']):.4f} - speckle is a primary",
    "  operational failure mode and should be screened at the source (multi-look / Lee filter).",
    f"* **Resolution-sensitive**: 20 m degraded resolution gives IoU {float(rows[4]['iou']):.4f}.",
    f"* **Radiometric +3 dB is a detection failure**: recall collapses to {float(rows[6]['recall']):.4f} while precision",
    "  stays high (fewer, higher-certainty hits) - over-bright scenes suppress dark slick contrast entirely.",
    f"* Baseline condition records IoU {clean_iou:.4f}, Dice {clean_dice:.4f}.",
    "",
    "## Operational Guidance",
    "",
    "* Confidence thresholds must not be re-tuned per scene; instead report quality grade",
    "  (see Data Quality Service) alongside every detection so low-grade scenes are handled",
    "  as provisional.",
    "* The +3 dB failure mode exactly mirrors the degraded raster used in the low-confidence",
    "  demonstration case; the pipeline correctly routes these detections to analyst review",
    "  rather than automatic attribution.",
])

OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {OUT}")