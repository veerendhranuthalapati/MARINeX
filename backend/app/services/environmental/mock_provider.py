import json
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path
from app.core.config import settings
from app.schemas.environment import (
    EnvironmentalSnapshotResponse,
    WindData,
    OceanCurrentData,
    WaveData,
)
from app.services.environmental.provider import EnvironmentalProvider
from app.core.logging import logger


class MockEnvironmentalProvider(EnvironmentalProvider):
    """
    Deterministic, clearly-labelled DEMO provisioning of environmental forcing.

    SciGuard: every response is stamped status_label=DEMO_DATA and source is
    "MARINeX Demo Baseline" so drift outputs derived from it are never mistaken
    for real reanalysis fields.
    """

    def __init__(self, samples_file: Optional[Path] = None):
        self.samples_file = samples_file or (settings.SAMPLES_DIR / "sample_environmental.json")
        self._cache = None

    def provider_id(self) -> str:
        return "demo_environment_v1"

    def metadata(self) -> dict:
        return {
            "source": "MARINeX Demo Baseline (deterministic Arabian Sea proxy)",
            "status_label": "DEMO_DATA",
            "resolution": "n/a",
            "caveats": "Not real reanalysis. Used only for demo and unit tests.",
        }

    def _load(self) -> dict:
        if self._cache is not None:
            return self._cache
        data = {}
        if self.samples_file and self.samples_file.exists():
            try:
                with open(self.samples_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"MockEnvironmentalProvider failed to read sample file: {e}")
        self._cache = data
        return data

    def get_conditions(
        self,
        lat: float,
        lon: float,
        timestamp: datetime,
        bbox: Optional[List[float]] = None,
    ) -> EnvironmentalSnapshotResponse:
        data = self._load()

        # Deterministic small spatial/temporal variation so different slicks
        # produce slightly different (but repeatable) forcing values.
        seed = round(lat * 1e4) + round(lon * 1e4)
        jitter = (seed % 7) / 100.0

        wind = data.get("wind", {})
        current = data.get("ocean_current", {})
        wave = data.get("wave", {})
        if not wind:
            wind = {"speed_mps": 5.4, "direction_deg": 240.0,
                    "u_component_mps": -4.68, "v_component_mps": -2.70, "gust_mps": 7.2}
        if not current:
            current = {"speed_mps": 0.38, "direction_deg": 70.0,
                       "u_component_mps": 0.357, "v_component_mps": 0.130, "depth_meters": 0.5}
        if not wave:
            wave = {"significant_wave_height_m": 1.2, "peak_period_seconds": 6.5,
                    "mean_direction_deg": 235.0}

        return EnvironmentalSnapshotResponse(
            id=f"env_demo_{int(timestamp.timestamp())}_{seed}",
            timestamp=timestamp,
            latitude=lat,
            longitude=lon,
            wind=WindData(
                speed_mps=round(wind["speed_mps"] + jitter, 3),
                direction_deg=wind["direction_deg"],
                u_component_mps=wind["u_component_mps"],
                v_component_mps=wind["v_component_mps"],
                gust_mps=wind.get("gust_mps"),
            ),
            ocean_current=OceanCurrentData(
                speed_mps=round(current["speed_mps"] - jitter, 3),
                direction_deg=current["direction_deg"],
                u_component_mps=current["u_component_mps"],
                v_component_mps=current["v_component_mps"],
                depth_meters=current.get("depth_meters", 0.5),
            ),
            wave=WaveData(
                significant_wave_height_m=wave["significant_wave_height_m"],
                peak_period_seconds=wave.get("peak_period_seconds"),
                mean_direction_deg=wave.get("mean_direction_deg"),
            ),
            source="MARINeX Demo Baseline (DEMO_DATA)",
            raw_data={"provider": self.provider_id(), "status_label": "DEMO_DATA"},
            created_at=datetime.now(timezone.utc),
        )