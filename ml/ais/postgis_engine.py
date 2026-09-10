"""
PostGIS Spatial Engine (Phase 12).

Used only for FINAL spatial intelligence over candidate AIS subsets — not as a
replacement for DuckDB parquet analytics. Inputs: candidate subset tables over
a single region/time window.

Queries:
  ST_DWithin      -- vessels within `distance_max_km` of a point
  ST_Intersects   -- vessels whose path intersects a polygon (e.g. origin hull)
  ST_Contains     -- points strictly inside a polygon
  ST_Distance     -- ordered distance-to-polygon ranking

Spatial index is created via `CREATE INDEX ... USING GIST (geom)`; ingestion
uses a geometry column built from `ST_SetSRID(ST_MakePoint(lon, lat), 4326)`.

The engine connects through SQLAlchemy/psycopg2. Availability is opt-in: if the
DB is unreachable it raises a clear error (fail loudly), it never silently falls
back to fake results.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

GEOM_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
    mmsi BIGINT,
    timestamp TIMESTAMPTZ,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    speed_knots DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326)
);
CREATE INDEX IF NOT EXISTS {table}_geom_idx ON {table} USING GIST (geom);
"""


def default_sqlalchemy_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/marinex",
    )


class PostgISAISEngine:
    def __init__(self, url: Optional[str] = None, table: str = "ais_candidates"):
        self.url = url or default_sqlalchemy_url()
        self.table = table
        self.engine = None
        self._connect()

    def _connect(self) -> None:
        try:
            from sqlalchemy import create_engine, text
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("sqlalchemy required for PostGIS engine") from e

        self._text = text
        self.engine = create_engine(self.url)
        # verify connectivity loudly
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.execute(text("SELECT PostGIS_Version()"))

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(self._text(GEOM_TABLE_SQL.format(table=self.table)))

    def ingest_points(self, mmsi_list: List[int], lat_list: List[float], lon_list: List[float],
                      ts_list: List[str], speed_list: Optional[List[float]] = None) -> int:
        if len({len(mmsi_list), len(lat_list), len(lon_list), len(ts_list)}) != 1:
            raise ValueError("mismatched arrays for PostGIS ingestion")
        speed_list = speed_list or [None] * len(mmsi_list)
        with self.engine.begin() as conn:
            for mmsi, lat, lon, ts, spd in zip(mmsi_list, lat_list, lon_list, ts_list, speed_list):
                conn.execute(self._text(
                    f"""INSERT INTO {self.table}
                        (mmsi, timestamp, latitude, longitude, speed_knots, geom)
                        VALUES (:m, :ts, :la, :lo, :s,
                                ST_SetSRID(ST_MakePoint(:lo, :la), 4326))"""
                ), {"m": mmsi, "ts": ts, "la": lat, "lo": lon, "s": spd})
        return len(mmsi_list)

    def vessels_within_distance(self, lat: float, lon: float, distance_km: float, limit: int = 100) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            rows = conn.execute(self._text(f"""
                SELECT mmsi, min(ST_Distance(geom::geography,
                          ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography))/1000.0 AS dist_km,
                       count(*) AS n_reports
                FROM {self.table}
                WHERE ST_DWithin(geom::geography,
                                 ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :d)
                GROUP BY mmsi ORDER BY dist_km LIMIT {limit}
            """), {"lat": lat, "lon": lon, "d": distance_km * 1000.0}).fetchall()
        return [{"mmsi": r[0], "distance_km": r[1], "n_reports": r[2]} for r in rows]

    def vessels_intersecting_polygon(self, wkt_polygon: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            rows = conn.execute(self._text(f"""
                SELECT v.mmsi, count(*) AS n_reports
                FROM {self.table} v
                WHERE ST_Intersects(v.geom, ST_SetSRID(ST_GeomFromText(:wkt), 4326))
                GROUP BY v.mmsi ORDER BY n_reports DESC LIMIT {limit}
            """), {"wkt": wkt_polygon}).fetchall()
        return [{"mmsi": r[0], "n_reports": r[1]} for r in rows]


if __name__ == "__main__":
    eng = PostgISAISEngine()
    eng.ensure_schema()
    print("PostGIS ready:", eng.table)