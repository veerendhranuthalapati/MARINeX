r"""Production Metadata Generator (Phases 2-3).

Reads all campaign reports, checkpoint metadata, splits, and robustness data
to produce models/production/metadata.json with full provenance.

Usage:
    .venv/Scripts/python scripts/production_metadata.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch

REPORTS = ROOT / "reports"
MODELS = ROOT / "models"
PROD_DIR = MODELS / "production"
CHKPT = MODELS / "best_model" / "marinex_unet_v1.pt"


def read_csv_rows(name: str) -> list[dict]:
    with open(REPORTS / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    PROD_DIR.mkdir(parents=True, exist_ok=True)

    ckpt = torch.load(CHKPT, map_location="cpu")
    ckpt_meta = ckpt.get("metadata", {})

    calib = json.loads((REPORTS / "calibration.json").read_text())
    splits = json.loads((ROOT / "data" / "splits" / "split_group_aware_v1.json").read_text())

    robustness_rows = read_csv_rows("robustness_results.csv")
    cross_rows = read_csv_rows("cross_dataset_results.csv")
    seed_rows = read_csv_rows("multi_seed.csv")

    final_row = next(
        (r for r in read_csv_rows("final_test_results.csv")
         if r["model"] == "unet (FINAL selected)"),
        None,
    )

    frozen_test = ckpt_meta.get("frozen_test", {})
    if final_row and not frozen_test:
        frozen_test = {
            "iou": float(final_row["iou"]),
            "dice": float(final_row["dice"]),
            "precision": float(final_row["precision"]),
            "recall": float(final_row["recall"]),
            "fpr": float(final_row["fpr"]),
            "object_f1": float(final_row["obj_f1"]),
        }
    elif final_row:
        frozen_test.setdefault("fpr", float(final_row["fpr"]))
        frozen_test.setdefault("object_f1", float(final_row["obj_f1"]))

    metadata = {
        "model_name": "marinex-unet-v1.0.0",
        "architecture": "UNetBaseline",
        "framework": "PyTorch",
        "checkpoint_path": "models/best_model/marinex_unet_v1.pt",
        "dataset": {
            "name": "sentinel1-primary",
            "total_samples": splits["sample_counts"]["total"],
            "split": {
                "train": splits["sample_counts"]["train"],
                "val": splits["sample_counts"]["val"],
                "test": splits["sample_counts"]["test"],
            },
            "parent_scenes": {
                "train": splits["parent_scenes"]["train"],
                "val": splits["parent_scenes"]["val"],
                "test": splits["parent_scenes"]["test"],
            },
        },
        "preprocessing": {
            "strategy": "percentile",
            "channels": ["VV", "VH", "VV-VH"],
            "input_shape": [3, 256, 256],
        },
        "threshold": calib["threshold"],
        "calibration": {
            "temperature": calib["temperature"],
            "ece_raw": calib["ece_raw"],
            "ece_calibrated": calib["ece_calibrated"],
            "brier_raw": calib["brier_raw"],
            "brier_calibrated": calib["brier_calibrated"],
        },
        "frozen_test_metrics": {
            "iou": frozen_test.get("iou", 0.0),
            "dice": frozen_test.get("dice", 0.0),
            "precision": frozen_test.get("precision", 0.0),
            "recall": frozen_test.get("recall", 0.0),
            "fpr": frozen_test.get("fpr", 0.0),
            "object_f1": frozen_test.get("object_f1", 0.0),
        },
        "multi_seed_stability": [
            {
                "seed": int(r["seed"]),
                "val_iou": float(r["val_iou"]),
                "val_dice": float(r["val_dice"]),
            }
            for r in seed_rows
        ],
        "robustness": [
            {
                "condition": r["condition"],
                "iou": float(r["iou"]),
                "dice": float(r["dice"]),
                "precision": float(r["precision"]),
                "recall": float(r["recall"]),
                "fpr": float(r["fpr"]),
            }
            for r in robustness_rows
        ],
        "cross_dataset": [
            {
                "evaluation_domain": r["evaluation_domain"],
                "dataset_name": r["dataset_name"],
                "iou": float(r["iou"]),
                "dice": float(r["dice"]),
                "precision": float(r["precision"]),
                "recall": float(r["recall"]),
                "fpr": float(r["fpr"]),
            }
            for r in cross_rows
        ],
        "git_commit": "f764d88",
        "frozen_at": "2026-09-10",
        "freeze_script": "scripts/freeze_final_model.py",
    }

    out = PROD_DIR / "metadata.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Wrote {out}")
    print(f"  model: {metadata['model_name']}")
    print(f"  threshold: {metadata['threshold']}")
    print(f"  temperature: {metadata['calibration']['temperature']:.4f}")
    print(f"  frozen_test IoU: {metadata['frozen_test_metrics']['iou']:.4f}")
    print(f"  seeds: {len(metadata['multi_seed_stability'])}")
    print(f"  robustness conditions: {len(metadata['robustness'])}")
    print(f"  cross-dataset evals: {len(metadata['cross_dataset'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
