# MARINeX AIS Validation (SIH26143)

Final-phase AIS module validation. Complements `docs/AIS.md` and
`docs/AIS_PIPELINE.md` with the re-run evidence from the closing phase and an
explicit, honest statement about data coverage.

## 1. Pipeline (as implemented)

- Provider: `CSVAISProvider` parses MarineCadastre-format position-report CSV
  (`mmsi, imo, vessel_name, vessel_type, flag, timestamp, latitude, longitude,
  speed_knots, course_deg, heading_deg, nav_status`).
- ML layer (`ml/ais/`): schema validation, cleaning (`bad_coordinates`,
  `impossible_speed`, `course_out_of_range`), dedupe, gap-aware trajectory
  segmentation, velocity-agnostic `haversine_km` reference math, and a DuckDB
  engine over partitioned parquet.
- Corridor queries: vessels by bbox + time window (drift-hindcast search
  corridor); `get_vessel_trajectory(vessel_id)` reconstructs the sorted track.

## 2. Partitioned engine — re-verified (Phase 26-27)

`scripts/prepare_ais.py` on the sample CSV reproduced the partitions and the
query benchmark:

- `data/processed/ais/partitions/year=2026/month=3/day=1/part_00000.parquet`
  (filtered 20 rows, written 20 rows, cleaning `{'valid': 20}`).
- `reports/ais_benchmark.json` (5 DuckDB queries over the partition):
  `region` 0.0092 s / `time` 0.0039 s / `region_time` 0.0040 s /
  `vessels` 0.0054 s / `trajectory_mmsi_636019842` 0.0034 s — all single-digit
  millisecond scans, 20/20 rows returned.
- Trajectory reconstruction: MMSI `636019842` → 7 points, 1 segment, first-leg
  haversine 6.964 km.

> Note: the parquet partitions are bulk data and gitignored; `prepare_ais.py`
> regenerates them deterministically from the committed sample CSV.

## 3. Data-quality audit (PASS)

`scripts/ais_audit.py` on `data/samples/sample_ais_trajectories.csv`
(20 records, 5 MMSI):

| Check | Result |
|---|---|
| Missing fields (mmsi/timestamp/lat/lon/speed/course) | 0 |
| Range / impossible values (speed ≥ 50 kn, bounds, course) | 0 |
| Duplicates (mmsi+timestamp) | 0 |
| Large jumps > 100 km | 0 |
| Synthetic trajectory validation (east / north+gap / 90° turn) | ALL PASS, error ~0.112% |

Artifacts: `reports/ais_quality_audit.csv`, `reports/ais_quality_report.md`,
`reports/ais_trajectory_validation.json`.

## 4. Integration in the incident path (verified E2E)

`scripts/run_pipeline_cli.py` on a fresh-schema DB: 5 vessels scanned in the
drift-hindcast corridor; the attribution engine ranked a primary suspect
(PACIFIC CROWN, forensic evidence score 40.6/100) with per-factor evidence —
see `docs/FINAL_ARCHITECTURE.md` §3.

## 5. Honesty about coverage

- AIS here is **broadcast-only archive data** (bundled sample, not the full
  MarineCadastre history). Vessels with transponders off, or without a working
  transponder (**dark vessels**), are absent from the archive and **cannot be
  scored by any correlation pipeline** — this is inherent to broadcast AIS.
- A zero-track window is reported as `NO_RELIABLE_CANDIDATE` (no correlation
  performed) — the system never invents a suspect.
- Live AIS streaming and extended archives are explicitly listed as future work.

## 6. Residual risks

1. Sample archive size (20 rows) bounds the benchmark realism; scaling to
   full archives would need the DuckDB/PostGIS engines already present.
2. Trajectory segmentation assumes broadcast gaps are gaps — vessels that drop
   out mid-corridor produce partial tracks and lower temporal scores (by design,
   surfaced in evidence provenance).