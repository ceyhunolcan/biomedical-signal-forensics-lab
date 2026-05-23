"""Activity / step-count reliability."""
from __future__ import annotations

import numpy as np
import pandas as pd


def step_consistency(steps: np.ndarray) -> float:
    if steps.size < 3 or np.mean(steps) < 1:
        return float("nan")
    cov = float(np.std(steps) / (np.mean(steps) + 1e-6))
    return float(np.clip(1.0 - cov, 0.0, 1.0))


def activity_artifact_risk(active_minutes: np.ndarray) -> float:
    if active_minutes.size == 0:
        return float("nan")
    return float(np.clip(np.mean(active_minutes > 120), 0.0, 1.0))


def active_minute_reliability(active: np.ndarray) -> float:
    if active.size < 3:
        return float("nan")
    return float(np.clip(1.0 - np.std(active) / 60.0, 0.0, 1.0))


def summarize_activity(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pid, g in df.groupby("participant_id"):
        rows.append(
            {
                "participant_id": pid,
                "step_consistency": step_consistency(g["step_count"].to_numpy()),
                "activity_artifact_risk": activity_artifact_risk(
                    g["active_minutes"].to_numpy()
                ),
                "active_minute_reliability": active_minute_reliability(
                    g["active_minutes"].to_numpy()
                ),
            }
        )
    return pd.DataFrame(rows)
