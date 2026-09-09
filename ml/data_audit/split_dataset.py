"""
Group-Aware Dataset Splitting Module.
Guarantees zero train/val/test leakage by partitioning by parent Sentinel-1 acquisition scene.
"""

import os
import json
import random
from typing import Dict, List, Any

def create_group_aware_split(
    inventory: Dict[str, Any],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    output_path: str = "data/splits/split_group_aware_v1.json"
) -> Dict[str, Any]:
    """
    Partitions samples by parent_scene_id so that all patches from any satellite scene
    belong exclusively to either Train, Validation, or Test.
    """
    random.seed(seed)
    samples = inventory.get("samples", [])
    if not samples:
        raise ValueError("Cannot split empty dataset.")

    # Group samples by parent_scene_id
    scene_groups = {}
    for s in samples:
        scene_id = s.get("parent_scene_id", "unknown")
        if scene_id not in scene_groups:
            scene_groups[scene_id] = []
        scene_groups[scene_id].append(s)

    unique_scenes = sorted(list(scene_groups.keys()))
    random.shuffle(unique_scenes)

    num_scenes = len(unique_scenes)
    num_val = max(1, int(round(num_scenes * val_ratio)))
    num_test = max(1, int(round(num_scenes * test_ratio)))
    num_train = num_scenes - num_val - num_test

    train_scenes = unique_scenes[:num_train]
    val_scenes = unique_scenes[num_train:num_train + num_val]
    test_scenes = unique_scenes[num_train + num_val:]

    train_samples = []
    val_samples = []
    test_samples = []

    for sc in train_scenes:
        train_samples.extend(scene_groups[sc])
    for sc in val_scenes:
        val_samples.extend(scene_groups[sc])
    for sc in test_scenes:
        test_samples.extend(scene_groups[sc])

    # Build split manifest
    split_manifest = {
        "split_strategy": "group_aware_parent_scene",
        "random_seed": seed,
        "parent_scenes": {
            "train": train_scenes,
            "val": val_scenes,
            "test": test_scenes
        },
        "sample_counts": {
            "train": len(train_samples),
            "val": len(val_samples),
            "test": len(test_samples),
            "total": len(samples)
        },
        "splits": {
            "train": [s["sample_id"] for s in train_samples],
            "val": [s["sample_id"] for s in val_samples],
            "test": [s["sample_id"] for s in test_samples]
        },
        "class_balance": {
            "train": {
                "oil": sum(1 for s in train_samples if s["has_oil"]),
                "lookalike": sum(1 for s in train_samples if s["has_lookalike"]),
                "clean": sum(1 for s in train_samples if not s["has_oil"] and not s["has_lookalike"])
            },
            "val": {
                "oil": sum(1 for s in val_samples if s["has_oil"]),
                "lookalike": sum(1 for s in val_samples if s["has_lookalike"]),
                "clean": sum(1 for s in val_samples if not s["has_oil"] and not s["has_lookalike"])
            },
            "test": {
                "oil": sum(1 for s in test_samples if s["has_oil"]),
                "lookalike": sum(1 for s in test_samples if s["has_lookalike"]),
                "clean": sum(1 for s in test_samples if not s["has_oil"] and not s["has_lookalike"])
            }
        }
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(split_manifest, f, indent=2)

    print(f"Group-aware split generated at: {output_path}")
    print(f"Train: {len(train_samples)} samples ({len(train_scenes)} scenes)")
    print(f"Val:   {len(val_samples)} samples ({len(val_scenes)} scenes)")
    print(f"Test:  {len(test_samples)} samples ({len(test_scenes)} scenes)")

    return split_manifest

if __name__ == "__main__":
    from ml.data_audit.dataset_inventory import scan_dataset
    inv = scan_dataset("data/datasets/sentinel1_primary")
    create_group_aware_split(inv)
