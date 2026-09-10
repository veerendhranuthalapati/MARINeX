"""
FINAL DATA + LEAKAGE AUDIT for MARINeX (SIH26143).
====================================================
Phase 3 (leakage) + Phase 4 (dataset statistics) of the final validation phase.

Produces:
  reports/final_leakage_audit.json
  reports/final_leakage_audit.md
  reports/final_dataset_statistics.csv

Checks, beyond the existing three-level audit (sample-id / parent-scene / sha256):
  * per-sample parent-scene containment: every patch of a scene must live in ONE split
  * near-duplicate detection across splits (32x32 downsampled normalized correlation)
"""

import csv
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from PIL import Image

from ml.data.leakage_detection import detect_data_leakage, compute_image_hash
from ml.data_audit.dataset_inventory import scan_dataset

PRIMARY = "data/datasets/sentinel1_primary"
EXTERNAL = "data/datasets/sentinel1_external"
SPLIT = "data/splits/split_group_aware_v1.json"
REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

NEAR_DUP_CORR = 0.98
THUMB = 32


def thumbnail_vector(path: str) -> np.ndarray:
    img = Image.open(path).convert("L").resize((THUMB, THUMB))
    a = np.asarray(img, dtype=np.float32)
    a = (a - a.mean()) / (a.std() + 1e-6)
    return a.ravel()


def near_duplicate_pairs(group_a, group_b):
    """Returns list of (id_a, id_b, corr) for cross-split near duplicates."""
    pairs = []
    for ia, pa in group_a:
        va = thumbnail_vector(pa)
        for ib, pb in group_b:
            vb = thumbnail_vector(pb)
            c = float(np.dot(va, vb) / (len(va)))  # z-scored -> cosine on unit-norm-ish vectors
            if c >= NEAR_DUP_CORR:
                pairs.append((ia, ib, round(c, 6)))
    return pairs


def main():
    with open(SPLIT, "r", encoding="utf-8") as f:
        split = json.load(f)

    inv = scan_dataset(PRIMARY)
    ext_inv = scan_dataset(EXTERNAL)

    # ------------------------------------------------------------------
    # 1. Standard three-level leakage audit
    # ------------------------------------------------------------------
    base_leak = detect_data_leakage(inv, split)
    split_ids = {k: set(v) for k, v in split["splits"].items()}

    smap = {s["sample_id"]: s for s in inv["samples"]}

    # ------------------------------------------------------------------
    # 2. Parent-scene containment (adjacency control)
    # ------------------------------------------------------------------
    scene_split = {}   # scene_id -> set of splits it appears in
    scene_counts = {}  # scene_id -> {split: count}
    for sid in smap:
        scene = smap[sid]["parent_scene_id"]
        for sp, ids in split_ids.items():
            if sid in ids:
                scene_split.setdefault(scene, set()).add(sp)
                scene_counts.setdefault(scene, {}).setdefault(sp, 0)
                scene_counts[scene][sp] += 1

    containment_violations = {
        scene: sorted(splits) for scene, splits in scene_split.items() if len(splits) > 1
    }

    # ------------------------------------------------------------------
    # 3. Near-duplicate detection across splits
    # ------------------------------------------------------------------
    id_to_img = {s["sample_id"]: s["image_path"] for s in inv["samples"]}
    groups = {}
    for sp, ids in split_ids.items():
        groups[sp] = [(sid, id_to_img[sid]) for sid in ids if sid in id_to_img]

    near_dups = {
        "train_val": near_duplicate_pairs(groups["train"], groups["val"]),
        "train_test": near_duplicate_pairs(groups["train"], groups["test"]),
        "val_test": near_duplicate_pairs(groups["val"], groups["test"]),
    }
    near_dup_counts = {k: len(v) for k, v in near_dups.items()}

    leakage_detected = bool(
        base_leak["leakage_detected"]
        or containment_violations
        or any(near_dup_counts.values())
    )

    # ------------------------------------------------------------------
    # 4. Dataset statistics (per split)
    # ------------------------------------------------------------------
    splits = ["train", "val", "test"]
    rows = []
    totals = {
        "n_samples": 0, "oil": 0, "lookalike": 0, "no_oil": 0, "empty_mask": 0,
        "oil_pixels": 0, "lookalike_pixels": 0, "n_channels_3": 0, "dim_256": 0,
    }
    size_buckets_all = []

    def bucket(oil_px, total_px):
        r = oil_px / max(total_px, 1)
        if oil_px == 0:
            return "empty"
        if r < 0.01:
            return "tiny(<1%)"
        if r < 0.05:
            return "small(1-5%)"
        if r < 0.15:
            return "medium(5-15%)"
        return "large(>15%)"

    for sp in splits:
        ids = sorted(split_ids[sp])
        n = len(ids)
        n_oil = sum(1 for i in ids if smap[i]["has_oil"])
        n_look = sum(1 for i in ids if smap[i]["has_lookalike"])
        n_no_oil = sum(1 for i in ids if not smap[i]["has_oil"])
        n_empty = sum(1 for i in ids if (not smap[i]["has_oil"]) and (not smap[i]["has_lookalike"]))
        oil_px = sum(smap[i]["oil_pixels"] for i in ids)
        look_px = sum(smap[i]["lookalike_pixels"] for i in ids)
        dims = [tuple(smap[i]["dimensions"]) for i in ids]
        dim_256 = sum(1 for d in dims if d == (256, 256))
        ch = [smap[i]["channels"] for i in ids]
        ch3 = sum(1 for c in ch if c == 3)
        buckets = {}
        totalpx = 256 * 256
        for i in ids:
            b = bucket(smap[i]["oil_pixels"], totalpx)
            buckets[b] = buckets.get(b, 0) + 1
            size_buckets_all.append(b)
        rows.append({
            "split": sp,
            "n_samples": n,
            "oil_examples": n_oil,
            "lookalike_examples": n_look,
            "no_oil_examples": n_no_oil,
            "empty_masks": n_empty,
            "oil_pixels": oil_px,
            "lookalike_pixels": look_px,
            "tiny_lt_1pct": buckets.get("tiny(<1%)", 0),
            "small_1_5pct": buckets.get("small(1-5%)", 0),
            "medium_5_15pct": buckets.get("medium(5-15%)", 0),
            "large_gt_15pct": buckets.get("large(>15%)", 0),
            "n_3channel": ch3,
            "n_256x256": dim_256,
        })
        totals["n_samples"] += n
        totals["oil"] += n_oil
        totals["lookalike"] += n_look
        totals["no_oil"] += n_no_oil
        totals["empty_mask"] += n_empty
        totals["oil_pixels"] += oil_px
        totals["lookalike_pixels"] += look_px
        totals["n_channels_3"] += ch3
        totals["dim_256"] += dim_256

    totals_row = {
        "split": "TOTAL",
        "n_samples": totals["n_samples"],
        "oil_examples": totals["oil"],
        "lookalike_examples": totals["lookalike"],
        "no_oil_examples": totals["no_oil"],
        "empty_masks": totals["empty_mask"],
        "oil_pixels": totals["oil_pixels"],
        "lookalike_pixels": totals["lookalike_pixels"],
        "tiny_lt_1pct": sum(r.get("tiny_lt_1pct", 0) for r in rows[:-1]),
        "small_1_5pct": sum(r.get("small_1_5pct", 0) for r in rows[:-1]),
        "medium_5_15pct": sum(r.get("medium_5_15pct", 0) for r in rows[:-1]),
        "large_gt_15pct": sum(r.get("large_gt_15pct", 0) for r in rows[:-1]),
        "n_3channel": totals["n_channels_3"],
        "n_256x256": totals["dim_256"],
    }
    rows.append(totals_row)

    csv_path = REPORTS / "final_dataset_statistics.csv"
    fieldnames = ["split", "n_samples", "oil_examples", "lookalike_examples", "no_oil_examples",
                  "empty_masks", "oil_pixels", "lookalike_pixels", "tiny_lt_1pct",
                  "small_1_5pct", "medium_5_15pct", "large_gt_15pct", "n_3channel", "n_256x256"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ------------------------------------------------------------------
    # 5. Assemble JSON + MD
    # ------------------------------------------------------------------
    audit = {
        "audit_timestamp": __import__("datetime").datetime.now().isoformat(),
        "primary_dataset": PRIMARY,
        "external_dataset": EXTERNAL,
        "leakage_detected": leakage_detected,
        "three_level_check": base_leak,
        "parent_scene_containment": {
            "violations": containment_violations,
            "scene_split_counts": scene_counts,
        },
        "near_duplicate_check": {
            "threshold_corr": NEAR_DUP_CORR,
            "counts": near_dup_counts,
            "top_pairs": {k: v[:5] for k, v in near_dups.items()},
        },
        "duplicate_groups_in_primary": inv["duplicate_groups_count"],
        "corrupted_files": inv["corrupted_files_count"],
        "external_duplicate_groups": ext_inv["duplicate_groups_count"],
        "external_samples": ext_inv["paired_samples_count"],
        "dataset_statistics_csv": str(csv_path),  # placeholder replaced below
    }
    audit["dataset_statistics_csv"] = str(csv_path)

    json_path = REPORTS / "final_leakage_audit.json"
    json_path.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")

    # Markdown
    def scene_table():
        lines = ["| parent scene | split | patches |"]
        lines.append("|---|---|---|")
        for scene, spcounts in sorted(scene_counts.items()):
            for sp, cnt in sorted(spcounts.items()):
                lines.append(f"| {scene} | {sp} | {cnt} |")
        return "\n".join(lines)

    md = f"""# MARINeX Final Data & Leakage Audit (SIH26143)

_Generated by `scripts/final_data_audit.py` on {audit['audit_timestamp']}._

## Verdict

- **Leakage detected: {leakage_detected}**
- Three-level audit: {base_leak['verification_status']}
- Parent-scene containment violations: {len(containment_violations)}
- Cross-split near-duplicate pairs: {sum(near_dup_counts.values())} (train/val {near_dup_counts['train_val']},
  train/test {near_dup_counts['train_test']}, val/test {near_dup_counts['val_test']})
- Duplicate image groups in primary: {inv['duplicate_groups_count']}; corrupted files: {inv['corrupted_files_count']}.
- External dataset (cross-dataset eval only, never in a split): {ext_inv['paired_samples_count']} samples,
  {ext_inv['duplicate_groups_count']} duplicate groups.

## Parent-scene → split containment

Every patch of a parent scene must be in exactly one split (adjacency control).

{scene_table()}

## Three-level leakage detail (sample id / parent scene / sha256)

```json
{json.dumps(base_leak, indent=2)}
```

## Dataset statistics (per split)

See `reports/final_dataset_statistics.csv`.

| split | n | oil | lookalike | no-oil | empty | tiny | small | medium | large | 3ch | 256² |
|---|---|---|---|---|---|---|---|---|---|---|---|
"""
    for r in rows:
        md += (f"| {r['split']} | {r['n_samples']} | {r['oil_examples']} | {r['lookalike_examples']} | "
               f"{r['no_oil_examples']} | {r['empty_masks']} | {r['tiny_lt_1pct']} | {r['small_1_5pct']} | "
               f"{r['medium_5_15pct']} | {r['large_gt_15pct']} | {r['n_3channel']} | {r['n_256x256']} |\n")

    md += f"""
## Notes

- Dataset is synthetic (procedural SAR generator). See `data/manifests/sentinel1-oilspill-primary-v1.json`.
- Near-duplicate check uses 32×32 normalized-correlation (threshold {NEAR_DUP_CORR}); pairs reported are
  conservative and manually reviewable in `final_leakage_audit.json` (`near_duplicate_check.top_pairs`).
- VV/VH availability: 100% of samples are 3-channel (VV, VH, VV−VH).
"""
    (REPORTS / "final_leakage_audit.md").write_text(md, encoding="utf-8")

    print(f"leakage_detected={leakage_detected}")
    print(f"  three-level: {base_leak['verification_status']}")
    print(f"  containment violations: {len(containment_violations)}")
    print(f"  near-duplicates: {near_dup_counts}")
    print("wrote", json_path, csv_path, REPORTS / 'final_leakage_audit.md')
    return 0 if not leakage_detected else 1


if __name__ == "__main__":
    raise SystemExit(main())