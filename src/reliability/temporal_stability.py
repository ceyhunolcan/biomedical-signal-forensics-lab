"""Day-to-day stability, rolling CoV, drift."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import linregress


def rolling_cov(values: np.ndarray, window: int = 7) -> np.ndarray:
    if values.size < window:
        return np.array([])
    s = pd.Series(values)
    mean = s.rolling(window).mean()
    std = s.rolling(window).std()
    return (std / (mean + 1e-9)).to_numpy()


def drift_slope(values: np.ndarray) -> dict[str, float]:
    """Linear-regression slope and p-value of `values` vs sample index.

    NaN samples are dropped before the regression. Returns NaN slope and
    p-value when fewer than 5 finite samples remain or when the finite
    portion has effectively zero variance.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 5 or np.std(arr) < 1e-9:
        return {"slope": float("nan"), "p_value": float("nan")}
    x = np.arange(arr.size)
    res = linregress(x, arr)
    return {"slope": float(res.slope), "p_value": float(res.pvalue)}


def participant_stability(df: pd.DataFrame, column: str) -> pd.DataFrame:
    rows = []
    for pid, g in df.groupby("participant_id"):
        v = g.sort_values("date")[column].to_numpy()
        cov = rolling_cov(v)
        drift = drift_slope(v)
        rows.append(
            {
                "participant_id": pid,
                f"{column}_mean_rolling_cov": float(np.nanmean(cov)) if cov.size else float("nan"),
                f"{column}_drift_slope": drift["slope"],
                f"{column}_drift_p": drift["p_value"],
            }
        )
    return pd.DataFrame(rows)
