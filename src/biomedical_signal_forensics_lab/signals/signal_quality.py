"""Aggregate signal-quality scoring across ECG, PPG, and daily summaries."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import ecg_processing as ecg
from . import ppg_processing as ppg


SQI_COLUMNS = ("window_idx", "ecg_sqi", "ppg_sqi", "ppg_motion")


def per_window_sqi(ecg_arr: np.ndarray, ppg_arr: np.ndarray,
                   ecg_fs: int, ppg_fs: int) -> pd.DataFrame:
    n = min(len(ecg_arr), len(ppg_arr))
    if n == 0:
        return pd.DataFrame(columns=list(SQI_COLUMNS))
    rows = []
    for i in range(n):
        rows.append(
            {
                "window_idx": i,
                "ecg_sqi": ecg.signal_quality_index(ecg_arr[i], ecg_fs),
                "ppg_sqi": ppg.signal_quality_index(ppg_arr[i], ppg_fs),
                "ppg_motion": ppg.motion_artifact_score(ppg_arr[i], ppg_fs),
            }
        )
    return pd.DataFrame(rows)


def daily_signal_quality(df: pd.DataFrame) -> pd.Series:
    """A simple per-day quality estimate from wear-time and motion proxy.

    Missing source columns are treated as 'no information'. Returns a Series
    of NaN of the same length as `df` when both source columns are absent.
    """
    if "wearable_minutes" not in df.columns and "active_minutes" not in df.columns:
        return pd.Series([float("nan")] * len(df), name="daily_signal_quality")
    coverage = (df["wearable_minutes"].fillna(0) / 1440.0
                if "wearable_minutes" in df.columns
                else pd.Series([0.5] * len(df)))
    motion_pen = ((df["active_minutes"].fillna(0) / 240.0).clip(0, 1)
                  if "active_minutes" in df.columns
                  else pd.Series([0.0] * len(df)))
    sq = np.clip(0.95 * coverage - 0.25 * motion_pen, 0.0, 1.0)
    return sq.rename("daily_signal_quality")
