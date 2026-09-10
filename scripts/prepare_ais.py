"""
AIS Preparation CLI — filter a (large) AIS source to a bounded region/time window
and write it as year/month/day partitioned Parquet.

Example (matches docs/AIS_PIPELINE.md):
  python scripts/prepare_ais.py \
      --input  data/raw/ais/india_2026.csv \
      --output data/processed/ais/partitions \
      --region 71.0,71.7,19.0,19.6 \
      --start 2026-03-01T00:00:00Z \
      --end   2026-03-02T00:00:00Z
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    ap = argparse.ArgumentParser(description="MARINeX AIS CSV -> filtered partitioned Parquet")
    ap.add_argument("--input", required=True, help="source AIS CSV")
    ap.add_argument("--output", default="data/processed/ais/partitions", help="parquet output dir")
    ap.add_argument("--region", default=None,
                    help="lon_min,lon_max,lat_min,lat_max (e.g. 71.0,71.7,19.0,19.6)")
    ap.add_argument("--start", default=None, help="ISO8601 start timestamp (UTC)")
    ap.add_argument("--end", default=None, help="ISO8601 end timestamp (UTC)")
    ap.add_argument("--max-rows", type=int, default=None, help="stop after N rows (testing)")
    ap.add_argument("--json", action="store_true", help="print summary as JSON")
    args = ap.parse_args()

    from ml.ais.prepare_ais import prepare_ais_parquet

    region = args.region.split(",") if args.region else None
    if region:
        region = [float(r) for r in region]
        if len(region) != 4:
            raise SystemExit("--region must be lon_min,lon_max,lat_min,lat_max")

    summary = prepare_ais_parquet(
        input_csv=args.input,
        output_dir=args.output,
        lon_min=region[0] if region else None,
        lon_max=region[1] if region else None,
        lat_min=region[2] if region else None,
        lat_max=region[3] if region else None,
        start=args.start,
        end=args.end,
        max_rows=args.max_rows,
    )

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print(f"filtered rows: {summary['rows_after_filter']}")
        print(f"written rows:  {summary['rows_written']}")
        print(f"cleaning:      {summary['cleaning']}")
        print(f"partitions:    {summary['output_dir']}")


if __name__ == "__main__":
    main()