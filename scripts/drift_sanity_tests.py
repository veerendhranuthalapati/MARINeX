r"""Drift Sanity Tests, Determinism Check & Sensitivity Analysis (Phases 14-16).

Usage:
    .venv/Scripts/python scripts/drift_sanity_tests.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.services.drift.service import MockDriftService
from app.schemas.drift import DriftSimulationRequest

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

CENTROID = [71.5, 19.35]
START_TIME = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def run_sim(svc, duration_hours, wind_u, wind_v, current_u, current_v, centroid=None, start_time=None):
    req = DriftSimulationRequest(
        duration_hours=duration_hours,
        direction="HINDCAST",
        time_step_seconds=900,
        num_particles=200,
    )
    return svc.simulate(
        slick_id="test_slick",
        centroid=centroid or CENTROID,
        start_time=start_time or START_TIME,
        req=req,
        wind_u=wind_u,
        wind_v=wind_v,
        current_u=current_u,
        current_v=current_v,
    )


def physics_sanity(svc):
    results = {}
    tests = [
        ("eastward_current", 0.5, 0.0, "origin_west_of_centroid"),
        ("westward_current", -0.5, 0.0, "origin_east_of_centroid"),
        ("northward_current", 0.0, 0.5, "origin_south_of_centroid"),
        ("southward_current", 0.0, -0.5, "origin_north_of_centroid"),
        ("zero_forcing", 0.0, 0.0, "origin_near_centroid"),
    ]
    for name, cu, cv, check in tests:
        resp = run_sim(svc, 24.0, 0.0, 0.0, cu, cv)
        ox, oy = resp.probable_origin_centroid
        cx, cy = CENTROID
        dist = haversine_km(cy, cx, oy, ox)

        if check == "origin_west_of_centroid":
            passed = ox < cx
            detail = f"origin_lon={ox:.5f} < centroid_lon={cx:.5f}"
        elif check == "origin_east_of_centroid":
            passed = ox > cx
            detail = f"origin_lon={ox:.5f} > centroid_lon={cx:.5f}"
        elif check == "origin_south_of_centroid":
            passed = oy < cy
            detail = f"origin_lat={oy:.5f} < centroid_lat={cy:.5f}"
        elif check == "origin_north_of_centroid":
            passed = oy > cy
            detail = f"origin_lat={oy:.5f} > centroid_lat={cy:.5f}"
        else:
            passed = dist < 5.0
            detail = f"drift_distance={dist:.3f} km < 5 km"

        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] Physics: {name} -- {detail} (drift={dist:.3f} km)")
        results[name] = {
            "origin_centroid": [ox, oy],
            "drift_distance_km": round(dist, 4),
            "diffusion_radius_km": resp.uncertainty.get("diffusion_radius_km", 0),
            "passed": passed,
        }
    return results


def determinism_test(svc):
    r1 = run_sim(svc, 24.0, 0.1, -0.05, 0.3, 0.1)
    r2 = run_sim(svc, 24.0, 0.1, -0.05, 0.3, 0.1)
    same_centroid = r1.probable_origin_centroid == r2.probable_origin_centroid
    same_uncertainty = r1.uncertainty == r2.uncertainty
    passed = same_centroid and same_uncertainty
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] Determinism: same inputs -> same outputs (centroid={same_centroid}, uncertainty={same_uncertainty})")
    return {
        "run1_origin": r1.probable_origin_centroid,
        "run2_origin": r2.probable_origin_centroid,
        "same_centroid": same_centroid,
        "same_uncertainty": same_uncertainty,
        "passed": passed,
    }


def sensitivity_analysis(svc):
    rows = []
    base_wind_u, base_wind_v = 0.1, -0.05
    base_cur_u, base_cur_v = 0.3, 0.1
    base_duration = 24.0

    def record(scenario, param, value, resp):
        ox, oy = resp.probable_origin_centroid
        dist = haversine_km(CENTROID[1], CENTROID[0], oy, ox)
        diff_r = resp.uncertainty.get("diffusion_radius_km", 0)
        rows.append({
            "scenario": scenario,
            "parameter": param,
            "value": value,
            "origin_lon": round(ox, 5),
            "origin_lat": round(oy, 5),
            "drift_distance_km": round(dist, 4),
            "diffusion_radius_km": round(diff_r, 4),
        })

    for dur in [12.0, 24.0, 36.0]:
        resp = run_sim(svc, dur, base_wind_u, base_wind_v, base_cur_u, base_cur_v)
        record("duration_sweep", "duration_hours", dur, resp)

    for wu_mod, wv_mod in [(0.5, 1.0), (0.5, -1.0), (1.5, 1.0), (1.5, -1.0)]:
        wu = base_wind_u * wu_mod
        wv = base_wind_v * wv_mod
        resp = run_sim(svc, base_duration, wu, wv, base_cur_u, base_cur_v)
        record("wind_uncertainty", f"wind=({wu:.4f},{wv:.4f})", f"{wu_mod:.1f}x/{wv_mod:.1f}x", resp)

    for cu_mod, cv_mod in [(0.5, 1.0), (0.5, -1.0), (1.5, 1.0), (1.5, -1.0)]:
        cu = base_cur_u * cu_mod
        cv = base_cur_v * cv_mod
        resp = run_sim(svc, base_duration, base_wind_u, base_wind_v, cu, cv)
        record("current_uncertainty", f"current=({cu:.4f},{cv:.4f})", f"{cu_mod:.1f}x/{cv_mod:.1f}x", resp)

    for dx, dy in [(-0.01, 0.0), (0.01, 0.0), (0.0, -0.01), (0.0, 0.01)]:
        c = [CENTROID[0] + dx, CENTROID[1] + dy]
        resp = run_sim(svc, base_duration, base_wind_u, base_wind_v, base_cur_u, base_cur_v, centroid=c)
        record("position_sensitivity", f"offset=({dx:+.3f},{dy:+.3f})", f"{dx},{dy}", resp)

    return rows


def main() -> int:
    svc = MockDriftService()

    print("=" * 60)
    print("A. Physics Sanity Tests (constant currents, no wind)")
    print("=" * 60)
    physics_results = physics_sanity(svc)

    print("\n" + "=" * 60)
    print("B. Determinism Test")
    print("=" * 60)
    determinism_results = determinism_test(svc)

    print("\n" + "=" * 60)
    print("C. Sensitivity Analysis")
    print("=" * 60)
    sensitivity_rows = sensitivity_analysis(svc)
    print(f"  Generated {len(sensitivity_rows)} sensitivity scenarios")

    all_results = {
        "physics_sanity": physics_results,
        "determinism": determinism_results,
        "sensitivity_summary": {
            "num_scenarios": len(sensitivity_rows),
            "centroid": CENTROID,
            "start_time": START_TIME.isoformat(),
        },
    }

    out_json = REPORTS / "drift_sanity_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nWrote {out_json}")

    out_csv = REPORTS / "drift_sensitivity.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "parameter", "value",
                                                "origin_lon", "origin_lat",
                                                "drift_distance_km", "diffusion_radius_km"])
        writer.writeheader()
        writer.writerows(sensitivity_rows)
    print(f"Wrote {out_csv}")

    all_passed = all(r["passed"] for r in physics_results.values()) and determinism_results["passed"]
    print(f"\nOverall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
