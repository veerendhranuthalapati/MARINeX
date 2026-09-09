"""
Standalone CLI Pipeline Runner for MARINeX (SIH26143).
Executes the full pipeline:
  Scene -> Detection -> Characterization -> Environmental Retrieval -> Drift Hindcast -> AIS Trajectory Correlation -> Vessel Attribution -> Report
Usage:
    python scripts/run_pipeline_cli.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.database import SessionLocal, init_db
from app.api.v1.demo import run_end_to_end_demo
from app.core.logging import setup_logging


def main():
    setup_logging()
    init_db()
    db = SessionLocal()
    try:
        print("=" * 70)
        print("  MARINeX: Satellite Oil Spill Detection & AIS Attribution (SIH26143)")
        print("=" * 70)
        print("\n[+] Triggering full automated end-to-end pipeline...")

        summary = run_end_to_end_demo(db)

        print("\n" + "-" * 70)
        print("PIPELINE EXECUTION SUMMARY")
        print("-" * 70)
        print(f"Status              : {summary['status'].upper()}")
        print(f"Pipeline Stages     : {summary['pipeline']}")
        print(f"Detected Slick ID   : {summary['slick_id']}")
        print(f"Slick Footprint Area: {summary['slick_area_km2']:.2f} km^2")
        print(f"Vessels Scanned     : {summary['candidate_count']}")
        print(f"Primary Suspect     : {summary['primary_suspect']}")
        print(f"Evidence Score      : {summary['primary_suspect_score']:.1f} / 100")
        print(f"Investigation Report: {summary['report_id']}")
        print("-" * 70)
        print("\n[OK] Success: Full pipeline executed without error.\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
