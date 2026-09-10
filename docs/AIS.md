# MARINeX AIS Pipeline & Data Quality (SIH26143)

AIS is the vessel-truth source for the candidate search window. This document
describes the provider pipeline, the audit tooling, the verified quality
findings, and an honest statement about coverage limits.

## 1. Pipeline

- **Provider**: `CSVAISProvider` (`backend/app/services/ais/csv_provider.py`)
  parses MarineCadastre-style historical position-report CSVs (columns: mmsi,
  imo, vessel_name, vessel_type, flag, timestamp, latitude, longitude,
  speed_knots, course_deg, heading_deg, nav_status - see
  `data/samples/sample_ais_trajectories.csv`).
- **Corridor queries**: `query_vessels(bounding_box, start_time, end_time)`
  filters vessels by spatial bbox and temporal window (the drift-hindcast search
  corridor).
- **Trajectory windowing**: `get_vessel_trajectory(vessel_id)` reconstructs a
  sorted breadcrumb track within the window for each scanned vessel. The ML/AIS
  layer (manifested `ml/ais/`) provides schema validation, cleaning
  (`bad_coordinates`, `impossible_speed`, `course_out_of_range`), dedupe, and
  gap-aware trajectory segmentation.
- A velocity-agnostic reference implementation of the haversine distance and
  trajectory math is in `ml/ais/trajectory.py`.

The backend also ships `MockAISProvider` for deterministic integration tests;
only the CSV provider is used in the demo/incident paths.

## 2. Audit Script

`scripts/ais_audit.py` performs:

- **Part A - data-quality audit** on `data/samples/sample_ais_trajectories.csv`
  (20 records, 5 unique MMSIs):
  - missing-field detection (mmsi, timestamp, lat/lon, speed, course)
  - range / impossible-value checks (speed >= 50 kn, lat/lon bounds, course 0-360)
  - duplicate detection on `(mmsi, timestamp)`
  - large-jump detection (consecutive fixes > 100 km)
- **Part B - synthetic trajectory validation** with `haversine_km` to confirm the
  distance math is correct:
  - constant east at 10 kn, 10 points, 1 h intervals
  - constant north with an AIS gap (point 5 dropped)
  - 90-degree turn (east then north)

## 3. Findings (verified)

| Check | Result |
|---|---|
| Missing fields | 0 |
| Range / impossible values | 0 |
| Duplicates (mmsi+timestamp) | 0 |
| Large jumps > 100 km | 0 |
| Trajectory east/north/turn validation | ALL PASS (error ~0.112%) |

Artifacts:

- `reports/ais_quality_audit.csv` - field-level issue rows (empty in the clean run)
- `reports/ais_quality_report.md` - human-readable audit summary
- `reports/ais_trajectory_validation.json` - synthetic east / north+gap /
  90-degree-turn validation (`all_passed: true`, tolerance 5%, observed error
  ~0.112%)

## 4. Honesty About Coverage

- **AIS is broadcast-only**: the data consists of archived AIS position reports
  transmitted by vessels. Vessels that switch off, or operate without a working
  transponder (so-called **dark vessels**), are simply absent from the archive
  and therefore **uncatalogued** - they cannot be scored by this pipeline.
- A zero-track result in a search window is reported honestly as
  `NO_RELIABLE_CANDIDATE` (no correlation performed), rather than inventing a
  suspect.
- The local repository holds the bundled sample archive, **not** the full
  MarineCadastre history; live AIS streaming integration is future work.

## References

- `backend/app/services/ais/csv_provider.py` - CSV provider
- `scripts/ais_audit.py` - audit + trajectory validation
- `ml/ais/` - schema, trajectory math, DuckDB/PostGIS engines
- `reports/ais_quality_audit.csv`, `reports/ais_quality_report.md`,
  `reports/ais_trajectory_validation.json`
- `docs/AIS_PIPELINE.md` - ML-layer AIS pipeline documentation