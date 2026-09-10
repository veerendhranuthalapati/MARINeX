from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from app.schemas.environment import EnvironmentalSnapshotResponse


class EnvironmentalProvider(ABC):
    """
    Abstract interface for environmental forcing providers (wind, currents, waves).

    Phases 6-7: an implementation must accept a spatial window + time range and
    return validated environmental data for that window only. Implementations
    must NOT silently fetch or substitute unrelated global data.
    """

    @abstractmethod
    def get_conditions(
        self,
        lat: float,
        lon: float,
        timestamp: datetime,
        bbox: Optional[List[float]] = None,
    ) -> EnvironmentalSnapshotResponse:
        """Return validated conditions at the requested point/time."""
        pass

    @abstractmethod
    def provider_id(self) -> str:
        """Stable identifier for the provider (used in provenance)."""
        pass

    @abstractmethod
    def metadata(self) -> Dict[str, str]:
        """Source, version, resolution, and availability caveats."""
        pass