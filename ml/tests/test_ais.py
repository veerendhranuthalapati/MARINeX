"""Tests for the AIS pipeline: schema validation, trajectories, DuckDB engine."""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from datetime import datetime, timezone

import numpy as np

from ml.ais.ais_schema import AISPoint, clean_points, dedupe_by_timestamp
from ml.ais.trajectory import build_trajectories, haversine_km
from ml.ais.prepare_ais import prepare_ais_parquet, summary_of_prepared


def _pt(mmsi, lat, lon, ts, speed=10.0, clean="valid"):
    return AISPoint(
        mmsi=mmsi, imo=None, timestamp=datetime.fromisoformat(ts), latitude=lat,
        longitude=lon, speed_knots=speed, clean_reason=clean,
    )


def test_haversine_sanity():
    # ~111 km per degree of latitude.
    d = haversine_km(0.0, 0.0, 1.0, 0.0)
    assert 110.0 < d < 112.0


def test_validation_flags():
    bad = _pt(123456789, 200.0, 0.0, "2026-03-01T00:00:00Z")
    assert AISPoint.validate(bad) == "bad_coordinates"
    bad_speed = _pt(123456789, 10.0, 10.0, "2026-03-01T00:00:00Z", speed=999.0)
    assert AISPoint.validate(bad_speed) == "impossible_speed"


def test_dedupe_by_timestamp():
    a = _pt(123456789, 10.0, 10.0, "2026-03-01T00:00:00Z")
    b = _pt(123456789, 10.1, 10.1, "2026-03-01T00:00:00Z")
    out = dedupe_by_timestamp([a, b])
    assert sum(1 for p in out if p.clean_reason == "duplicate_timestamp") == 1


def test_trajectory_gap_break():
    # Consecutive positions must stay under max_speed (60 kn) when not gapped.
    pts = [
        _pt(123456789, 10.00, 10.00, "2026-03-01T00:00:00Z"),
        _pt(123456789, 10.05, 10.05, "2026-03-01T00:10:00Z"),  # ~7km in 10min = ~22kn
        _pt(123456789, 20.00, 20.00, "2026-03-02T00:00:00Z"),  # 23h50m gap
        _pt(123456789, 20.05, 20.05, "2026-03-02T00:10:00Z"),
    ]
    trajs = build_trajectories(pts, max_gap_minutes=60)
    t = trajs[123456789]
    assert t.n_segments == 2
    assert any("t_gap_gt_limit" in s for s in t.step_log)
    assert t.as_linestrings()[0][0] == (10.0, 10.0)


def test_prepare_sample_parquet(tmp_path):
    src = "data/samples/sample_ais_trajectories.csv"
    out = prepare_ais_parquet(
        src, str(tmp_path),
        lon_min=71.0, lon_max=71.7, lat_min=19.0, lat_max=19.6,
        start="2026-03-01T00:00:00Z", end="2026-03-02T00:00:00Z",
    )
    assert out["rows_written"] > 0
    info = summary_of_prepared(str(tmp_path))
    assert info["partitions"] >= 1
    # Partition directories year=2026/month=3/day=1 present
    assert os.path.isdir(os.path.join(str(tmp_path), "year=2026", "month=3", "day=1"))