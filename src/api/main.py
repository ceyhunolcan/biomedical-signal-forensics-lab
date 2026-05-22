"""FastAPI application.

Endpoints:
    GET  /              project description
    GET  /health        health check
    POST /audit-signal  quick audit from summary stats
    POST /trust-score   full Digital Biomarker Trust Score
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import FastAPI

from ..reliability.biomarker_trust_score import DigitalBiomarkerTrustScore
from .schemas import AuditResult, SignalSummary, TrustScoreResult


app = FastAPI(
    title="biomedical-signal-forensics-lab",
    description=(
        "Signal-forensics API for wearable physiological data. "
        "Non-clinical research prototype. Outputs are signal-quality "
        "estimates and methodological recommendations, not medical advice."
    ),
    version="0.3.2",
)


DISCLAIMER = (
    "Research prototype only. Not medical advice, diagnosis, treatment, "
    "or a medical device."
)


def _none_if_nan(value: float) -> float | None:
    """JSON does not represent NaN; map NaN to None for response models."""
    if value != value:  # NaN check
        return None
    return float(value)


def _summary_to_frame(s: SignalSummary) -> pd.DataFrame:
    """Inflate the summary into a tiny dataframe the scorer can consume."""
    n = max(int(s.n_days_observed), 7)
    rng = np.random.default_rng(0)
    dates = pd.date_range("2025-01-01", periods=n).astype(str)
    miss_flags = (rng.random(n) < s.missing_rate).astype(int)
    return pd.DataFrame(
        {
            "participant_id": [s.participant_id] * n,
            "date": dates,
            "resting_hr": s.mean_resting_hr + rng.normal(0, 2, n),
            "hrv_rmssd": s.mean_hrv_rmssd + rng.normal(0, 4, n),
            "hrv_sdnn": s.mean_hrv_rmssd * 0.9 + rng.normal(0, 4, n),
            "step_count": s.mean_step_count + rng.normal(0, 1000, n),
            "active_minutes": s.mean_active_minutes + rng.normal(0, 10, n),
            "sleep_duration": s.mean_sleep_duration + rng.normal(0, 0.3, n),
            "sleep_efficiency": np.clip(
                s.mean_sleep_efficiency + rng.normal(0, 0.03, n), 0.4, 0.99
            ),
            "stress_proxy": np.clip(0.3 + rng.normal(0, 0.1, n), 0, 1),
            "temperature_c": 22 + rng.normal(0, 2, n),
            "humidity": 55 + rng.normal(0, 5, n),
            "aqi": 50 + rng.normal(0, 15, n),
            "heat_index": s.mean_heat_index + rng.normal(0, 1.5, n),
            "wearable_minutes": np.where(miss_flags, 0,
                                         s.mean_wearable_minutes + rng.normal(0, 100, n)),
            "missing_wearable_flag": miss_flags,
            "signal_quality_ground_truth": np.clip(
                0.85 - 0.5 * s.missing_rate + rng.normal(0, 0.05, n), 0, 1
            ),
            "artifact_burden_ground_truth": np.clip(
                0.15 + 0.3 * (s.mean_active_minutes / 120.0) + rng.normal(0, 0.05, n), 0, 1
            ),
            "reliability_ground_truth": np.clip(
                0.85 - 0.3 * s.missing_rate + rng.normal(0, 0.05, n), 0, 1
            ),
            "device_type": [s.device_type or "device_A"] * n,
        }
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "biomedical-signal-forensics-lab",
        "description": "Non-clinical research prototype for wearable signal forensics.",
        "endpoints": ["/health", "/audit-signal", "/trust-score"],
        "disclaimer": DISCLAIMER,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/audit-signal", response_model=AuditResult)
def audit_signal(payload: SignalSummary) -> AuditResult:
    df = _summary_to_frame(payload)
    scorer = DigitalBiomarkerTrustScore()
    report = scorer.score(df)
    warnings: list[str] = []
    if payload.missing_rate > 0.2:
        warnings.append("Missingness above 20%. Interpret with caution.")
    if payload.mean_active_minutes > 150:
        warnings.append("High activity load. PPG-derived metrics likely noisy.")
    if report.overall_trust_score < 40:
        warnings.append("Trust score below 'low' threshold.")
    return AuditResult(
        participant_id=payload.participant_id,
        signal_quality_score=_none_if_nan(report.components.signal_quality_score),
        artifact_burden_score=_none_if_nan(report.components.artifact_burden_score),
        reliability_score=_none_if_nan(report.components.temporal_stability_score),
        overall_trust_score=_none_if_nan(report.overall_trust_score),
        category=report.category,
        warnings=warnings,
        non_clinical_disclaimer=DISCLAIMER,
    )


@app.post("/trust-score", response_model=TrustScoreResult)
def trust_score(payload: SignalSummary) -> TrustScoreResult:
    df = _summary_to_frame(payload)
    scorer = DigitalBiomarkerTrustScore()
    report = scorer.score(df)
    comp = report.components
    return TrustScoreResult(
        participant_id=payload.participant_id,
        signal_quality_score=_none_if_nan(comp.signal_quality_score),
        artifact_burden_score=_none_if_nan(comp.artifact_burden_score),
        temporal_stability_score=_none_if_nan(comp.temporal_stability_score),
        missingness_risk_score=_none_if_nan(comp.missingness_risk_score),
        device_bias_score=_none_if_nan(comp.device_bias_score),
        confounding_risk_score=_none_if_nan(comp.confounding_risk_score),
        overall_trust_score=_none_if_nan(report.overall_trust_score),
        category=report.category,
        explanation=report.explanation,
        non_clinical_disclaimer=DISCLAIMER,
    )
