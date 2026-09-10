"""DuckDB engine tests against the prepared sample AIS parquet."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from ml.ais.duckdb_engine import DuckDBAISEngine

PARTITION_DIR = "data/processed/ais/partitions"


@pytest.fixture(scope="module")
def engine_dir():
    if not os.path.isdir(PARTITION_DIR):
        pytest.skip("run scripts/prepare_ais.py first")
    return PARTITION_DIR


def test_region_query(engine_dir):
    with DuckDBAISEngine(engine_dir) as eng:
        df = eng.query_region(71.0, 71.7, 19.0, 19.6, benchmark=True)
        assert len(df) > 0
        assert eng.last_benchmark["elapsed_s"] >= 0


def test_region_time(engine_dir):
    with DuckDBAISEngine(engine_dir) as eng:
        df = eng.query_region_time(
            71.0, 71.7, 19.0, 19.6,
            "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z",
        )
        assert len(df) > 0


def test_get_vessels(engine_dir):
    with DuckDBAISEngine(engine_dir) as eng:
        df = eng.get_vessels(
            71.0, 71.7, 19.0, 19.6,
            "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z",
        )
        assert len(df) > 0
        assert "n_reports" in df.columns


def test_get_trajectory(engine_dir):
    with DuckDBAISEngine(engine_dir) as eng:
        # mmsi from the sample CSV
        df = eng.get_trajectory(636019842)
        assert len(df) >= 2