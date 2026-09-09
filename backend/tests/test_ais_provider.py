from datetime import datetime, timezone
import pytest
from app.services.ais.csv_provider import CSVAISProvider
from app.services.ais.mock_provider import MockAISProvider


def test_csv_ais_provider():
    provider = CSVAISProvider()
    bbox = [71.0, 19.0, 71.8, 19.6]
    t0 = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 3, 1, 8, 0, 0, tzinfo=timezone.utc)

    vessels = provider.query_vessels(bbox, t0, t1)
    assert len(vessels) > 0

    # Ensure Pacific Crown (MMSI: 636019842) is found
    mmsis = [v.mmsi for v in vessels]
    assert 636019842 in mmsis

    # Retrieve Pacific Crown trajectory
    traj = provider.get_vessel_trajectory("vessel_636019842", t0, t1)
    assert traj is not None
    assert traj.vessel.mmsi == 636019842
    assert traj.point_count >= 5
    assert traj.points[0].latitude > 0


def test_mock_ais_provider():
    provider = MockAISProvider()
    bbox = [71.0, 19.0, 71.8, 19.6]
    t0 = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 3, 1, 8, 0, 0, tzinfo=timezone.utc)

    vessels = provider.query_vessels(bbox, t0, t1)
    assert len(vessels) >= 3

    traj = provider.get_vessel_trajectory("vessel_636019842", t0, t1)
    assert traj is not None
    assert traj.point_count > 0
