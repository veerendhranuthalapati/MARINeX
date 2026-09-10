"""
AIS Trajectory Generation (Phase 13).

Pipeline:
    AISPoint
      -> validated points (koe clean_reason == "valid")
      -> sorted by (mmsi, timestamp)
      -> trajectory segments (pairs of consecutive points within a time/speed limit)
      -> LineString (list of (lon, lat) ordered by time)

Invalid AIS records are not silently discarded: every point carries a recorded
clean_reason (see ais_schema.clean_points) that is surfaced in reports.

Segment break rules (recorded in step_log):
  - t_gap_gt_limit   : time gap between consecutive points exceeds max_gap_minutes
  - speed_anomaly    : implied ground speed exceeds max_speed_knots
  - duplicate_time   : duplicate timestamp for same MMSI (dropped upstream when dedupe=True)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ml.ais.ais_schema import AISPoint

EARTH_R = 6371.0088  # km


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return EARTH_R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@dataclass
class Trajectory:
    mmsi: int
    points: List[AISPoint] = field(default_factory=list)
    segments: List[List[AISPoint]] = field(default_factory=list)  # contiguous runs
    cleaning: Dict[str, int] = field(default_factory=dict)        # reason -> count
    step_log: List[str] = field(default_factory=list)

    def as_linestrings(self) -> List[List[Tuple[float, float]]]:
        """GeoJSON-friendly [lon, lat] coordinates per segment."""
        return [[(p.longitude, p.latitude) for p in seg] for seg in self.segments if len(seg) >= 2]

    @property
    def n_points(self) -> int:
        return len(self.points)

    @property
    def n_segments(self) -> int:
        return len(self.segments)


def build_trajectories(
    points: List[AISPoint],
    max_gap_minutes: float = 60.0,
    max_speed_knots: float = 60.0,
) -> Dict[int, Trajectory]:
    """Group + validate + segmente AIS points by MMSI.

    Returns a dict mmsi -> Trajectory. Break reasons are logged, never silently
    dropped records (drops happen only for invalid points, recorded as cleaning reasons).
    """
    by_mmsi: Dict[int, List[AISPoint]] = {}
    for p in points:
        by_mmsi.setdefault(p.mmsi, []).append(p)

    trajs: Dict[int, Trajectory] = {}
    for mmsi, pts in by_mmsi.items():
        pts = sorted(pts, key=lambda p: p.timestamp)
        valid = [p for p in pts if p.clean_reason == "valid"]
        cleaning: Dict[str, int] = {}
        for p in pts:
            cleaning[p.clean_reason] = cleaning.get(p.clean_reason, 0) + 1

        traj = Trajectory(mmsi=mmsi, points=valid, cleaning=cleaning)
        if len(valid) < 2:
            traj.step_log.append("too_few_points")
            trajs[mmsi] = traj
            continue

        current: List[AISPoint] = [valid[0]]
        for prev, cur in zip(valid, valid[1:]):
            gap_min = (cur.timestamp - prev.timestamp).total_seconds() / 60.0
            if gap_min > max_gap_minutes:
                if len(current) >= 2:
                    traj.segments.append(current)
                else:
                    traj.step_log.append("gap_dropped_singleton")
                current = [cur]
                traj.step_log.append(f"t_gap_gt_limit:{gap_min:.1f}min")
                continue
            if gap_min > 0:
                dist_km = haversine_km(prev.latitude, prev.longitude, cur.latitude, cur.longitude)
                speed_kn = dist_km / (gap_min / 60.0)
                if speed_kn > max_speed_knots:
                    traj.step_log.append(f"speed_anomaly:{speed_kn:.1f}kn")
                    if len(current) >= 2:
                        traj.segments.append(current)
                    else:
                        traj.step_log.append("speed_dropped_singleton")
                    current = [cur]
                    continue
            current.append(cur)
        if len(current) >= 2:
            traj.segments.append(current)

        traj.step_log.append(f"segments:{len(traj.segments)}")
        trajs[mmsi] = traj

    return trajs