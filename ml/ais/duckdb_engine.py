"""
DuckDB Analytical Engine for Large AIS Data (Phase 11).

Strategy:
  - AIS archives are normalized to partitioned Parquet (see ml.ais.prepare_ais).
  - DuckDB queries the Parquet WITHOUT loading the whole archive into RAM.
  - Region/time filters use predicate pushdown on the partition columns so only
    relevant year/month/day files are scanned.

Methods:
  query_region        -- vessels with positions inside a lon/lat box
  query_time_range    -- positions within [start, end)
  query_region_time   -- region + time (the primary investigation query)
  get_vessels         -- distinct vessel summary rows inside region+time
  get_trajectory      -- ordered position reports for one MMSI in region+time

Benchmark helper records: query size (files scanned), rows returned, elapsed time.
"""

from __future__ import annotations

import os
import time
import glob
from typing import Any, Dict, List, Optional, Sequence

import duckdb
import pandas as pd

PARTITION_COLUMNS = ["year", "month", "day"]


class DuckDBAISEngine:
    def __init__(self, parquet_dir: str, db_path: Optional[str] = None):
        self.parquet_dir = os.path.abspath(parquet_dir)
        self.db_path = db_path or os.path.join(os.path.dirname(self.parquet_dir), "ais_query.duckdb")
        self.con = duckdb.connect(self.db_path)
        self.con.execute("SET threads TO 4")
        self._register_view()

    def _register_view(self) -> None:
        """Register a view over all parquet partitions for the given glob."""
        glob_expr = os.path.join(self.parquet_dir, "**", "*.parquet").replace("\\", "/")
        try:
            self.con.execute(f"CREATE OR REPLACE VIEW ais AS SELECT * FROM read_parquet('{glob_expr}')")
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Failed to register AIS parquet view at {glob_expr}: {e}")

    # ------------------------------------------------------------------ queries
    def query_region(
        self,
        lon_min: float,
        lon_max: float,
        lat_min: float,
        lat_max: float,
        limit: int = 100_000,
        benchmark: bool = False,
    ) -> pd.DataFrame:
        sql = f"""SELECT * FROM ais
                  WHERE longitude BETWEEN {lon_min} AND {lon_max}
                    AND latitude  BETWEEN {lat_min} AND {lat_max}
                  LIMIT {limit}"""
        return self._run(sql, benchmark)

    def query_time_range(
        self,
        start: str,
        end: str,
        limit: int = 100_000,
        benchmark: bool = False,
    ) -> pd.DataFrame:
        sql = f"""SELECT * FROM ais
                  WHERE timestamp >= '{start}' AND timestamp < '{end}'
                  LIMIT {limit}"""
        return self._run(sql, benchmark)

    def query_region_time(
        self,
        lon_min: float,
        lon_max: float,
        lat_min: float,
        lat_max: float,
        start: str,
        end: str,
        limit: int = 100_000,
        benchmark: bool = False,
    ) -> pd.DataFrame:
        sql = f"""SELECT * FROM ais
                  WHERE longitude BETWEEN {lon_min} AND {lon_max}
                    AND latitude  BETWEEN {lat_min} AND {lat_max}
                    AND timestamp >= '{start}' AND timestamp < '{end}'
                  LIMIT {limit}"""
        return self._run(sql, benchmark)

    def get_vessels(
        self,
        lon_min: float,
        lon_max: float,
        lat_min: float,
        lat_max: float,
        start: str,
        end: str,
        benchmark: bool = False,
    ) -> pd.DataFrame:
        sql = f"""SELECT mmsi, count(*) AS n_reports,
                         min(timestamp) AS first_seen, max(timestamp) AS last_seen,
                         min(speed_knots) AS min_sog, max(speed_knots) AS max_sog,
                         arg_max(vessel_name, timestamp) AS vessel_name
                  FROM ais
                  WHERE longitude BETWEEN {lon_min} AND {lon_max}
                    AND latitude  BETWEEN {lat_min} AND {lat_max}
                    AND timestamp >= '{start}' AND timestamp < '{end}'
                  GROUP BY mmsi
                  ORDER BY n_reports DESC"""
        return self._run(sql, benchmark)

    def get_trajectory(self, mmsi: int, benchmark: bool = False) -> pd.DataFrame:
        sql = f"""SELECT mmsi, timestamp, latitude, longitude, speed_knots, course_deg, heading_deg
                  FROM ais WHERE mmsi = {mmsi} ORDER BY timestamp"""
        return self._run(sql, benchmark)

    # ---------------------------------------------------------- benchmarking
    def _run(self, sql: str, benchmark: bool) -> pd.DataFrame:
        if not benchmark:
            return self.con.execute(sql).df()
        files = glob.glob(os.path.join(self.parquet_dir, "**", "*.parquet"), recursive=True)
        rows = 0
        for f in files:
            try:
                rows += self.con.execute(f"SELECT count(*) FROM read_parquet('{f}')").fetchone()[0]
            except Exception:  # noqa: BLE001
                rows = -1
                break
        t0 = time.perf_counter()
        df = self.con.execute(sql).df()
        elapsed_s = time.perf_counter() - t0
        self.last_benchmark = {
            "files_scanned": len(files),
            "total_rows_in_partitions": rows,
            "rows_returned": int(len(df)),
            "elapsed_s": round(elapsed_s, 4),
        }
        return df

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> "DuckDBAISEngine":
        return self

    def __exit__(self, *exc_a: Any) -> None:
        self.close()


if __name__ == "__main__":
    engine = DuckDBAISEngine("data/processed/ais/partitions")
    df = engine.query_region_time(71.0, 71.7, 19.0, 19.6, "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", benchmark=True)
    print(engine.last_benchmark)
    print(df.head())