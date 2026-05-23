"""Missingness as signal: clustering, consecutive dropout, state dependence."""
from __future__ import annotations

import numpy as np
import pandas as pd


def consecutive_run_lengths(flags: np.ndarray) -> np.ndarray:
    """Return lengths of consecutive 1-runs in a binary array."""
    if flags.size == 0:
        return np.array([], dtype=int)
    runs: list[int] = []
    run = 0
    for f in flags:
        if f:
            run += 1
        else:
            if run > 0:
                runs.append(run)
            run = 0
    if run > 0:
        runs.append(run)
    return np.array(runs, dtype=int)


def per_participant_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pid, g in df.groupby("participant_id"):
        g_sorted = g.sort_values("date")
        flags = g_sorted["missing_wearable_flag"].fillna(0).astype(int).to_numpy()
        runs = consecutive_run_lengths(flags)
        rows.append(
            {
                "participant_id": pid,
                "miss_rate": float(flags.mean()) if flags.size else float("nan"),
                "max_consecutive_missing": int(runs.max()) if runs.size else 0,
                "mean_consecutive_missing": float(runs.mean()) if runs.size else 0.0,
                "n_missing_episodes": int(runs.size),
            }
        )
    return pd.DataFrame(rows)


def state_dependent_missingness(df: pd.DataFrame) -> pd.DataFrame:
    """Does missingness correlate with stress / poor sleep / heat?"""
    out = []
    for state in ("stress_proxy", "sleep_efficiency", "heat_index"):
        if state not in df.columns:
            continue
        miss = df["missing_wearable_flag"].astype(float).to_numpy()
        s = df[state].to_numpy()
        if np.std(s) < 1e-6 or np.std(miss) < 1e-6:
            r = float("nan")
        else:
            r = float(np.corrcoef(miss, s)[0, 1])
        out.append({"state": state, "miss_correlation_r": r})
    return pd.DataFrame(out)
