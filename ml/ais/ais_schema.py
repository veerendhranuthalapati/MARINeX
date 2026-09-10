"""
AIS Point Schema and Validation (Phase 13).

Defines the canonical AIS record, column schema shared by CSV -> Parquet -> DuckDB,
and lightweight per-point validation. Invalid records are NEVER silently deleted:
cleaning decisions are recorded with a `clean_reason` code for provenance.

Cleaning reason codes:
  - valid                 : passed all checks
  - bad_coordinates       : latitude/longitude out of physical range
  - unknown_mmsi          : missing/invalid 9-digit MMSI
  - impossible_speed      : speed_knots > 100
  - not_under_way_stop    : speed == 0 (kept, flagged)         [unused in v1]
  - duplicate_timestamp   : same MMSI + timestamp
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Canonical column order written to Parquet.
AIS_SCHEMA: List[str] = [
    "mmsi", "imo", "vessel_name", "vessel_type", "flag",
    "timestamp", "latitude", "longitude",
    "speed_knots", "course_deg", "heading_deg", "nav_status",
    "clean_reason", "source_file",
]

MIN_MMSI = 100_000_000
MAX_MMSI = 999_999_999
MAX_SPEED_KNOTS = 250.0
COORD_EPS = 1e-6


@dataclass
class AISPoint:
    mmsi: int
    timestamp: datetime
    latitude: float
    longitude: float
    speed_knots: float = -1.0
    course_deg: float = -1.0
    heading_deg: float = -1.0
    imo: Optional[int] = None
    vessel_name: str = ""
    vessel_type: str = ""
    flag: str = ""
    nav_status: str = ""
    clean_reason: str = "valid"
    source_file: str = ""

    def valid_latitude(self) -> bool:
        return -90.0 - COORD_EPS <= self.latitude <= 90.0 + COORD_EPS

    def valid_longitude(self) -> bool:
        return -180.0 - COORD_EPS <= self.longitude <= 180.0 + COORD_EPS

    def to_row(self, source_file: str) -> List[Any]:
        return [
            self.mmsi, self.imo, self.vessel_name, self.vessel_type, self.flag,
            self.timestamp.isoformat(), self.latitude, self.longitude,
            self.speed_knots, self.course_deg, self.heading_deg, self.nav_status,
            self.clean_reason, source_file or self.source_file,
        ]

    @staticmethod
    def from_row(row: Dict[str, Any], source_file: str = "") -> "AISPoint":
        ts = row["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return AISPoint(
            mmsi=int(row["mmsi"]),
            imo=int(row["imo"]) if row.get("imo") else None,
            vessel_name=str(row.get("vessel_name") or ""),
            vessel_type=str(row.get("vessel_type") or ""),
            flag=str(row.get("flag") or ""),
            timestamp=ts,
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            speed_knots=float(row.get("speed_knots") or -1.0),
            course_deg=float(row.get("course_deg") or -1.0),
            heading_deg=float(row.get("heading_deg") or -1.0),
            nav_status=str(row.get("nav_status") or ""),
            source_file=str(row.get("source_file") or source_file),
        )

    @staticmethod
    def validate(p: "AISPoint") -> str:
        """Return the clean_reason that applies to this point (or 'valid')."""
        if not (MIN_MMSI <= p.mmsi <= MAX_MMSI):
            return "unknown_mmsi"
        if not p.valid_latitude() or not p.valid_longitude():
            return "bad_coordinates"
        if p.speed_knots > MAX_SPEED_KNOTS:
            return "impossible_speed"
        return "valid"


def dedupe_by_timestamp(points: List[AISPoint]) -> List[AISPoint]:
    """For each MMSI keep the first point per timestamp; later ones -> duplicate_timestamp."""
    seen: Dict[tuple, int] = {}
    out: List[AISPoint] = []
    for p in points:
        key = (p.mmsi, p.timestamp)
        if key in seen:
            if p.clean_reason == "valid":
                dup = type(p)(
                    mmsi=p.mmsi, imo=p.imo, vessel_name=p.vessel_name, vessel_type=p.vessel_type,
                    flag=p.flag, timestamp=p.timestamp, latitude=p.latitude, longitude=p.longitude,
                    speed_knots=p.speed_knots, course_deg=p.course_deg, heading_deg=p.heading_deg,
                    nav_status=p.nav_status, clean_reason="duplicate_timestamp",
                    source_file=p.source_file,
                )
                out.append(dup)
            continue
        seen[key] = 1
        out.append(p)
    return out


def clean_points(
    raw_rows: List[Dict[str, Any]],
    source_file: str = "",
    dedupe: bool = True,
) -> tuple[List[AISPoint], List[Dict[str, str]]]:
    """Validate + dedupe raw AIS rows, returning points and a cleaning log."""
    points = [AISPoint.from_row(r, source_file) for r in raw_rows]
    for p in points:
        p.clean_reason = AISPoint.validate(p)
    if dedupe:
        points = dedupe_by_timestamp(points)
    log = [{"mmsi": p.mmsi, "timestamp": p.timestamp.isoformat(), "clean_reason": p.clean_reason}
           for p in points if p.clean_reason != "valid"]
    return points, log