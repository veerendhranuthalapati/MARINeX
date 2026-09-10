# MARINeX Data Architecture

The data layer provides reproducible, auditable access to all scientific assets:
satellite-imagery datasets, splits, manifests, and the AIS pipeline. Every number
reported here was produced on a real run; nothing is fabricated.

## Directory policy

| Path | Contents | Git |
|---|---|---|
| `data/datasets/` | Sentinel-1 SAR patches (primary + external) | ✅ committed |
| `data/raw/` | Unprocessed external downloads | ❌ ignored |
| `data/interim/` | Intermediate transforms | ❌ ignored |
| `data/processed/ais/partitions/` | Parquet year/month/day partitions | ❌ ignored (bulk) |
| `data/manifests/` | Per-dataset JSON manifests | ✅ committed |
| `data/splits/` | Group-aware split JSON | ✅ committed |
| `data/metadata/` | Scene calibration, attribution metadata | ✅ committed |
| `data/samples/` | Small demo CSVs / patches | ✅ committed |
| `*.duckdb`, `mlruns/` | Query engine DBs, MLflow runs | ❌ ignored |

## Manifest catalog

Each configured dataset has a descriptor (`configs/datasets/*.yaml`) and a computed
manifest (`data/manifests/<dataset_id>.json`) with `checksum`, `n_samples`,
`size_bytes`, and `status` (`local` / `remote` / `missing`).

- Catalog: `ml/data/manifest.py` (build, save, load, `catalog()`, `catalog_summary()`)
- Report: `python scripts/data_status.py`

Current catalog (real):

```
dataset_id                          samples status  local_bytes  checksum(16)
sentinel1-oilspill-external-v1            40 local      7202678  279f505e35a0caa3
sentinel1-oilspill-primary-v1            120 local     21612134  f25423bf21f0d193
```

## Audit + leakage fail-safe

`python -m ml.data_audit.audit_dataset --datasets p,e`

Scans every image/mask pair, validates integrity, checks for corrupted files, and
verifies **zero leakage** between parent scenes and train/val/test splits. On any
integrity failure or detected leakage it exits non-zero (fail loud — never silently
continue). Writes `reports/sar_dataset_report.{json,md}`.

Last verified run: both datasets valid, leakage **PASSED** (zero leakage).

## Remote / selective access

Environments inject the storage roots, so training and evaluation scripts are
location-independent:

| Env var | Meaning |
|---|---|
| `DATA_ROOT` | Dataset root (defaults to `data/datasets`) |
| `ARTIFACT_ROOT` | Model artifact root (defaults to `models`) |
| `SPLIT_PATH` | Split JSON (defaults to the group-aware split) |
| `REMOTE_DATA_URI` | Remote dataset URI for provisioning on GPU box |
| `REMOTE_ARTIFACT_URI` | Remote artifact pull URI |
| `MLFLOW_URI` | MLflow tracking server (optional) |

See `docs/REMOTE_TRAINING.md`.