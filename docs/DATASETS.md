# MARINeX Datasets

## Origin & honesty policy

All imagery in this repository is **100% synthetic**. The SAR-like patches are
procedurally generated (`ml/data/generate_sar_dataset.py`): dark-polynomial slick
morphologies, realistic sea-clutter Rayleigh noise, wind streaks, and instrument
speckle. Masks encode `0` = background, `1` = oil, `2` = look-alike (low-wind
zones / biogenic surfactants). Class `3/4` labels are never generated.

> Reports and papers must be labeled synthetic-only and must never claim
> real-world aircraft/satellite truth. This is a model-development benchmark.

## Formats

- Patches: 256×256 PNG, 3 channels `[VV, VH, VV_minus_VH]`
- Masks: 256×256 PNG, 8-bit grayscale, values 0/1/2
- Descriptors: `configs/datasets/sentinel1_oilspill_{primary,external}.yaml`

## Formation & size

| Dataset | Scenes | Patches | Location | Total size |
|---|---|---|---|---|
| Primary | 12 | 120 | Arabian Sea (Mumbai Offshore corridor) | 21.6 MB |
| External | 4 | 40 | Singapore Strait / Malacca | 7.2 MB |

## Split — group-aware, zero leakage

`data/splits/split_group_aware_v1.json`

The split is computed on **parent scenes**, never on patches, so patches from the
same scene cannot leak across train/validation/test. Leakage detection runs in the
audit CLI and re-verifies group disjointness on every audit.

- Verified: **PASSED — zero leakage between parent scenes and splits**
- Oil vs look-alike vs clean-sea class balance is preserved per fold.

## Dataset inventory

```text
data/datasets/
├── sentinel1_primary/
│   ├── images/patch_0001.png ... patch_0120.png
│   └── masks/patch_0001.png  ... patch_0120.png
└── sentinel1_external/
    ├── images/patch_0001.png ... patch_0040.png
    └── masks/patch_0001.png  ... patch_0040.png
```

## Inspection commands

```bash
python scripts/data_status.py                 # catalog table
python -m ml.data_audit.audit_dataset --datasets p,e   # integrity + leakage audit
```