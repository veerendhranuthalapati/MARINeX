# MARINeX Data Layout

The project never assumes the entire dataset lives on a developer's local PC.
This directory defines the *storage policy* — what may live where, and what the
repository may contain.

```
data/
├── raw/          # NEVER committed (see .gitignore). Downstream source archives.
│                 # Selective downloads land here (region/time filtered).
├── samples/      # COMMITTED. Small deterministic demo/sample data for local dev
│                 # and the end-to-end demo (Phase 48). Marked "DEMO / SAMPLE ONLY".
├── interim/      # NEVER committed. Intermediate extraction / cleaning workspace.
├── processed/    # COMMITTED (small) + ignored bulk. Working analytical data:
│   │             #   processed/ais/partitions/...  (parquet, regenerated)
│   └──           #   processed/ais/ais_sample.parquet
├── metadata/     # COMMITTED. Checksums, provenance records, provider notes.
├── manifests/    # COMMITTED. Dataset manifests produced by the manifest CLI.
│                 # Every dataset has a manifest (ml/data/manifest.py) describing
│                 # dataset_id, source, license, version, size, channels, coverage,
│                 # labels, split — so data can be queried WITHOUT downloading.
└── splits/       # COMMITTED. Split manifests (e.g. split_group_aware_v1.json).
```

## Policy

- **Never commit**: national AIS archives, hundreds of GB of raw SAR,
  downloads in `data/raw/` or `data/interim/`, caches, training checkpoints,
  credentials.
- **Training pipeline never depends on `data/samples/`** — sample data is for
  development and the local demo only.
- **Remote / filtered access is preferred.** Where a source supports HTTP/API/
  object access, use the `DataProvider` layer (`ml/data/providers.py`) to query
  metadata, issue range requests, and selectively download only what an
  investigation / experiment needs.
- **Parquet + DuckDB** are the analytical layers for large AIS data — queries run
  against partitioned parquet without loading the archive into RAM.
- **PostGIS** (`docker-compose`) is used for final spatial intelligence
  (`ST_DWithin`, `ST_Intersects`, ...) on candidate subsets.

## Sample data (DEMO / SAMPLE ONLY)

`data/samples/` contains contracts and small fixtures (one scene, one slick, a
handful of AIS tracks, drift hindcast, candidates) used by the demo and tests.
It is **not** representative of production data and is **never** used for final
model training.

## Generating reports

```bash
# SAR dataset audit + manifest (both datasets)
.venv\Scripts\python.exe -m ml.data_audit.audit_dataset
# Per-sample visualization
.venv\Scripts\python.exe -m ml.data_audit.visualize_samples
```