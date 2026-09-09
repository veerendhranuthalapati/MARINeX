import pytest
from datetime import datetime


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "MARINeX"


def test_scenes_and_detection_flow(client):
    # 1. Seed or upload scene
    seed_res = client.post("/api/v1/demo/seed")
    assert seed_res.status_code == 200

    # 2. List scenes
    scenes_res = client.get("/api/v1/scenes")
    assert scenes_res.status_code == 200
    scenes = scenes_res.json()["scenes"]
    assert len(scenes) >= 1
    scene_id = scenes[0]["id"]

    # 3. Get scene by ID
    scene_detail = client.get(f"/api/v1/scenes/{scene_id}")
    assert scene_detail.status_code == 200
    assert scene_detail.json()["id"] == scene_id

    # 4. List slicks
    slicks_res = client.get("/api/v1/slicks")
    assert slicks_res.status_code == 200
    slicks = slicks_res.json()["slicks"]
    assert len(slicks) >= 1
    slick_id = slicks[0]["id"]

    # 5. Get slick detail & GeoJSON
    slick_detail = client.get(f"/api/v1/slicks/{slick_id}")
    assert slick_detail.status_code == 200
    assert slick_detail.json()["area_km2"] > 0

    slick_geojson = client.get(f"/api/v1/slicks/{slick_id}/geojson")
    assert slick_geojson.status_code == 200
    assert slick_geojson.json()["type"] == "Feature"

    # 6. Environmental data
    env_res = client.get(f"/api/v1/environment/{slick_id}")
    assert env_res.status_code == 200
    assert env_res.json()["wind"]["speed_mps"] > 0

    # 7. Drift simulation
    drift_res = client.post(f"/api/v1/drift/{slick_id}/simulate", json={"duration_hours": 3.0, "direction": "HINDCAST"})
    assert drift_res.status_code == 200
    assert drift_res.json()["status"] == "COMPLETED"

    # 8. Attribution run
    attr_res = client.post(f"/api/v1/attribution/{slick_id}/run", json={"search_radius_km": 30.0})
    assert attr_res.status_code == 200
    candidates = attr_res.json()["candidates"]
    assert len(candidates) >= 1

    # 9. Get candidates
    cands_res = client.get(f"/api/v1/candidates/{slick_id}")
    assert cands_res.status_code == 200
    assert len(cands_res.json()) >= 1

    # 10. Investigation status & update
    inv_res = client.get(f"/api/v1/investigations/{slick_id}")
    assert inv_res.status_code == 200

    patch_res = client.patch(f"/api/v1/investigations/{slick_id}", json={"analyst_notes": "Priority target verified"})
    assert patch_res.status_code == 200

    # 11. Report generation & markdown export
    rep_res = client.post(f"/api/v1/reports/{slick_id}/generate", json={"analyst_name": "Test Inspector"})
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert "report_id" in rep_data
    assert len(rep_data["observed_facts"]) > 0

    md_res = client.get(f"/api/v1/reports/{slick_id}/markdown")
    assert md_res.status_code == 200
    assert "MARINeX Forensic Investigation Report" in md_res.text
