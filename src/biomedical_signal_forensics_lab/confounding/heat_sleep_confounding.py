"""A focused module on heat × sleep confounding."""
from __future__ import annotations

import numpy as np
import pandas as pd


def per_participant_heat_sleep(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pid, g in df.groupby("participant_id"):
        if len(g) < 7:
            continue
        h = g["heat_index"].to_numpy()
        s = g["sleep_efficiency"].to_numpy()
        if np.std(h) < 1e-6 or np.std(s) < 1e-6:
            continue
        rows.append(
            {
                "participant_id": pid,
                "heat_sleep_r": float(np.corrcoef(h, s)[0, 1]),
                "mean_heat_index": float(h.mean()),
                "mean_sleep_efficiency": float(s.mean()),
            }
        )
    return pd.DataFrame(rows)


def cohort_summary(df: pd.DataFrame) -> dict:
    per = per_participant_heat_sleep(df)
    if per.empty:
        return {}
    return {
        "median_heat_sleep_r": float(per["heat_sleep_r"].median()),
        "n_participants_with_negative_effect": int((per["heat_sleep_r"] < -0.2).sum()),
        "n_participants_evaluated": int(len(per)),
    }
