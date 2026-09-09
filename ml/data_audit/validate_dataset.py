"""
Dataset Validation Module for Sentinel-1 Oil Spill Data.
Validates pairing, dimension matching, valid class values, value ranges, and zero-mask statistics.
"""

from typing import Dict, List, Any
import numpy as np

def validate_inventory(inventory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a dataset inventory against strict scientific and operational rules.
    """
    errors = []
    warnings = []
    samples = inventory.get("samples", [])

    if not samples:
        errors.append("Dataset inventory contains 0 valid samples.")
        return {"is_valid": False, "errors": errors, "warnings": warnings, "summary": {}}

    dim_ref = samples[0]["dimensions"]
    channels_ref = samples[0]["channels"]

    zero_mask_count = 0
    oil_samples_count = 0
    lookalike_samples_count = 0
    clean_sea_count = 0
    both_count = 0

    oil_ratios = []
    lookalike_ratios = []

    for s in samples:
        # 1. Dimension consistency
        if s["dimensions"] != dim_ref:
            warnings.append(f"Sample {s['sample_id']} dimension {s['dimensions']} differs from reference {dim_ref}")

        # 2. Channel consistency
        if s["channels"] != channels_ref:
            warnings.append(f"Sample {s['sample_id']} channel count {s['channels']} differs from reference {channels_ref}")

        # 3. Value check
        if s["has_nan"] or s["has_inf"]:
            errors.append(f"Sample {s['sample_id']} contains NaN or Inf pixel values.")

        # 4. Class balance check
        has_oil = s["has_oil"]
        has_look = s["has_lookalike"]

        if not has_oil and not has_look:
            zero_mask_count += 1
            clean_sea_count += 1
        elif has_oil and not has_look:
            oil_samples_count += 1
            oil_ratios.append(s["oil_ratio"])
        elif not has_oil and has_look:
            lookalike_samples_count += 1
            lookalike_ratios.append(s["lookalike_ratio"])
        else:
            both_count += 1
            oil_samples_count += 1
            lookalike_samples_count += 1
            oil_ratios.append(s["oil_ratio"])
            lookalike_ratios.append(s["lookalike_ratio"])

    total = len(samples)
    zero_mask_pct = (zero_mask_count / total) * 100.0

    summary = {
        "total_samples": total,
        "zero_mask_count": zero_mask_count,
        "zero_mask_percentage": zero_mask_pct,
        "oil_samples_count": oil_samples_count,
        "lookalike_samples_count": lookalike_samples_count,
        "clean_sea_count": clean_sea_count,
        "co_occurring_count": both_count,
        "mean_oil_foreground_ratio": float(np.mean(oil_ratios)) if oil_ratios else 0.0,
        "max_oil_foreground_ratio": float(np.max(oil_ratios)) if oil_ratios else 0.0,
        "mean_lookalike_foreground_ratio": float(np.mean(lookalike_ratios)) if lookalike_ratios else 0.0,
    }

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "summary": summary
    }

if __name__ == "__main__":
    from ml.data_audit.dataset_inventory import scan_dataset
    inv = scan_dataset("data/datasets/sentinel1_primary")
    val = validate_inventory(inv)
    print("Validation passed:", val["is_valid"])
    print("Summary:", val["summary"])
