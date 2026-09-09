from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.schemas.ais import VesselSchema, AISPointSchema, VesselTrajectoryResponse


class AISProvider(ABC):
    """
    Abstract Interface for AIS (Automatic Identification System) Data Providers.
    Allows transparent switching between historical CSV replays, mock traffic generators,
    and live streaming / database providers (MarineCadastre, AISHub, Spire, Coast Guard VTS).
    """

    @abstractmethod
    def query_vessels(
        self,
        bounding_box: List[float],
        start_time: datetime,
        end_time: datetime,
        vessel_types: Optional[List[str]] = None
    ) -> List[VesselSchema]:
        """Query unique vessels active within the spatial bounding box and time window."""
        pass

    @abstractmethod
    def get_vessel_trajectory(
        self,
        vessel_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[VesselTrajectoryResponse]:
        """Retrieve chronological AIS breadcrumb trajectory for a specific vessel."""
        pass

    @abstractmethod
    def get_all_trajectories_in_window(
        self,
        bounding_box: List[float],
        start_time: datetime,
        end_time: datetime
    ) -> List[VesselTrajectoryResponse]:
        """Retrieve all vessel trajectories within spatial and temporal bounds."""
        pass
