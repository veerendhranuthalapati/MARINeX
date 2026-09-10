"""
Phase 11 / 45 benchmark: regional, temporal, spatiotemporal AIS queries via DuckDB.
Writes reports/ais_benchmark.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.ais.duckdb_engine import DuckDBAISEngine
from ml.ais.trajectory import build_trajectories, haversine_km
from ml.ais.prepare_ais import summary_of_prepared


def run(parquet_dir: str = "data/processed/ais/partitions") -> dict:
    prepared = summary_of_prepared(parquet_dir)
    if prepared["partitions"] == 0:
        raise SystemExit(f"No parquet partitions found under {parquet_dir}. Run prepare_ais.py first.")

    bench = {"partitions": prepared["partitions"], "files": prepared["files"], "queries": []}
    with DuckDBAISEngine(parquet_dir) as eng:
        for label, fn in [
            ("region", lambda: eng.query_region(71.0, 71.7, 19.0, 19.6, benchmark=True)),
            ("time", lambda: eng.query_time_range("2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", benchmark=True)),
            ("region_time", lambda: eng.query_region_time(71.0, 71.7, 19.0, 19.6, "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", benchmark=True)),
            ("vessels", lambda: eng.get_vessels(71.0, 71.7, 19.0, 19.6, "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", benchmark=True)),
        ]:
            df = fn()
            bench["queries"].append({"query": label, **eng.last_benchmark})

        # Trajectory benchmark for one vessel + segmentation
        traj_df = eng.get_trajectory(636019842, benchmark=True)
        bench["queries"].append({"query": "trajectory_mmsi_636019842", **eng.last_benchmark})

        points = [_to_point(r) for r in traj_df.to_dict(orient="records") if r["mmsi"] == 636019842]
        trajs = build_trajectories(points)
        t = trajs[636019842]
        seg_len = [len(s) for s in t.segments]
        bench["trajectory"] = {
            "mmsi": 636019842,
            "n_points": t.n_points,
            "n_segments": t.n_segments,
            "segment_lengths": seg_len,
            "linestrings": t.as_linestrings(),
        }
        # sample haversine sanity check
        if t.n_points >= 2:
            a, b = t.points[0], t.points[1]
            bench["haversine_km_first_leg"] = round(
                haversine_km(a.latitude, a.longitude, b.latitude, b.longitude), 3
            )

    os.makedirs("reports", exist_ok=True)
    with open("reports/ais_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(bench, f, indent=2)
    return bench


def _to_point(r: dict) -> "AISPoint":
    from datetime import datetime
    from ml.ais.ais_schema import AISPoint
    return AISPoint(
        mmsi=int(r["mmsi"]),
        imo=None, vessel_name="", vessel_type="", flag="",
        timestamp=datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")),
        latitude=float(r["latitude"]),
        longitude=float(r["longitude"]),
        speed_knots=float(r.get("speed_knots") or -1.0),
        course_deg=float(r.get("course_deg") or -1.0),
        heading_deg=float(r.get("heading_deg") or -1.0),
        nav_status="",
        clean_reason="valid",
    )


if __name__ == "__main__":
    b = run()
    print(json.dumps(b, indent=2, default=str))