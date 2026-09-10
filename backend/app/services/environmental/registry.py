from typing import Optional
from app.services.environmental.provider import EnvironmentalProvider
from app.services.environmental.mock_provider import MockEnvironmentalProvider
from app.services.environmental.era5_provider import ERA5Provider
from app.core.config import settings


class EnvironmentalProviderRegistry:
    """Selects the environmental provider based on configuration.

    Preference:
      1. ERA5Provider if real-data credentials are configured (env vars).
      2. MockEnvironmentalProvider (DEMO_DATA, deterministic) for local dev & tests.
    """

    @staticmethod
    def resolve() -> EnvironmentalProvider:
        era5 = ERA5Provider(
            cache_dir=settings.ERA5_CACHE_DIR,
            cds_key=settings.CDS_API_KEY,
            cds_url=settings.CDS_API_URL,
        )
        if era5.available:
            return era5
        return MockEnvironmentalProvider()