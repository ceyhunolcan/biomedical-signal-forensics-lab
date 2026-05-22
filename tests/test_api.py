"""API smoke tests. Skip cleanly if FastAPI or its test client isn't installed."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import app  # noqa: E402


client = TestClient(app)


def test_root_returns_project_blurb():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "biomedical-signal-forensics-lab" in body.get("name", "").lower() or "signal" in str(body).lower()


def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_audit_signal_returns_score():
    payload = {
        "participant_id": "p001",
        "summary": {
            "resting_hr_mean": 62.0, "resting_hr_std": 3.0,
            "hrv_rmssd_mean": 45.0, "hrv_rmssd_std": 6.0,
            "sleep_duration_mean": 7.2, "sleep_efficiency_mean": 0.87,
            "wearable_minutes_mean": 1200, "missing_fraction": 0.05,
            "artifact_burden_mean": 0.1, "device_type": "A",
            "temperature_c_mean": 22.0, "aqi_mean": 45.0,
        },
    }
    r = client.post("/audit-signal", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["trust_score"] <= 100
    assert "disclaimer" in body
