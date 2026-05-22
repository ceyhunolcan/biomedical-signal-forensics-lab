"""Behavioral confounders: activity → PPG, low wear → reliability."""
from __future__ import annotations

import numpy as np
import pandas as pd


def activity_vs_quality(df: pd.DataFrame) -> dict:
    if "active_minutes" not in df.columns or "signal_quality_ground_truth" not in df.columns:
        return {}
    a = df["active_minutes"].to_numpy()
    q = df["signal_quality_ground_truth"].to_numpy()
    if np.std(a) < 1e-6 or np.std(q) < 1e-6:
        return {"activity_vs_quality_r": float("nan")}
    return {"activity_vs_quality_r": float(np.corrcoef(a, q)[0, 1])}


def wear_vs_reliability(df: pd.DataFrame) -> dict:
    if "wearable_minutes" not in df.columns or "reliability_ground_truth" not in df.columns:
        return {}
    w = df["wearable_minutes"].to_numpy()
    r = df["reliability_ground_truth"].to_numpy()
    if np.std(w) < 1e-6 or np.std(r) < 1e-6:
        return {"wear_vs_reliability_r": float("nan")}
    return {"wear_vs_reliability_r": float(np.corrcoef(w, r)[0, 1])}
