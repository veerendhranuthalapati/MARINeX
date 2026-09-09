from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from app.services.ais.provider import AISProvider
from app.schemas.ais import VesselSchema, AISPointSchema, VesselTrajectoryResponse
from app.core.config import settings
from app.core.logging import logger


class CSVAISProvider(AISProvider):
    """
    AIS Provider reading from standardized CSV position reports.
    Parses MMSI, IMO, VesselName, VesselType, Flag, Timestamp, Lat, Lon, SOG, COG, Heading, NavStatus.
    """

    def __init__(self, csv_path: Optional[Path] = None):
        self.csv_path = csv_path or (settings.SAMPLES_DIR / "sample_ais_trajectories.csv")
        self._df: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_data(self):
        if not self.csv_path.exists():
            logger.warning(f"AIS CSV file not found at {self.csv_path}")
            self._df = pd.DataFrame()
            return

        try:
            df = pd.read_csv(self.csv_path)
            # Ensure timestamps are ISO parsed datetime objects
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            self._df = df
            logger.info(f"Loaded {len(df)} AIS points across {df['mmsi'].nunique()} vessels from CSV.")
        except Exception as e:
            logger.error(f"Error parsing AIS CSV: {e}")
            self._df = pd.DataFrame()

    def query_vessels(
        self,
        bounding_box: List[float],
        start_time: datetime,
        end_time: datetime,
        vessel_types: Optional[List[str]] = None,
    ) -> List[VesselSchema]:
        if self._df is None or self._df.empty:
            return []

        min_lon, min_lat, max_lon, max_lat = bounding_box
        t_start = pd.Timestamp(start_time).tz_convert("UTC") if start_time.tzinfo else pd.Timestamp(start_time, tz="UTC")
        t_end = pd.Timestamp(end_time).tz_convert("UTC") if end_time.tzinfo else pd.Timestamp(end_time, tz="UTC")

        mask = (
            (self._df["latitude"] >= min_lat)
            & (self._df["latitude"] <= max_lat)
            & (self._df["longitude"] >= min_lon)
            & (self._df["longitude"] <= max_lon)
            & (self._df["timestamp"] >= t_start)
            & (self._df["timestamp"] <= t_end)
        )

        filtered = self._df[mask]
        if vessel_types:
            filtered = filtered[filtered["vessel_type"].isin(vessel_types)]

        vessels = []
        for mmsi, group in filtered.groupby("mmsi"):
            row = group.iloc[0]
            vessels.append(
                VesselSchema(
                    id=f"vessel_{mmsi}",
                    mmsi=int(mmsi),
                    imo=int(row["imo"]) if pd.notna(row.get("imo")) else None,
                    vessel_name=str(row["vessel_name"]),
                    vessel_type=str(row["vessel_type"]),
                    flag=str(row.get("flag", "Unknown")),
                    metadata_json={
                        "point_count": len(group),
                        "avg_speed_knots": round(float(group["speed_knots"].mean()), 2),
                    },
                )
            )

        return vessels

    def get_vessel_trajectory(
        self,
        vessel_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Optional[VesselTrajectoryResponse]:
        if self._df is None or self._df.empty:
            return None

        # vessel_id is e.g. "vessel_636019842" or numeric MMSI
        mmsi_str = vessel_id.replace("vessel_", "")
        try:
            mmsi = int(mmsi_str)
        except ValueError:
            return None

        vessel_df = self._df[self._df["mmsi"] == mmsi].sort_values("timestamp")
        if vessel_df.empty:
            return None

        if start_time:
            t_start = pd.Timestamp(start_time).tz_convert("UTC") if start_time.tzinfo else pd.Timestamp(start_time, tz="UTC")
            vessel_df = vessel_df[vessel_df["timestamp"] >= t_start]
        if end_time:
            t_end = pd.Timestamp(end_time).tz_convert("UTC") if end_time.tzinfo else pd.Timestamp(end_time, tz="UTC")
            vessel_df = vessel_df[vessel_df["timestamp"] <= t_end]

        if vessel_df.empty:
            return None

        row = vessel_df.iloc[0]
        vessel_schema = VesselSchema(
            id=f"vessel_{mmsi}",
            mmsi=mmsi,
            imo=int(row["imo"]) if pd.notna(row.get("imo")) else None,
            vessel_name=str(row["vessel_name"]),
            vessel_type=str(row["vessel_type"]),
            flag=str(row.get("flag", "Unknown")),
        )

        points = []
        for _, pt in vessel_df.iterrows():
            points.append(
                AISPointSchema(
                    id=f"pt_{mmsi}_{int(pt['timestamp'].timestamp())}",
                    vessel_id=f"vessel_{mmsi}",
                    timestamp=pt["timestamp"].to_pydatetime(),
                    latitude=float(pt["latitude"]),
                    longitude=float(pt["longitude"]),
                    speed=float(pt.get("speed_knots", 0.0)),
                    course=float(pt.get("course_deg", 0.0)),
                    heading=float(pt.get("heading_deg", 0.0)),
                    navigation_status=str(pt.get("nav_status", "Under way using engine")),
                )
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
        vessels = self.query_vessels(bounding_box, start_time, end_time)
        trajectories = []
        for v in vessels:
            traj = self.get_vessel_trajectory(v.id, start_time, end_time)
            if traj and traj.point_count > 0:
                trajectories.append(traj)
        return trajectories
