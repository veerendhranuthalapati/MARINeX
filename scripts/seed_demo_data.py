"""
CLI Seed Script: Populates database with the SIH26143 Mumbai Offshore SAR Demo Scenario.
Usage:
    python scripts/seed_demo_data.py
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.database import SessionLocal, init_db
from app.api.v1.demo import seed_demo_data
from app.core.logging import setup_logging, logger


def main():
    setup_logging()
    logger.info("Initializing database...")
    init_db()

    db = SessionLocal()
    try:
        logger.info("Seeding SIH26143 demo scenario (Sentinel-1 SAR + AIS Traffic + Slick)...")
        result = seed_demo_data(db)
        logger.info(f"Seeding completed successfully: {result['message']}")
        logger.info(f"Scene ID: {result['scene_id']}")
        logger.info(f"Slick ID: {result['slick_id']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
