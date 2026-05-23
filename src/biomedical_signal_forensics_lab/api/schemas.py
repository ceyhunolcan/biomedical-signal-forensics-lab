"""Pydantic schemas for the API."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class SignalSummary(BaseModel):
    participant_id: str
    n_days_observed: int = Field(..., ge=1, le=365)
    mean_resting_hr: float
    mean_hrv_rmssd: float
    mean_step_count: float
    mean_sleep_duration: float
    mean_sleep_efficiency: float
    mean_heat_index: float
    missing_rate: float = Field(..., ge=0.0, le=1.0)
    device_type: Optional[str] = "device_A"
    mean_active_minutes: float = 60.0
    mean_wearable_minutes: float = 1100.0


class AuditResult(BaseModel):
    participant_id: str
    signal_quality_score: Optional[float]
    artifact_burden_score: Optional[float]
    reliability_score: Optional[float]
    overall_trust_score: Optional[float]
    category: str
    warnings: list[str]
    non_clinical_disclaimer: str


class TrustScoreResult(BaseModel):
    participant_id: str
    signal_quality_score: Optional[float]
    artifact_burden_score: Optional[float]
    temporal_stability_score: Optional[float]
    missingness_risk_score: Optional[float]
    device_bias_score: Optional[float]
    confounding_risk_score: Optional[float]
    overall_trust_score: Optional[float]
    category: str
    explanation: str
    non_clinical_disclaimer: str
