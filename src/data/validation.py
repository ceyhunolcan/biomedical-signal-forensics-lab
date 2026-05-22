"""Validation. Checks physiological plausibility and schema."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS: tuple[str, ...] = (
    "participant_id", "date",
    "resting_hr", "hrv_rmssd", "hrv_sdnn",
    "step_count", "active_minutes",
    "sleep_duration", "sleep_efficiency", "stress_proxy",
    "temperature_c", "humidity", "aqi", "heat_index",
    "wearable_minutes", "missing_wearable_flag",
    "signal_quality_ground_truth", "artifact_burden_ground_truth",
    "reliability_ground_truth",
)

PHYSIO_RANGES = {
    "resting_hr": (30, 130),
    "hrv_rmssd": (0, 250),
    "hrv_sdnn": (0, 300),
    "step_count": (0, 60000),
    "active_minutes": (0, 480),
    "sleep_duration": (0, 14),
    "sleep_efficiency": (0, 1),
    "temperature_c": (-20, 50),
    "humidity": (0, 100),
    "aqi": (0, 500),
}


@dataclass
class ValidationResult:
    ok: bool
    missing_columns: list[str]
    range_violations: dict[str, int]
    n_rows: int
    all_nan_columns: list[str] = None  # populated by validate()

    def __post_init__(self):
        if self.all_nan_columns is None:
            self.all_nan_columns = []

    def summary(self) -> str:
        if self.ok:
            return f"OK. {self.n_rows} rows, all schema and range checks passed."
        parts = [f"{self.n_rows} rows."]
        if self.missing_columns:
            parts.append(f"Missing columns: {self.missing_columns}.")
        if self.range_violations:
            parts.append(f"Out-of-range counts: {self.range_violations}.")
        if self.all_nan_columns:
            parts.append(f"All-NaN columns: {self.all_nan_columns}.")
        return " ".join(parts)


def validate(df: pd.DataFrame, columns: Iterable[str] = REQUIRED_COLUMNS) -> ValidationResult:
    missing = [c for c in columns if c not in df.columns]
    violations: dict[str, int] = {}
    for col, (lo, hi) in PHYSIO_RANGES.items():
        if col in df.columns:
            bad = int(((df[col] < lo) | (df[col] > hi)).sum())
            if bad > 0:
                violations[col] = bad
    # An all-NaN required column passes the column-presence check but
    # carries no information. Flag it.
    all_nan = [c for c in columns if c in df.columns and df[c].isna().all()]
    return ValidationResult(
        ok=(not missing and not violations and not all_nan),
        missing_columns=missing,
        range_violations=violations,
        n_rows=len(df),
        all_nan_columns=all_nan,
    )
