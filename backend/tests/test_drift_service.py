from datetime import datetime, timezone
import pytest
from app.services.drift.service import MockDriftService
from app.schemas.drift import DriftSimulationRequest


def test_mock_drift_hindcast_simulation():
    drift_service = MockDriftService()
    slick_centroid = [71.418, 19.345]  # [lon, lat]
    start_time = datetime(2026, 3, 1, 6, 45, 0, tzinfo=timezone.utc)

    # Ocean current flowing eastward (u > 0) and northward (v > 0)
    # Wind blowing toward east-north-east (u > 0, v > 0)
    # Backward hindcast should therefore move westward and southward!
    req = DriftSimulationRequest(
        duration_hours=4.0,
        direction="HINDCAST",
        time_step_seconds=600,
        num_particles=150,
    )

    res = drift_service.simulate(
        slick_id="slick_test_001",
        centroid=slick_centroid,
        start_time=start_time,
        req=req,
        wind_u=4.0,
        wind_v=2.0,
        current_u=0.3,
        current_v=0.1,
    )

    assert res.status == "COMPLETED"
    assert res.direction == "HINDCAST"
    assert res.probable_origin_centroid is not None

    # Origin should be back in time and displaced westward / southward
    orig_lon, orig_lat = res.probable_origin_centroid
    assert orig_lon < slick_centroid[0]
    assert orig_lat < slick_centroid[1]
    assert res.end_time < start_time

    # Bounding uncertainty polygon must exist
    assert res.origin_geometry is not None
    assert res.origin_geometry["type"] == "Polygon"
    assert len(res.origin_geometry["coordinates"][0]) >= 4

    # Trajectory LineString must exist
    assert res.trajectory_geometry["type"] == "LineString"
    assert len(res.trajectory_geometry["coordinates"]) >= 2
