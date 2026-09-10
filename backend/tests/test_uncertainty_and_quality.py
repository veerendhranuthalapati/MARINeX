"""Tests for Phase 28 uncertainty tiers, Phase 31 data quality, Phase 13 uncertainty report fields."""

from datetime import datetime, timezone

from app.core.status import DataQuality
from app.schemas.ais import VesselSchema
from app.schemas.attribution import (
    CandidateMetrics,
    FactorBreakdown,
    VesselCandidateResponse,
)
from app.services.attribution.engine import (
    CONCLUSION_CANDIDATE,
    CONCLUSION_INSUFFICIENT,
    CONCLUSION_NO_CANDIDATE,
)
from app.services.data_quality.service import DataQualityService
from app.services.reporting.generator import ReportGeneratorService


def _candidate(score, confidence, name="MV TEST"):
    vessel = VesselSchema(id="v1", mmsi=123, imo=9988776, vessel_name=name,
                          vessel_type="Tanker", flag="PA")
    return VesselCandidateResponse(
        id="c1", slick_id="s1", vessel_id="v1", vessel=vessel, rank=1,
        overall_score=score, confidence=confidence,
        factors=FactorBreakdown(proximity_score=1, temporal_score=1,
                                trajectory_score=1, behavior_score=1),
        metrics=CandidateMetrics(closest_distance_km=1.0, time_delta_minutes=5.0,
                                 trajectory_intersects_origin=True,
                                 transit_speed_knots=10.0),
        evidence=[], recommendation="rec", evaluated_at=datetime.now(timezone.utc),
    )


def test_conclusion_no_candidates():
    conclusion, detail = ReportGeneratorService.derive_conclusion([])
    assert conclusion == CONCLUSION_NO_CANDIDATE


def test_conclusion_excluded_top_is_no_candidate():
    conclusion, _ = ReportGeneratorService.derive_conclusion([_candidate(15, "EXCLUDED")])
    assert conclusion == CONCLUSION_NO_CANDIDATE


def test_conclusion_low_and_medium_are_insufficient():
    low_c, _ = ReportGeneratorService.derive_conclusion([_candidate(30, "LOW")])
    med_c, _ = ReportGeneratorService.derive_conclusion([_candidate(60, "MEDIUM")])
    assert low_c == CONCLUSION_INSUFFICIENT
    assert med_c == CONCLUSION_INSUFFICIENT


def test_conclusion_high_is_candidate_identified():
    conclusion, _ = ReportGeneratorService.derive_conclusion([_candidate(85, "HIGH")])
    assert conclusion == CONCLUSION_CANDIDATE


def test_data_quality_full_pass_input():
    dq = DataQualityService.assess(
        detection_status="SLICKS_FOUND",
        detection_confidence=0.90,
        env_quality={"overall": "PASS", "checks": []},
        drift_ok=True,
        ais_track_count=3,
    )
    assert dq["overall"] == "PASS"
    assert {s["source"] for s in dq["sources"]} == {"satellite", "model", "environmental", "drift", "ais"}


def test_data_quality_strict_worst_case():
    dq = DataQualityService.assess(
        detection_status="LOW_CONFIDENCE",
        detection_confidence=0.45,
        env_quality=None,
        drift_ok=True,
        ais_track_count=0,
    )
    assert dq["overall"] == "WARN"
    grades = {s["source"]: s["grade"] for s in dq["sources"]}
    assert grades["satellite"] == "WARN"
    assert grades["model"] == "WARN"
    assert grades["environmental"] == "WARN"
    assert grades["ais"] == "WARN"


def test_data_quality_fail_when_no_drift():
    dq = DataQualityService.assess(
        detection_status="ERROR",
        detection_confidence=0.0,
        env_quality={"overall": "FAIL", "checks": []},
        drift_ok=None,
        ais_track_count=None,
    )
    assert dq["overall"] == "FAIL"
    assert dq["coverage"]["drift"] is False