"""Freeze the FINAL MARINeX UNet for production (SIH26143).

Copies the campaign-selected checkpoint to models/best_model/marinex_unet_v1.pt,
appending the frozen operating point and frozen-test/calibration provenance so
every production consumer shares one decision rule.

Frozen decisions (from the completed Phase 1-11 campaign):
  architecture = unet, threshold = 0.70 (calibration.json best_iou_threshold),
  temperature = 0.226 (log-space), ECE 17.35% -> 0.46%.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CHKPT_DIR = ROOT / "models" / "campaign"
BEST_DIR = ROOT / "models" / "best_model"
REPORTS = ROOT / "reports"


def read_csv(name: str) -> list[dict]:
    with open(REPORTS / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    BEST_DIR.mkdir(exist_ok=True)
    calib = json.loads((REPORTS / "calibration.json").read_text())
    final_row = next(r for r in read_csv("final_test_results.csv")
                     if r["model"] == "unet (FINAL selected)")
    temp = float(calib["temperature"])

    final_th = float(calib["threshold"])
    if abs(final_th - 0.70) > 1e-6:
        print(f"WARNING: calibration threshold changed to {final_th:.4f}")

    ckpt_name = "arch_unet_best.pt"
    ckpt = torch.load(CHKPT_DIR / ckpt_name, map_location="cpu")
    ckpt["metadata"] = dict(ckpt.get("metadata", {}),
                            production=True,
                            frozen_threshold=final_th,
                            temperature=temp,
                            calibration={"ece_raw": calib["ece_raw"],
                                         "ece_calibrated": calib["ece_calibrated"]},
                            frozen_test={"iou": float(final_row["iou"]),
                                         "dice": float(final_row["dice"]),
                                         "precision": float(final_row["precision"]),
                                         "recall": float(final_row["recall"])})
    out = BEST_DIR / "marinex_unet_v1.pt"
    torch.save(ckpt, out)
    print(f"froze {ckpt_name} -> {out}")
    fiou, fdice = float(final_row["iou"]), float(final_row["dice"])
    print(f"  threshold={final_th:.3f} temperature={temp:.3f} "
          f"frozen_test IoU={fiou:.4f} Dice={fdice:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())