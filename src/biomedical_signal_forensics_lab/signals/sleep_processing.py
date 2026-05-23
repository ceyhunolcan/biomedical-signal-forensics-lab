"""Sleep-summary reliability metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd


def regularity_index(durations: np.ndarray) -> float:
    """1 - normalized std of sleep duration. Higher = more regular."""
    if durations.size < 3:
        return float("nan")
    std = float(np.std(durations))
    return float(np.clip(1.0 - std / 4.0, 0.0, 1.0))


def efficiency_reliability(efficiencies: np.ndarray) -> float:
    if efficiencies.size < 3:
        return float("nan")
    return float(np.clip(1.0 - 2 * np.std(efficiencies), 0.0, 1.0))


def duration_deviation(durations: np.ndarray, target_hours: float = 7.5) -> float:
    if durations.size == 0:
        return float("nan")
    return float(np.mean(np.abs(durations - target_hours)))


def summarize_sleep(df: pd.DataFrame) -> pd.DataFrame:
    out_rows = []
    for pid, g in df.groupby("participant_id"):
        out_rows.append(
            {
                "participant_id": pid,
                "sleep_regularity": regularity_index(g["sleep_duration"].to_numpy()),
                "efficiency_reliability": efficiency_reliability(
                    g["sleep_efficiency"].to_numpy()
                ),
                "duration_deviation": duration_deviation(
                    g["sleep_duration"].to_numpy()
                ),
            }
        )
    return pd.DataFrame(out_rows)
