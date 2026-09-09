from datetime import datetime, timezone
import pytest
from app.services.attribution.engine import VesselAttributionEngine
from app.services.ais.csv_provider import CSVAISProvider
from app.schemas.attribution import ScoringWeightsConfig


def test_vessel_attribution_scoring():
    engine = VesselAttributionEngine(
        weights=ScoringWeightsConfig(proximity=0.35, temporal=0.25, trajectory=0.25, behavior=0.15)
    )
    provider = CSVAISProvider()

    # Define origin at 19.312, 71.378 at 03:30 UTC
    origin_centroid = [71.378, 19.312]
    origin_time = datetime(2026, 3, 1, 3, 30, 0, tzinfo=timezone.utc)
    origin_poly = [
        [71.365, 19.302],
        [71.390, 19.308],
        [71.396, 19.324],
        [71.382, 19.330],
        [71.365, 19.302],
    ]

    t0 = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 3, 1, 8, 0, 0, tzinfo=timezone.utc)
    trajectories = provider.get_all_trajectories_in_window([71.0, 19.0, 71.8, 19.6], t0, t1)

    assert len(trajectories) >= 3

    results = engine.evaluate_candidates(
        slick_id="slick_test_001",
        origin_centroid=origin_centroid,
        origin_polygon_coords=origin_poly,
        origin_time=origin_time,
        trajectories=trajectories,
    )

    assert len(results.candidates) >= 3
    # First candidate should have rank 1 and highest score
    c1 = results.candidates[0]
    assert c1.rank == 1
    assert c1.overall_score > 70.0
    assert c1.vessel.mmsi == 636019842  # PACIFIC CROWN passed right through origin!
    assert c1.confidence == "HIGH"
    assert len(c1.evidence) >= 3

    # Check factor score values
    assert 0.0 <= c1.factors.proximity_score <= 100.0
    assert 0.0 <= c1.factors.temporal_score <= 100.0
    assert 0.0 <= c1.factors.trajectory_score <= 100.0
    assert 0.0 <= c1.factors.behavior_score <= 100.0

    # Ensure last candidate is ranked lower
    c_last = results.candidates[-1]
    assert c_last.overall_score < c1.overall_score
