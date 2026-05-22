"""The trust score must stay in [0, 100] and respond sensibly to bad inputs."""
import numpy as np
import pandas as pd

from src.reliability.biomarker_trust_score import DigitalBiomarkerTrustScore


def _toy_frame(seed=0, quality=0.85, artifacts=0.1, missingness=0.05, pid="p001"):
    rng = np.random.default_rng(seed)
    n = 60
    return pd.DataFrame({
        "participant_id": [pid] * n,
        "date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "device_type": ["A"] * n,
        "resting_hr": 60 + rng.normal(0, 2, n),
        "hrv_rmssd": 45 + rng.normal(0, 4, n),
        "sleep_duration": 7.0 + rng.normal(0, 0.4, n),
        "sleep_efficiency": np.clip(0.85 + rng.normal(0, 0.03, n), 0, 1),
        "step_count": 8000 + rng.normal(0, 500, n),
        "wearable_minutes": 1200 + rng.normal(0, 60, n),
        "temperature_c": 22 + rng.normal(0, 2, n),
        "aqi": 50 + rng.normal(0, 5, n),
        "missing_wearable_flag": (rng.random(n) < missingness).astype(int),
        "signal_quality_ground_truth": np.full(n, quality),
        "artifact_burden_ground_truth": np.full(n, artifacts),
        "reliability_ground_truth": np.full(n, 1 - artifacts),
    })


def test_score_is_in_zero_to_hundred():
    df = _toy_frame()
    report = DigitalBiomarkerTrustScore().score(df)
    assert 0.0 <= report.overall_trust_score <= 100.0


def test_categories_are_valid():
    df = _toy_frame()
    report = DigitalBiomarkerTrustScore().score(df)
    assert report.category in {"high", "moderate", "low", "unreliable"}


def test_clean_signal_scores_higher_than_messy():
    clean = DigitalBiomarkerTrustScore().score(_toy_frame(quality=0.9, artifacts=0.05, missingness=0.02))
    messy = DigitalBiomarkerTrustScore().score(_toy_frame(quality=0.3, artifacts=0.7, missingness=0.5))
    assert clean.overall_trust_score > messy.overall_trust_score


def test_cohort_scores_returns_frame():
    df = pd.concat([_toy_frame(seed=0, pid="p001"), _toy_frame(seed=1, pid="p002")])
    out = DigitalBiomarkerTrustScore().cohort_scores(df)
    assert "overall_trust_score" in out.columns
    assert len(out) == 2
    assert out["overall_trust_score"].between(0, 100).all()


def test_component_keys_present():
    df = _toy_frame()
    report = DigitalBiomarkerTrustScore().score(df)
    for key in ("signal_quality_score", "artifact_burden_score", "temporal_stability_score",
                "missingness_risk_score", "device_bias_score", "confounding_risk_score"):
        assert hasattr(report.components, key)
