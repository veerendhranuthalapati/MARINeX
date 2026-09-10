import math
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from app.utils.geo import (
    haversine_km,
    point_to_polygon_distance_km,
    trajectory_intersects_polygon,
)
from app.schemas.ais import VesselTrajectoryResponse
from app.schemas.attribution import (
    VesselCandidateResponse,
    FactorBreakdown,
    CandidateMetrics,
    ScoringWeightsConfig,
    AttributionResultsResponse,
)
from app.core.config import settings
from app.core.logging import logger
from app.core.status import ConfidenceTier


# Attribution conclusion tiers (Phase 28): every run must land on exactly one.
CONCLUSION_CANDIDATE = "CANDIDATE_IDENTIFIED"                 # >=1 HIGH/MEDIUM candidate
CONCLUSION_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"             # candidates exist but too weak
CONCLUSION_NO_CANDIDATE = "NO_RELIABLE_CANDIDATE"             # no usable candidate / no AIS in window


class VesselAttributionEngine:
    """
    Explainable Forensic Vessel Attribution and Ranking Engine.

    Evaluates candidate vessels against estimated oil spill origin geometry and release window.
    Calculates four independent, explainable factor scores:
      1. Proximity Score (inverse distance to origin at closest point of approach)
      2. Temporal Score (consistency with hindcast release timestamp)
      3. Trajectory Score (intersection and course alignment with origin uncertainty polygon)
      4. Behavior Score (vessel cargo classification, speed alterations, loitering)

    IMPORTANT:
    Composite scores represent relative investigation priority and forensic consistency.
    They do NOT constitute legal proof of liability.
    """

    def __init__(self, weights: Optional[ScoringWeightsConfig] = None):
        self.weights = weights or ScoringWeightsConfig(
            proximity=settings.WEIGHT_PROXIMITY,
            temporal=settings.WEIGHT_TEMPORAL,
            trajectory=settings.WEIGHT_TRAJECTORY,
            behavior=settings.WEIGHT_BEHAVIOR,
        )

    def evaluate_candidates(
        self,
        slick_id: str,
        origin_centroid: List[float],  # [lon, lat]
        origin_polygon_coords: List[List[float]],  # [[lon, lat], ...]
        origin_time: datetime,
        trajectories: List[VesselTrajectoryResponse],
        weights_override: Optional[ScoringWeightsConfig] = None,
    ) -> AttributionResultsResponse:
        w = weights_override or self.weights
        origin_lon, origin_lat = origin_centroid[0], origin_centroid[1]

        candidates: List[VesselCandidateResponse] = []

        for traj in trajectories:
            vessel = traj.vessel
            points = traj.points
            if not points:
                continue

            # 1. Find Closest Point of Approach (CPA)
            min_dist_km = float("inf")
            cpa_point = points[0]
            for pt in points:
                d = haversine_km(origin_lat, origin_lon, pt.latitude, pt.longitude)
                if d < min_dist_km:
                    min_dist_km = d
                    cpa_point = pt

            # 2. Proximity Score (0 to 100)
            # Exponential decay: 100 at 0 km, ~60 at 2.5 km, ~36 at 5 km, <5 at 15 km
            proximity_score = max(0.0, min(100.0, 100.0 * math.exp(-min_dist_km / 4.8)))

            # 3. Temporal Score (0 to 100)
            # Difference in minutes between CPA and origin release time
            # Make sure timestamps are timezone-aware or naive consistently
            cpa_ts = cpa_point.timestamp
            if origin_time.tzinfo and not cpa_ts.tzinfo:
                cpa_ts = cpa_ts.replace(tzinfo=timezone.utc)
            elif not origin_time.tzinfo and cpa_ts.tzinfo:
                origin_time = origin_time.replace(tzinfo=timezone.utc)

            time_delta_mins = abs((cpa_ts - origin_time).total_seconds()) / 60.0
            # Gaussian falloff around release window (sigma = 75 minutes)
            temporal_score = max(0.0, min(100.0, 100.0 * math.exp(-((time_delta_mins / 75.0) ** 2))))

            # 4. Trajectory Intersection Score (0 to 100)
            line_coords = [(pt.longitude, pt.latitude) for pt in points]
            intersects = trajectory_intersects_polygon(line_coords, origin_polygon_coords)

            if intersects:
                trajectory_score = 92.0
            else:
                dist_to_poly_km = point_to_polygon_distance_km(cpa_point.latitude, cpa_point.longitude, origin_polygon_coords)
                trajectory_score = max(0.0, min(75.0, 75.0 * math.exp(-dist_to_poly_km / 3.5)))

            # 5. Behavior / Vessel Profile Score (0 to 100)
            # Base score by vessel type risk
            vtype_lower = vessel.vessel_type.lower()
            if any(t in vtype_lower for t in ["crude", "oil tanker", "vlcc", "chemical", "tanker"]):
                behavior_score = 75.0
            elif any(t in vtype_lower for t in ["cargo", "container", "bulk"]):
                behavior_score = 40.0
            elif any(t in vtype_lower for t in ["tug", "supply", "offshore"]):
                behavior_score = 25.0
            else:
                behavior_score = 15.0

            # Check speed anomaly / loitering
            speeds = [pt.speed for pt in points if pt.speed is not None]
            avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
            speed_anomaly = False
            if len(speeds) >= 3 and (max(speeds) - min(speeds) > 4.5):
                speed_anomaly = True
                behavior_score = min(100.0, behavior_score + 15.0)

            # 6. Weighted Overall Score
            overall_score = (
                w.proximity * proximity_score
                + w.temporal * temporal_score
                + w.trajectory * trajectory_score
                + w.behavior * behavior_score
            )
            overall_score = round(max(0.0, min(100.0, overall_score)), 1)

            # 7. Confidence / Priority Tier
            if overall_score >= 75.0:
                confidence = "HIGH"
                rec = "PRIORITY_1: Initiate formal maritime query. Request Oil Record Book (Part II) and voyage data recorder (VDR)."
            elif overall_score >= 50.0:
                confidence = "MEDIUM"
                rec = "PRIORITY_2: Monitor secondary AIS tracks and correlate with port of departure inspection records."
            elif overall_score >= 25.0:
                confidence = "LOW"
                rec = "PRIORITY_3: Low evidence correlation. Maintain passive tracking log."
            else:
                confidence = "EXCLUDED"
                rec = "EXCLUDED: Spatial and temporal trajectory inconsistent with inferred spill origin."

            # 8. Generate Forensic Evidence Trail
            evidence: List[str] = []
            if intersects:
                evidence.append(
                    f"Vessel trajectory directly intersected the 95% probable origin uncertainty polygon at {cpa_ts.strftime('%H:%M UTC')}."
                )
            else:
                evidence.append(
                    f"Closest approach was {min_dist_km:.2f} km from estimated origin centroid."
                )

            evidence.append(
                f"Temporal difference with inferred release window ({origin_time.strftime('%H:%M UTC')}): {time_delta_mins:.1f} minutes."
            )

            if "tanker" in vtype_lower:
                evidence.append(
                    f"High-risk cargo classification: {vessel.vessel_type} (MMSI: {vessel.mmsi}, Flag: {vessel.flag})."
                )
            else:
                evidence.append(
                    f"Standard vessel category: {vessel.vessel_type} (MMSI: {vessel.mmsi}, Flag: {vessel.flag})."
                )

            if speed_anomaly:
                evidence.append("Speed variation anomaly detected along transit corridor.")

            candidates.append(
                VesselCandidateResponse(
                    id=f"cand_{slick_id[:12]}_{vessel.mmsi}",
                    slick_id=slick_id,
                    vessel_id=vessel.id,
                    vessel=vessel,
                    rank=1,  # will be assigned after sorting
                    overall_score=overall_score,
                    confidence=confidence,
                    factors=FactorBreakdown(
                        proximity_score=round(proximity_score, 1),
                        temporal_score=round(temporal_score, 1),
                        trajectory_score=round(trajectory_score, 1),
                        behavior_score=round(behavior_score, 1),
                    ),
                    metrics=CandidateMetrics(
                        closest_distance_km=round(min_dist_km, 2),
                        time_delta_minutes=round(time_delta_mins, 1),
                        trajectory_intersects_origin=intersects,
                        transit_speed_knots=round(cpa_point.speed, 1),
                        speed_anomaly_detected=speed_anomaly,
                    ),
                    evidence=evidence,
                    recommendation=rec,
                    evaluated_at=datetime.now(timezone.utc),
                )
            )

        # Sort descending by overall score and assign rank
        candidates.sort(key=lambda c: c.overall_score, reverse=True)
        for idx, cand in enumerate(candidates):
            cand.rank = idx + 1

        # Phase 28: derive a single honest conclusion from the actual outputs.
        conclusion = CONCLUSION_CANDIDATE
        conclusion_detail = (
            "Candidate vessels were correlated against the drift-hindcast origin region."
        )
        if candidates:
            top_conf = candidates[0].confidence
            if top_conf == ConfidenceTier.EXCLUDED.value:
                conclusion = CONCLUSION_NO_CANDIDATE
                conclusion_detail = (
                    f"All {len(candidates)} scanned vessel(s) were spatially/temporally inconsistent "
                    "with the inferred spill origin. No reliable candidate identified."
                )
            elif top_conf in (ConfidenceTier.LOW.value, ConfidenceTier.MEDIUM.value):
                conclusion = CONCLUSION_INSUFFICIENT
                conclusion_detail = (
                    f"Top candidate ('{candidates[0].vessel.vessel_name}', score {candidates[0].overall_score:.1f}/100) "
                    "reaches only LOW/MEDIUM evidence consistency. Insufficient for reliable attribution; "
                    "recommend additional optical/tracking verification before any port-state action."
                )
        else:
            conclusion = CONCLUSION_NO_CANDIDATE
            conclusion_detail = (
                "No AIS vessel trajectories were found in the spatial and temporal search window, so no "
                "candidate correlation could be performed. No reliable candidate identified."
            )

        return AttributionResultsResponse(
            slick_id=slick_id,
            evaluated_at=datetime.now(timezone.utc),
            total_vessels_scanned=len(trajectories),
            weights_applied=w,
            candidates=candidates,
            conclusion=conclusion,
            conclusion_detail=conclusion_detail,
        )
