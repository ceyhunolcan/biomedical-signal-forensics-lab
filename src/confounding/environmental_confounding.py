"""Environmental confounders: heat, AQI, humidity."""
from __future__ import annotations

import numpy as np
import pandas as pd


PAIRS = [
    ("heat_index", "hrv_rmssd"),
    ("heat_index", "sleep_efficiency"),
    ("temperature_c", "hrv_rmssd"),
    ("aqi", "sleep_efficiency"),
    ("aqi", "sleep_duration"),
    ("humidity", "hrv_rmssd"),
]


def correlation_table(df: pd.DataFrame, pairs: list[tuple[str, str]] = PAIRS) -> pd.DataFrame:
    rows = []
    for a, b in pairs:
        if a in df.columns and b in df.columns:
            sub = df[[a, b]].dropna()
            if len(sub) >= 5 and np.std(sub[a]) > 1e-6 and np.std(sub[b]) > 1e-6:
                r = float(np.corrcoef(sub[a], sub[b])[0, 1])
                rows.append(
                    {"environmental_var": a, "biomarker": b, "pearson_r": r, "n": len(sub)}
                )
    return pd.DataFrame(rows).sort_values("pearson_r", key=lambda s: s.abs(), ascending=False)


def top_confounder(corr_df: pd.DataFrame) -> dict:
    if corr_df.empty:
        return {}
    row = corr_df.iloc[0]
    return {
        "environmental_var": row["environmental_var"],
        "biomarker": row["biomarker"],
        "pearson_r": float(row["pearson_r"]),
    }
