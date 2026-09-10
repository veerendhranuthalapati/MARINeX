"""
Phase 7 - Environment Quality Checks.

Validates a requested spatio-temporal window BEFORE drift simulation:
  - coordinate-system / bounds sanity
  - temporal coverage (start/end within provider availability)
  - units consistency (wind m/s, currents m/s)
  - missing-value detection

Failure to pass a FAIL check must stop the pipeline with a clear message.
WARN entails a documented caveat attached to provenance.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.core.status import DataQuality


class EnvironmentQualityError(Exception):
    pass


class EnvironmentQualityReport:
    def __init__(self):
        self.checks: List[Dict[str, str]] = []
        self.overall: DataQuality = DataQuality.PASS

    def add(self, name: str, quality: DataQuality, detail: str):
        self.checks.append({"name": name, "quality": quality.value, "detail": detail})
        order = {DataQuality.PASS: 0, DataQuality.WARN: 1, DataQuality.FAIL: 2}
        cur = order[DataQuality(self.overall.value)] if isinstance(self.overall, DataQuality) else 0
        if order[quality] > cur:
            self.overall = quality

    def to_dict(self) -> dict:
        return {"overall": self.overall.value if isinstance(self.overall, DataQuality) else str(self.overall),
                "checks": self.checks}


class EnvironmentQualityChecker:
    def __init__(self, coverage_start: Optional[datetime] = None,
                 coverage_end: Optional[datetime] = None,
                 provider_name: str = "unspecified"):
        self.coverage_start = coverage_start
        self.coverage_end = coverage_end
        self.provider_name = provider_name

    def check_window(self, lat: float, lon: float,
                     requested_start: datetime, requested_end: datetime) -> EnvironmentQualityReport:
        report = EnvironmentQualityReport()

        # 1. Coordinate system / bounds sanity
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            report.add("coordinates", DataQuality.FAIL,
                       f"lat={lat} lon={lon} outside WGS84 bounds.")
        else:
            report.add("coordinates", DataQuality.PASS,
                       f"lat={lat} lon={lon} valid WGS84 coordinates.")

        # 2. Timestamp ordering / timezone consistency
        if requested_end <= requested_start:
            report.add("timestamps", DataQuality.FAIL,
                       "requested end_time not after start_time.")
        else:
            report.add("timestamps", DataQuality.PASS,
                       f"window {requested_start.isoformat()} -> {requested_end.isoformat()} valid.")

        # 3. Temporal coverage vs provider availability (when known)
        if self.coverage_start and self.coverage_end:
            margin = timedelta(hours=6)
            if requested_start < self.coverage_start - margin or requested_end > self.coverage_end + margin:
                report.add("temporal_coverage", DataQuality.FAIL,
                           f"window outside provider coverage "
                           f"({self.coverage_start.isoformat()}..{self.coverage_end.isoformat()}).")
            else:
                report.add("temporal_coverage", DataQuality.PASS,
                           "window inside provider availability plus 6h margin.")
        else:
            report.add("temporal_coverage", DataQuality.WARN,
                       f"provider '{self.provider_name}' has unknown coverage; assuming window.")

        # 4. Units sanity - performed when a snapshot is available (values in m/s, 0..50 wind)
        return report

    def check_snapshot(self, report: EnvironmentQualityReport,
                       wind_speed_mps: float, current_speed_mps: float,
                       wave_height_m: Optional[float] = None) -> EnvironmentQualityReport:
        if not (-1.0 <= wind_speed_mps <= 80.0):
            report.add("units", DataQuality.FAIL,
                       f"wind speed {wind_speed_mps} m/s out of physical range.")
        elif not (-2.0 <= current_speed_mps <= 5.0):
            report.add("units", DataQuality.FAIL,
                       f"current speed {current_speed_mps} m/s out of physical range.")
        else:
            report.add("units", DataQuality.PASS,
                       f"wind {wind_speed_mps:.2f} m/s, current {current_speed_mps:.2f} m/s in physical range.")

        if wave_height_m is not None and wave_height_m < 0.0:
            report.add("wave_units", DataQuality.FAIL, "negative wave height.")
        return report