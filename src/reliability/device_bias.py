"""Estimate device-class bias on key biomarkers."""
from __future__ import annotations

import numpy as np
import pandas as pd


def per_column_bias(df: pd.DataFrame, columns: list[str],
                    device_col: str = "device_type",
                    reference: str | None = None) -> pd.DataFrame:
    """For each device class, report mean - reference_mean for each column."""
    if device_col not in df.columns:
        return pd.DataFrame(columns=["device", "reference", "column", "mean_diff", "n_obs"])
    devices = sorted(df[device_col].dropna().unique())
    if not devices:
        return pd.DataFrame(columns=["device", "reference", "column", "mean_diff", "n_obs"])
    if reference is None:
        reference = devices[0]
    elif reference not in devices:
        # Caller named a reference that doesn't appear in the data. Falling
        # back silently would be confusing; raise so the user notices.
        raise KeyError(
            f"reference device {reference!r} not found in {device_col} column "
            f"(present: {devices})"
        )
    ref_means = df[df[device_col] == reference][columns].mean()
    rows = []
    for d in devices:
        sub = df[df[device_col] == d][columns]
        diff = sub.mean() - ref_means
        for col, value in diff.items():
            rows.append(
                {
                    "device": d,
                    "reference": reference,
                    "column": col,
                    "mean_diff": float(value) if value == value else float("nan"),
                    "n_obs": int(len(sub)),
                }
            )
    return pd.DataFrame(rows)


def bias_severity(bias_df: pd.DataFrame) -> float:
    """Aggregate device-bias severity in [0, 1].

    Defined as the maximum absolute mean_diff across rows, divided by a
    fixed scale (10 bpm / 10 ms) and clipped to [0, 1]. This is a simple
    heuristic, not a standardized effect size, so it depends on the unit of
    `mean_diff`. For metrics whose natural scale differs from 10, pre-scale
    or use a different aggregator.

    Returns 0.0 on an empty frame.
    """
    if bias_df is None or bias_df.empty:
        return 0.0
    return float(np.clip(bias_df["mean_diff"].abs().max() / 10.0, 0.0, 1.0))
