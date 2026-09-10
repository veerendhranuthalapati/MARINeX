"""Tests for Phases 54-56 demo cases and Phase 47-48 ML validation bundle endpoints."""

import json


def test_ml_card(client):
    r = client.get("/api/v1/ml/card")
    assert r.status_code == 200
    data = r.json()
    assert data["production_model"]["model_name"] == "marinex-unet-v1.0.0"
    assert data["calibration"]["temperature"] > 0
    assert data["final_test_results"]


def test_ml_validation(client):
    r = client.get("/api/v1/ml/validation")
    assert r.status_code == 200
    data = r.json()
    assert data["robustness"]
    assert data["lookalike"]
    assert data["error_taxonomy"]


def test_ml_explainability_validation(client):
    r = client.get("/api/v1/explainability/validation")
    assert r.status_code == 200
    data = r.json()
    assert "sanity" in data
    assert data["sanity"] is not None


def test_demo_case_c_multi_candidate(client):
    r = client.post("/api/v1/demo/cases/case_c_multi_candidate")
    assert r.status_code == 200
    data = r.json()
    assert data["case_id"] == "case_c_multi_candidate"
    assert data["total_vessels_scanned"] >= 1
    assert data["candidates"]
    assert data["conclusion"] in {"CANDIDATE_IDENTIFIED", "INSUFFICIENT_EVIDENCE", "NO_RELIABLE_CANDIDATE"}


def test_demo_case_d_no_candidate(client):
    r = client.post("/api/v1/demo/cases/case_d_no_candidate")
    assert r.status_code == 200
    data = r.json()
    assert data["conclusion"] == "NO_RELIABLE_CANDIDATE"
    assert data["candidates"] == []


def test_demo_case_b_low_confidence(client):
    r = client.post("/api/v1/demo/cases/case_b_low_confidence")
    assert r.status_code == 200
    data = r.json()
    assert data["detection_status"] in {"LOW_CONFIDENCE", "NO_SLICKS", "SLICKS_FOUND"}
    assert data["automatic_attribution_run"] is False
    assert data["status_label"] == "DEMO_DATA"


def test_demo_case_a_high_confidence(client):
    r = client.post("/api/v1/demo/cases/case_a_high_confidence")
    assert r.status_code == 200
    data = r.json()
    assert data["total_vessels_scanned"] >= 1
    assert any(c["confidence"] == "HIGH" for c in data["candidates"])


def test_demo_case_incident_complete(client):
    r = client.post("/api/v1/demo/cases/incident_complete")
    assert r.status_code == 200
    data = r.json()
    arts = data["artifacts"]
    assert arts["incident"]
    assert arts["scene"]
    assert arts["detection"] >= 1
    assert arts["report"].startswith("REP-")
    assert arts["evidence_ledger"] >= 4
    assert {"ENVIRONMENT", "DRIFT", "AIS", "CANDIDATE"}.issubset(data["evidence_types"])
    assert "# MARINeX Forensic Investigation Report" in data["report_markdown"]


def test_demo_case_unknown(client):
    r = client.post("/api/v1/demo/cases/bogus_case")
    assert r.status_code == 404