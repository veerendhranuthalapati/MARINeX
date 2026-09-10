from datetime import datetime, timezone
from typing import List, Optional
from app.schemas.environment import EnvironmentalSnapshotResponse
from app.services.environmental.provider import EnvironmentalProvider
from app.core.logging import logger


class ERA5Provider(EnvironmentalProvider):
    """
    Real-data adapter for ERA5 / Copernicus Marine reanalysis.

    SciGuard: if CDS credentials or a local data cache are NOT configured,
    get_conditions() raises NotImplementedError explaining the gap instead of
    returning a fabricated value. The backend then reports DRIFT_UNAVAILABLE /
    ENVIRONMENT_UNAVAILABLE to the client.
    """

    def __init__(self, cache_dir: Optional[str] = None, cds_key: Optional[str] = None,
                 cds_url: Optional[str] = None):
        self.cache_dir = cache_dir
        self.cds_key = cds_key
        self.cds_url = cds_url
        self.available = bool(cds_key and cache_dir)

    def provider_id(self) -> str:
        return "era5_reanalysis_v1"

    def metadata(self) -> dict:
        return {
            "source": "ERA5/CMEMS reanalysis",
            "status_label": "OBSERVED",
            "resolution": "0.25 deg / hourly",
            "caveats": self._reason(),
        }

    def _reason(self) -> str:
        if not self.available:
            return ("ERA5 provider not configured (missing CDS_API_URL and/or CDS_API_KEY). "
                    "Use MockEnvironmentalProvider for DEMO_DATA or configure credentials.")
        return "Operational reanalysis adapter (stub pending CMEMS API wiring)."

    def get_conditions(
        self,
        lat: float,
        lon: float,
        timestamp: datetime,
        bbox: Optional[List[float]] = None,
    ) -> EnvironmentalSnapshotResponse:
        raise NotImplementedError(self._reason())