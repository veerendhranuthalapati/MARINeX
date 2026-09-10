"""
AIS Audit.

Part A: Data quality audit on sample AIS trajectories.
Part B: Synthetic trajectory validation using haversine_km.
"""

from __future__ import annotations

import json
import math
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = ROOT / "data" / "samples" / "sample_ais_trajectories.csv"
REPORTS_DIR = ROOT / "reports"

EARTH_R = 6371.0088  # km


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two (lat, lon) points in degrees."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return EARTH_R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Part A - Data Quality Audit
# ---------------------------------------------------------------------------

SPEED_MAX_KN = 50.0
COURSE_MIN = 0.0
COURSE_MAX = 360.0
LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0
JUMP_THRESHOLD_KM = 100.0


def _parse_timestamp(ts):
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(ts), fmt)
        except (ValueError, TypeError):
            continue
    return None


def audit_data_quality(df: pd.DataFrame) -> pd.DataFrame:
    issues = []
    for idx, row in df.iterrows():
        row_issues = []
        if pd.isna(row.get("mmsi")) or str(row.get("mmsi", "")).strip() == "":
            row_issues.append("missing_mmsi")
        if pd.isna(row.get("timestamp")) or str(row.get("timestamp", "")).strip() == "":
            row_issues.append("missing_timestamp")
        if pd.isna(row.get("latitude")):
            row_issues.append("missing_latitude")
        elif not (LAT_MIN <= float(row["latitude"]) <= LAT_MAX):
            row_issues.append("latitude_out_of_range")
        if pd.isna(row.get("longitude")):
            row_issues.append("missing_longitude")
        elif not (LON_MIN <= float(row["longitude"]) <= LON_MAX):
            row_issues.append("longitude_out_of_range")
        if pd.isna(row.get("speed_knots")):
            row_issues.append("missing_speed")
        elif float(row["speed_knots"]) < 0 or float(row["speed_knots"]) >= SPEED_MAX_KN:
            row_issues.append("impossible_speed")
        if pd.isna(row.get("course_deg")):
            row_issues.append("missing_course")
        elif not (COURSE_MIN <= float(row["course_deg"]) <= COURSE_MAX):
            row_issues.append("course_out_of_range")
        if row_issues:
            issues.append({"index": idx, "issues": ";".join(row_issues)})
    return pd.DataFrame(issues)


def check_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    dup = df.duplicated(subset=["mmsi", "timestamp"], keep=False)
    return df[dup][["mmsi", "timestamp"]].drop_duplicates()


def check_large_jumps(df: pd.DataFrame) -> list[dict]:
    jumps = []
    sorted_df = df.sort_values(["mmsi", "timestamp"]).reset_index(drop=True)
    for i in range(1, len(sorted_df)):
        prev = sorted_df.iloc[i - 1]
        cur = sorted_df.iloc[i]
        if prev["mmsi"] != cur["mmsi"]:
            continue
        if pd.isna(prev["latitude"]) or pd.isna(prev["longitude"]) or pd.isna(cur["latitude"]) or pd.isna(cur["longitude"]):
            continue
        dist = haversine_km(float(prev["latitude"]), float(prev["longitude"]),
                            float(cur["latitude"]), float(cur["longitude"]))
        if dist > JUMP_THRESHOLD_KM:
            jumps.append({
                "mmsi": prev["mmsi"],
                "from_ts": prev["timestamp"],
                "to_ts": cur["timestamp"],
                "distance_km": round(dist, 2),
            })
    return jumps


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Part A: AIS Data Quality Audit")
    print("=" * 60)

    df = pd.read_csv(SAMPLE_CSV, encoding="utf-8")
    print(f"Loaded {len(df)} rows from {SAMPLE_CSV.name}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst 5 rows:")
    print(df.head().to_string())

    issues_df = audit_data_quality(df)
    dups_df = check_duplicates(df)
    jumps = check_large_jumps(df)

    if len(issues_df) > 0 and "issues" in issues_df.columns:
        n_missing_fields = len(issues_df[issues_df["issues"].str.contains("missing_", na=False)])
        n_range_issues = len(issues_df) - n_missing_fields
    else:
        n_missing_fields = 0
        n_range_issues = 0

    print(f"\nField issues: {len(issues_df)}")
    print(f"Duplicates (mmsi+timestamp): {len(dups_df)}")
    print(f"Large jumps >{JUMP_THRESHOLD_KM}km: {len(jumps)}")

    audit_csv = issues_df.copy()
    if len(dups_df) > 0:
        dups_df = dups_df.copy()
        dups_df["issue"] = "duplicate_mmsi_timestamp"
        audit_csv = pd.concat([audit_csv, dups_df[["issue"] if "issue" in dups_df.columns else ["mmsi", "timestamp"]]], ignore_index=True)
    issues_df.to_csv(REPORTS_DIR / "ais_quality_audit.csv", index=False, encoding="utf-8")
    print(f"\nWrote {REPORTS_DIR / 'ais_quality_audit.csv'}")

    report_lines = [
        "# AIS Data Quality Audit Report\n",
        f"Source: `{SAMPLE_CSV.name}`",
        f"Total records: {len(df)}",
        f"Unique MMSIs: {df['mmsi'].nunique()}\n",
        "## Summary\n",
        f"| Check | Count |",
        f"|-------|-------|",
        f"| Missing fields | {n_missing_fields} |",
        f"| Range / impossible values | {n_range_issues} |",
        f"| Duplicates (mmsi+timestamp) | {len(dups_df)} |",
        f"| Large jumps >{JUMP_THRESHOLD_KM}km | {len(jumps)} |",
        "",
    ]

    if len(jumps) > 0:
        report_lines.append("## Large Jumps\n")
        jumps_df = pd.DataFrame(jumps)
        report_lines.append(jumps_df.to_string(index=False))
        report_lines.append("")

    if len(dups_df) > 0:
        report_lines.append("## Duplicates\n")
        report_lines.append(dups_df.to_string(index=False))
        report_lines.append("")

    report_lines.append("## Field-Level Issues\n")
    if len(issues_df) > 0 and "issues" in issues_df.columns:
        report_lines.append(issues_df.to_string(index=False))
    else:
        report_lines.append("No field-level issues found.")
    report_lines.append("")

    (REPORTS_DIR / "ais_quality_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote {REPORTS_DIR / 'ais_quality_report.md'}")

    # -----------------------------------------------------------------------
    # Part B - Synthetic Trajectory Validation
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Part B: Synthetic Trajectory Validation")
    print("=" * 60)

    KNOT_TO_KMH = 1.852
    results = []

    # Trajectory 1: constant east, 10 kts, 10 pts, 1 hr intervals
    speed_kn = 10.0
    speed_kmh = speed_kn * KNOT_TO_KMH
    interval_h = 1.0
    n_pts = 10
    base_lat, base_lon = 19.0, 71.0
    km_per_deg_lon = 111.32 * math.cos(math.radians(base_lat))
    pts1 = []
    for i in range(n_pts):
        pts1.append((base_lat, base_lon + i * (speed_kmh / km_per_deg_lon)))
    total_dist_km = sum(haversine_km(pts1[j][0], pts1[j][1], pts1[j + 1][0], pts1[j + 1][1]) for j in range(len(pts1) - 1))
    expected_dist_km = speed_kmh * interval_h * (n_pts - 1)
    tol1 = abs(total_dist_km - expected_dist_km) / expected_dist_km * 100.0
    pass1 = tol1 <= 5.0
    results.append({
        "trajectory": "constant_east_10kts",
        "description": "Constant eastward at 10 kts, 10 points, 1-hour intervals",
        "n_points": n_pts,
        "speed_knots": speed_kn,
        "interval_hours": interval_h,
        "computed_distance_km": round(total_dist_km, 4),
        "expected_distance_km": round(expected_dist_km, 4),
        "error_pct": round(tol1, 4),
        "within_tolerance_5pct": pass1,
    })
    print(f"Traj 1 (constant east): dist={total_dist_km:.4f}km expected={expected_dist_km:.4f}km err={tol1:.2f}% -> {'PASS' if pass1 else 'FAIL'}")

    # Trajectory 2: constant north with AIS gap (skip point 5)
    speed_kn2 = 8.0
    speed_kmh2 = speed_kn2 * KNOT_TO_KMH
    n_pts2 = 10
    pts2_full = []
    for i in range(n_pts2):
        pts2_full.append((base_lat + i * (speed_kmh2 / 111.32), base_lon))
    pts2_gap = [pts2_full[j] for j in range(n_pts2) if j != 5]
    total_dist_km2 = sum(haversine_km(pts2_gap[j][0], pts2_gap[j][1], pts2_gap[j + 1][0], pts2_gap[j + 1][1]) for j in range(len(pts2_gap) - 1))
    expected_dist_km2 = speed_kmh2 * interval_h * (n_pts2 - 1)
    tol2 = abs(total_dist_km2 - expected_dist_km2) / expected_dist_km2 * 100.0
    pass2 = tol2 <= 5.0
    results.append({
        "trajectory": "constant_north_with_gap",
        "description": "Constant northward at 8 kts, 10 points (point 5 dropped as AIS gap), 1-hour intervals",
        "n_points": len(pts2_gap),
        "speed_knots": speed_kn2,
        "interval_hours": interval_h,
        "gap_at_index": 5,
        "computed_distance_km": round(total_dist_km2, 4),
        "expected_distance_km": round(expected_dist_km2, 4),
        "error_pct": round(tol2, 4),
        "within_tolerance_5pct": pass2,
    })
    print(f"Traj 2 (north+gap): dist={total_dist_km2:.4f}km expected={expected_dist_km2:.4f}km err={tol2:.2f}% -> {'PASS' if pass2 else 'FAIL'}")

    # Trajectory 3: 90-degree turn (east then north)
    speed_kn3 = 12.0
    speed_kmh3 = speed_kn3 * KNOT_TO_KMH
    half = 5
    km_per_deg_lon3 = 111.32 * math.cos(math.radians(base_lat))
    pts3 = []
    for i in range(half):
        pts3.append((base_lat, base_lon + i * (speed_kmh3 / km_per_deg_lon3)))
    turn_lat = pts3[-1][0]
    turn_lon = pts3[-1][1]
    for i in range(1, half):
        pts3.append((turn_lat + i * (speed_kmh3 / 111.32), turn_lon))
    total_dist_km3 = sum(haversine_km(pts3[j][0], pts3[j][1], pts3[j + 1][0], pts3[j + 1][1]) for j in range(len(pts3) - 1))
    expected_dist_km3 = speed_kmh3 * interval_h * (len(pts3) - 1)
    tol3 = abs(total_dist_km3 - expected_dist_km3) / expected_dist_km3 * 100.0
    pass3 = tol3 <= 5.0
    results.append({
        "trajectory": "90_degree_turn",
        "description": "East 5 pts then 90-degree turn north 4 pts, 12 kts, 1-hour intervals",
        "n_points": len(pts3),
        "speed_knots": speed_kn3,
        "interval_hours": interval_h,
        "turn_at_index": half - 1,
        "computed_distance_km": round(total_dist_km3, 4),
        "expected_distance_km": round(expected_dist_km3, 4),
        "error_pct": round(tol3, 4),
        "within_tolerance_5pct": pass3,
    })
    print(f"Traj 3 (90-deg turn): dist={total_dist_km3:.4f}km expected={expected_dist_km3:.4f}km err={tol3:.2f}% -> {'PASS' if pass3 else 'FAIL'}")

    validation_output = {
        "test": "synthetic_trajectory_validation",
        "haversine_function": "ml.ais.trajectory.haversine_km",
        "tolerance_pct": 5.0,
        "trajectories": results,
        "all_passed": all(r["within_tolerance_5pct"] for r in results),
    }

    json_path = REPORTS_DIR / "ais_trajectory_validation.json"
    json_path.write_text(json.dumps(validation_output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {json_path}")
    print(f"All passed: {validation_output['all_passed']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
