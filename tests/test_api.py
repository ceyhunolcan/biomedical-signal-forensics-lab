"""API smoke tests. Skip cleanly if FastAPI or its test client isn't installed."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi.testclient import TestClient  # noqa: E402

from biomedical_signal_forensics_lab.api.main import app  # noqa: E402


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
    """Payload matches the current SignalSummary schema in src/api/schemas.py."""
    payload = {
        "participant_id": "p001",
        "n_days_observed": 14,
        "mean_resting_hr": 62.0,
        "mean_hrv_rmssd": 45.0,
        "mean_step_count": 7500.0,
        "mean_sleep_duration": 7.2,
        "mean_sleep_efficiency": 0.87,
        "mean_heat_index": 24.0,
        "missing_rate": 0.05,
        "device_type": "device_A",
        "mean_active_minutes": 60.0,
        "mean_wearable_minutes": 1200.0,
    }
    r = client.post("/audit-signal", json=payload)
    assert r.status_code == 200
    body = r.json()
    # Field is `overall_trust_score`, not `trust_score`
    score = body["overall_trust_score"]
    # Score may be None (NaN sentinel) on degenerate inputs but should be
    # a finite number on this well-formed input.
    assert score is not None
    assert 0 <= score <= 100
    # Disclaimer field is `non_clinical_disclaimer`
    assert "non_clinical_disclaimer" in body
    assert "category" in body


def test_trust_score_returns_all_components():
    """Full trust-score endpoint returns all six components."""
    payload = {
        "participant_id": "p002",
        "n_days_observed": 30,
        "mean_resting_hr": 65.0,
        "mean_hrv_rmssd": 50.0,
        "mean_step_count": 8000.0,
        "mean_sleep_duration": 7.0,
        "mean_sleep_efficiency": 0.85,
        "mean_heat_index": 22.0,
        "missing_rate": 0.10,
        "device_type": "device_A",
    }
    r = client.post("/trust-score", json=payload)
    assert r.status_code == 200
    body = r.json()
    for k in ("signal_quality_score", "artifact_burden_score",
             "temporal_stability_score", "missingness_risk_score",
             "device_bias_score", "confounding_risk_score",
             "overall_trust_score", "category", "explanation"):
        assert k in body, f"missing field: {k}"
