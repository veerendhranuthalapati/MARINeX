from datetime import datetime, timedelta
from typing import List, Optional
from app.services.ais.provider import AISProvider
from app.schemas.ais import VesselSchema, AISPointSchema, VesselTrajectoryResponse


class MockAISProvider(AISProvider):
    """
    Mock AIS Provider that generates synthetic realistic maritime traffic
    for demonstration and test suites when external datasets are absent.
    """

    def __init__(self):
        self._seed_vessels = [
            {
                "mmsi": 636019842,
                "imo": 9456789,
                "vessel_name": "PACIFIC CROWN",
                "vessel_type": "Crude Oil Tanker",
                "flag": "Liberia",
                "speed": 11.8,
                "course": 60.0,
                # Path cuts right through origin (19.310, 71.376)
                "waypoints": [
                    (19.210, 71.220, 0),
                    (19.245, 71.275, 30),
                    (19.280, 71.330, 60),
                    (19.310, 71.376, 85),
                    (19.338, 71.422, 110),
                    (19.375, 71.480, 140),
                ],
            },
            {
                "mmsi": 212589000,
                "imo": 9784321,
                "vessel_name": "NORDIC VOYAGER",
                "vessel_type": "Chemical Tanker",
                "flag": "Cyprus",
                "speed": 13.0,
                "course": 45.0,
                "waypoints": [
                    (19.230, 71.320, 30),
                    (19.290, 71.370, 75),
                    (19.348, 71.428, 120),
                    (19.410, 71.485, 165),
                ],
            },
            {
                "mmsi": 419001234,
                "imo": 9321546,
                "vessel_name": "BHARAT RATNA",
                "vessel_type": "Container Ship",
                "flag": "India",
                "speed": 16.4,
                "course": 350.0,
                "waypoints": [
                    (19.180, 71.480, 0),
                    (19.295, 71.460, 60),
                    (19.410, 71.440, 120),
                ],
            },
        ]

    def query_vessels(
        self,
        bounding_box: List[float],
        start_time: datetime,
        end_time: datetime,
        vessel_types: Optional[List[str]] = None,
    ) -> List[VesselSchema]:
        vessels = []
        for v in self._seed_vessels:
            if vessel_types and v["vessel_type"] not in vessel_types:
                continue
            vessels.append(
                VesselSchema(
                    id=f"vessel_{v['mmsi']}",
                    mmsi=v["mmsi"],
                    imo=v["imo"],
                    vessel_name=v["vessel_name"],
                    vessel_type=v["vessel_type"],
                    flag=v["flag"],
                    metadata_json={"is_mock": True},
                )
            )
        return vessels

    def get_vessel_trajectory(
        self,
        vessel_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Optional[VesselTrajectoryResponse]:
        mmsi = int(vessel_id.replace("vessel_", ""))
        target = next((v for v in self._seed_vessels if v["mmsi"] == mmsi), None)
        if not target:
            return None

        # Base reference time: 2026-03-01 02:00:00 UTC
        base_t = start_time or datetime(2026, 3, 1, 2, 0, 0)
        points = []
        for lat, lon, offset_mins in target["waypoints"]:
            t = base_t + timedelta(minutes=offset_mins)
            points.append(
                AISPointSchema(
                    id=f"pt_mock_{mmsi}_{offset_mins}",
                    vessel_id=f"vessel_{mmsi}",
                    timestamp=t,
                    latitude=lat,
                    longitude=lon,
                    speed=target["speed"],
                    course=target["course"],
                    heading=target["course"],
                    navigation_status="Under way using engine",
                )
            )

        vessel_schema = VesselSchema(
            id=f"vessel_{mmsi}",
            mmsi=target["mmsi"],
            imo=target["imo"],
            vessel_name=target["vessel_name"],
            vessel_type=target["vessel_type"],
            flag=target["flag"],
        )

        return VesselTrajectoryResponse(
            vessel=vessel_schema,
            points=points,
            point_count=len(points),
            start_time=points[0].timestamp,
            end_time=points[-1].timestamp,
        )

    def get_all_trajectories_in_window(
        self,
        bounding_box: List[float],
        start_time: datetime,
        end_time: datetime,
    ) -> List[VesselTrajectoryResponse]:
        trajs = []
        for v in self._seed_vessels:
            t = self.get_vessel_trajectory(f"vessel_{v['mmsi']}", start_time, end_time)
            if t:
                trajs.append(t)
        return trajs
