"""Light preprocessing: rolling features, derived columns, scaling.

Kept deliberately simple. Heavy feature engineering lives in the individual
signal modules (signals/, artifacts/, etc.).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..utils.config import load_yaml
from ..utils.logging import get_logger
from ..utils.paths import ensure_dir, resolve

log = get_logger("preprocess")


def add_rolling_features(df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    out = df.sort_values(["participant_id", "date"]).copy()
    grouped = out.groupby("participant_id", group_keys=False)
    for col in ["resting_hr", "hrv_rmssd", "hrv_sdnn", "sleep_efficiency", "step_count"]:
        if col not in out.columns:
            continue
        out[f"{col}_roll{window}_mean"] = grouped[col].transform(
            lambda s: s.rolling(window, min_periods=2).mean()
        )
        out[f"{col}_roll{window}_std"] = grouped[col].transform(
            lambda s: s.rolling(window, min_periods=2).std()
        )
    return out


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add a few derived columns when their source columns are present.

    Missing source columns are skipped silently. Callers that depend on
    specific derived columns should check before consuming them.
    """
    out = df.copy()
    if "wearable_minutes" in out.columns:
        out["wearable_coverage_frac"] = out["wearable_minutes"] / 1440.0
    if "active_minutes" in out.columns:
        out["motion_proxy"] = out["active_minutes"] / 240.0
    if "heat_index" in out.columns:
        out["heat_load"] = np.maximum(0, out["heat_index"] - 26)
    if "sleep_duration" in out.columns:
        out["sleep_deficit"] = np.maximum(0, 7 - out["sleep_duration"])
    return out


def preprocess(synthetic_csv: str | None = None, out_csv: str | None = None) -> pd.DataFrame:
    cfg = load_yaml("configs/default.yaml")
    in_path = resolve(synthetic_csv or cfg.paths.synthetic_csv)
    out_path = resolve(out_csv or cfg.paths.processed_csv)

    df = pd.read_csv(in_path)
    df = add_derived_columns(df)
    df = add_rolling_features(df)
    ensure_dir(out_path.parent)
    df.to_csv(out_path, index=False)
    log.info("Preprocessed → %s (rows=%d, cols=%d)", out_path, len(df), df.shape[1])
    return df


if __name__ == "__main__":
    preprocess()
