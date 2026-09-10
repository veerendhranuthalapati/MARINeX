"""
AUDIT CLI — Phase 5 / Phase 44 fail-safe.

Usage:
    python -m ml.data_audit.audit_dataset [--datasets p,e] [--write-split]

Scans configured SAR datasets, validates integrity, verifies group-aware
leakage-free splits, and writes:
    reports/sar_dataset_report.json
    reports/sar_dataset_report.md
    data/manifests/<dataset_id>.json   (refreshed with n_samples)

Exit code: 0 on success, 1 if any dataset is corrupt/invalid or if leakage is
detected (fail loud — never silently continue).
"""

from __future__ import annotations

import os
import json
import argparse
from typing import Any, Dict, List

from ml.data_audit.dataset_inventory import scan_dataset
from ml.data_audit.validate_dataset import validate_inventory
from ml.data.leakage_detection import detect_data_leakage
from ml.data.manifest import load_dataset_config, build_manifest, save_manifest

DATASETS = {
    "p": ("data/datasets/sentinel1_primary", "configs/datasets/sentinel1_oilspill_primary.yaml"),
    "e": ("data/datasets/sentinel1_external", "configs/datasets/sentinel1_oilspill_external.yaml"),
}
SPLIT_PATH = "data/splits/split_group_aware_v1.json"


def audit_one(dataset_root: str, config_path: str, split: Any = None) -> Dict[str, Any]:
    print(f"[audit] Scanning  {dataset_root}")
    inventory = scan_dataset(dataset_root)
    validation = validate_inventory(inventory)

    report = {
        "dataset_root": inventory["dataset_root"],
        "inventory": {
            "total_images_found": inventory["total_images_found"],
            "total_masks_found": inventory["total_masks_found"],
            "paired_samples_count": inventory["paired_samples_count"],
            "unpaired_images_count": inventory["unpaired_images_count"],
            "corrupted_files_count": inventory["corrupted_files_count"],
            "corrupted_files": inventory["corrupted_files"],
            "duplicate_groups_count": inventory["duplicate_groups_count"],
        },
        "validation": {
            "is_valid": validation["is_valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "summary": validation["summary"],
        },
        "leakage": None,
    }

    # Leakage check only for the primary dataset (it is the only one with splits).
    if split is not None:
        leakage = detect_data_leakage(inventory, split)
        report["leakage"] = leakage
        print(f"  leakage: {leakage['verification_status']}")

    # Refresh manifest n_samples using real paired-sample count.
    if config_path and os.path.exists(config_path):
        config = load_dataset_config(config_path)
        m = build_manifest(config)
        if inventory["paired_samples_count"]:
            m.n_samples = inventory["paired_samples_count"]
        if m.status == "local" and report["inventory"]["corrupted_files_count"] == 0:
            m.status = "local"
        save_manifest(m, "data/manifests")

    ok = validation["is_valid"] and (split is None or not report["leakage"]["leakage_detected"])
    report["ok"] = ok
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="MARINeX SAR dataset audit")
    ap.add_argument("--datasets", default="p", help="comma-separated: p=primary, e=external")
    args = ap.parse_args()

    split = None
    if os.path.exists(SPLIT_PATH):
        with open(SPLIT_PATH, "r") as f:
            split = json.load(f)

    os.makedirs("reports", exist_ok=True)
    os.makedirs("data/manifests", exist_ok=True)

    results: List[Dict[str, Any]] = []
    all_ok = True
    for key in [k.strip() for k in args.datasets.split(",")]:
        if key not in DATASETS:
            print(f"[error] unknown dataset key '{key}'")
            all_ok = False
            continue
        root, cfg = DATASETS[key]
        r = audit_one(root, cfg, split=split if key == "p" else None)
        results.append(r)
        all_ok = all_ok and r["ok"]

    with open("reports/sar_dataset_report.json", "w", encoding="utf-8") as f:
        json.dump({"datasets": results}, f, indent=2)

    # Markdown report
    md_lines = ["# MARINeX SAR Dataset Audit Report\n"]
    for r in results:
        s = r["validation"]["summary"]
        inv = r["inventory"]
        md_lines += [
            f"## {os.path.basename(r['dataset_root'])}",
            "",
            f"- **Paired samples**: {inv['paired_samples_count']}  "
            f"(images {inv['total_images_found']}, masks {inv['total_masks_found']})",
            f"- **Corrupted files**: {inv['corrupted_files_count']}",
            f"- **Duplicate groups**: {inv['duplicate_groups_count']}",
            f"- **Valid**: {'YES' if r['validation']['is_valid'] else 'NO'}",
            f"- **Zero-mask patches**: {s['zero_mask_count']} ({s['zero_mask_percentage']:.1f}%)",
            f"- **Oil-bearing patches**: {s['oil_samples_count']}",
            f"- **Look-alike patches**: {s['lookalike_samples_count']}",
            f"- **Clean sea patches**: {s['clean_sea_count']}",
            f"- **Mean oil foreground ratio**: {s['mean_oil_foreground_ratio']*100:.2f}%",
            f"- **Mean look-alike ratio**: {s['mean_lookalike_foreground_ratio']*100:.2f}%",
        ]
        if r["validation"]["errors"]:
            md_lines += ["- **ERRORS**:", *[f"  - {e}" for e in r["validation"]["errors"]]]
        if r["validation"]["warnings"]:
            md_lines += ["- **WARNINGS**:", *[f"  - {w}" for w in r["validation"]["warnings"]]]
        if r["leakage"]:
            md_lines += ["", f"- **Leakage**: {r['leakage']['verification_status']}"]
        md_lines += ["", ""]

    with open("reports/sar_dataset_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print("\n[audit] wrote reports/sar_dataset_report.json, reports/sar_dataset_report.md")
    print(f"[audit] overall ok: {all_ok}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())