"""
AIS Preparation: CSV -> validated -> partitioned Parquet (Phase 10).

Reads raw AIS CSV sources, applies the schema validation from ais_schema
(reasons recorded, nothing silently deleted), filters by region + time window,
and writes partitioned Parquet by year/month/day.

This is the primary entry point for turning a potentially huge national AIS
archive into a lean, queryable analytical dataset. The archive itself is never
loaded entirely into RAM: rows are streamed with pandas chunking.
"""

from __future__ import annotations

import os
import json
from typing import Callable, List, Optional

import pandas as pd

from ml.ais.ais_schema import AIS_SCHEMA, clean_points
from ml.ais.ais_schema import AISPoint
from ml.ais.trajectory import build_trajectories

CHUNK = 200_000


def prepare_ais_parquet(
    input_csv: str,
    output_dir: str,
    lon_min: Optional[float] = None,
    lon_max: Optional[float] = None,
    lat_min: Optional[float] = None,
    lat_max: Optional[float] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_rows: Optional[int] = None,
) -> dict:
    """Convert an AIS CSV into year/month/day-partitioned Parquet.

    Returns a summary dict with row counts and cleaning statistics.
    """
    from collections import Counter

    os.makedirs(output_dir, exist_ok=True)
    total_written = 0
    total_filtered = 0
    clean_counter: Counter[str] = Counter()
    cleaning_log: List[dict] = []

    start_ts = pd.Timestamp(start, tz="UTC") if start else None
    end_ts = pd.Timestamp(end, tz="UTC") if end else None

    for i, chunk in enumerate(pd.read_csv(input_csv, chunksize=CHUNK, encoding="utf-8-sig")):
        raw_rows = chunk.to_dict(orient="records")
        if max_rows and total_written >= max_rows:
            break

        # Apply region/time pre-filter at the dataframe level BEFORE parsing.
        df = chunk
        if lon_min is not None:
            df = df[(df["longitude"] >= lon_min) & (df["longitude"] <= (lon_max or 180.0))]
        if lat_min is not None:
            df = df[(df["latitude"] >= lat_min) & (df["latitude"] <= (lat_max or 90.0))]
        if start_ts is not None:
            df = df[pd.to_datetime(df["timestamp"], utc=True) >= start_ts]
        if end_ts is not None:
            df = df[pd.to_datetime(df["timestamp"], utc=True) < end_ts]
        total_filtered += len(df)

        points, log = clean_points(df.to_dict(orient="records"), source_file=input_csv)
        cleaning_log.extend(log)
        for p in points:
            clean_counter[p.clean_reason] += 1

        if not points:
            continue

        records = [p.to_row(input_csv) for p in points]
        part_df = pd.DataFrame(records, columns=AIS_SCHEMA)
        part_df["timestamp"] = pd.to_datetime(part_df["timestamp"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        part_df["year"] = pd.to_datetime(part_df["timestamp"], utc=True).dt.year
        part_df["month"] = pd.to_datetime(part_df["timestamp"], utc=True).dt.month
        part_df["day"] = pd.to_datetime(part_df["timestamp"], utc=True).dt.day

        keys = ["year", "month", "day"]
        groups = list(part_df.groupby(keys, sort=True))
        for part_key, g in groups:
            sub = output_dir.rstrip("/\\")
            for k_name, k_val in zip(keys, part_key):
                sub = os.path.join(sub, f"{k_name}={k_val}")
            os.makedirs(sub, exist_ok=True)
            fname = os.path.join(sub, f"part_{i:05d}.parquet")
            usecols = [c for c in AIS_SCHEMA]
            g[usecols].to_parquet(fname, index=False)
            total_written += len(g)

        if total_written >= (max_rows or 0) > 0:
            break

    summary = {
        "input_csv": os.path.abspath(input_csv),
        "output_dir": os.path.abspath(output_dir),
        "rows_after_filter": total_filtered,
        "rows_written": total_written,
        "cleaning": dict(clean_counter),
        "cleaning_log": cleaning_log,
    }
    return summary


def summary_of_prepared(output_dir: str) -> dict:
    """Report the number of parquet partitions for the benchmark UI."""
    files = []
    for root, _, names in os.walk(output_dir):
        for n in names:
            if n.endswith(".parquet"):
                files.append(os.path.join(root, n))
    return {
        "parquet_dir": os.path.abspath(output_dir),
        "partitions": len(files),
        "files": files,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/samples/sample_ais_trajectories.csv")
    ap.add_argument("--output", default="data/processed/ais/partitions")
    args = ap.parse_args()
    s = prepare_ais_parquet(args.input, args.output)
    print(json.dumps(s, indent=2, default=str))