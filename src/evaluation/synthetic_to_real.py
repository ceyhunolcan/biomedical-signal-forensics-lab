"""Comparison harness for synthetic-to-real generalization.

This module is a stub: the framework is designed so that a real dataset
can replace the synthetic one through the same column schema. The function
below documents the contract.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_REAL_COLUMNS = (
    "participant_id", "date", "resting_hr", "hrv_rmssd",
    "step_count", "sleep_duration", "sleep_efficiency",
    "wearable_minutes", "device_type",
)


def check_real_schema(df: pd.DataFrame) -> dict:
    missing = [c for c in REQUIRED_REAL_COLUMNS if c not in df.columns]
    return {"ready_for_audit": not missing, "missing_columns": missing}
