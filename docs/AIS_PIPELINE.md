# MARINeX AIS Pipeline

AIS is used for vessel attribution: filter raw position reports to a spill region
and time window, clean them, build trajectories, and answer spatial/temporal
queries over both DuckDB (local, default) and PostGIS (Docker) backends.

## Layout

```
ml/ais/
├── ais_schema.py     # AISPoint dataclass, validation, cleaning reasons, dedupe
├── trajectory.py     # haversine, segment breaks (gap / speed / end-of-day), Trajectory
├── duckdb_engine.py  # DuckDBAISEngine: partitioned-parquet queries + benchmark
├── postgis_engine.py # PostgISAISEngine: SQL templates against PostGIS
└── prepare_ais.py    # CSV -> partitioned parquet (year=YYYY/month=M/day=D)
```

## Cleaning rules (`AISPoint.validate`)

| Reason | Rule |
|---|---|
| `unknown_mmsi` | mmsi outside valid 9-digit range |
| `bad_coordinates` | lat ∉ [-90,90], lon ∉ [-180,180] |
| `impossible_speed` | speed_knots > 100 |
| `duplicate_timestamp` | deduped per (mmsi, timestamp) |

## Trajectory break rules (`build_trajectories`, default)

- `t_gap_gt_limit` : inter-point gap > `max_gap_minutes` (default 60)
- `speed_anomaly`  : ground speed > `max_speed_knots` (default 60)
- `eod_flush`      : end-of-day flush keeps partition boundaries clean

## Prepare data

```bash
.venv\Scripts\python scripts/prepare_ais.py \
  --input data/samples/sample_ais_trajectories.csv \
  --output data/processed/ais/partitions \
  --region 71.0 71.7 19.0 19.6 \
  --start 2026-03-01T00:00:00Z --end 2026-03-02T00:00:00Z
```

Writes Hive-style partitions `year=2026/month=3/day=1/part_00000.parquet`
(pyarrow). Partitions are bulk data and gitignored.

## Query engine (DuckDB, default)

```python
from ml.ais.duckdb_engine import DuckDBAISEngine

with DuckDBAISEngine("data/processed/ais/partitions") as eng:
    df = eng.query_region(71.0, 71.7, 19.0, 19.6, benchmark=True)
    eng.query_region_time(lon1, lon2, lat1, lat2, t0, t1)
    eng.get_vessels(lon1, lon2, lat1, lat2, t0, t1)
    eng.get_trajectory(636019842)
```

## PostGIS engine

`PostgISAISEngine` holds SQL templates and is exercised through the Docker
PostGIS service (`docker compose up`). Cannot be verified on a SQLite-only box;
templates are syntax-guarded ready for CI.

## Measured benchmark (sample region, REAL)

From `scripts/benchmark_ais.py` → `reports/ais_benchmark.json`:

- 5 vessels in the search window (Mumbai Offshore corridor, 1 day)
- Vessel `636019842`: 7 reports / 1 trajectory line
- All spatial/time queries < 10 ms on the local DuckDB parquet store
- Haversine first leg: 6.964 km

## Tests

`ml/tests/test_ais.py`, `ml/tests/test_duckdb_engine.py` (part of the 19-test ML
suite). DuckDB tests skip cleanly if the partitions are absent.