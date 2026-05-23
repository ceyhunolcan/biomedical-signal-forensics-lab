"""Isolation Forest anomaly detector + logistic / random forest baselines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


@dataclass
class ModelResult:
    name: str
    auroc: float
    f1: float
    notes: str


FEATURE_COLUMNS: tuple[str, ...] = (
    "resting_hr", "hrv_rmssd", "hrv_sdnn",
    "step_count", "active_minutes",
    "sleep_duration", "sleep_efficiency",
    "stress_proxy", "heat_index", "humidity", "aqi",
    "wearable_minutes",
)


def _prepare(df: pd.DataFrame, target: str = "signal_quality_ground_truth",
             threshold: float = 0.7):
    if target not in df.columns:
        raise KeyError(
            f"target column {target!r} not found in dataframe; "
            f"available columns include {list(df.columns)[:8]}…"
        )
    feats = [c for c in FEATURE_COLUMNS if c in df.columns]
    if not feats:
        raise ValueError("No feature columns from FEATURE_COLUMNS are present in the input.")
    # Fill NaN with per-column median, falling back to 0.0 if the column is all-NaN
    X_df = df[feats].copy()
    medians = X_df.median(numeric_only=True)
    medians = medians.fillna(0.0)
    X = X_df.fillna(medians).to_numpy(dtype=float)
    y = (df[target] >= threshold).astype(int).to_numpy()
    return X, y, feats


def train_baselines(df: pd.DataFrame, seed: int = 42) -> list[ModelResult]:
    X, y, _ = _prepare(df)
    if len(np.unique(y)) < 2:
        note = (f"target is single-class (all {int(y[0]) if len(y) else 'n/a'}); "
                "cannot train supervised baselines")
        return [
            ModelResult("logistic_regression", float("nan"), float("nan"), note),
            ModelResult("random_forest", float("nan"), float("nan"), note),
            ModelResult("isolation_forest", float("nan"), float("nan"), note),
        ]
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            Xs, y, test_size=0.2, random_state=seed, stratify=y
        )
    except ValueError as exc:
        note = f"train_test_split failed: {exc}"
        return [
            ModelResult("logistic_regression", float("nan"), float("nan"), note),
            ModelResult("random_forest", float("nan"), float("nan"), note),
            ModelResult("isolation_forest", float("nan"), float("nan"), note),
        ]

    results: list[ModelResult] = []

    lr = LogisticRegression(C=1.0, max_iter=1000).fit(X_train, y_train)
    p = lr.predict_proba(X_test)[:, 1]
    results.append(ModelResult("logistic_regression",
                               roc_auc_score(y_test, p),
                               f1_score(y_test, (p > 0.5).astype(int)),
                               "linear baseline"))

    rf = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=seed)
    rf.fit(X_train, y_train)
    p = rf.predict_proba(X_test)[:, 1]
    results.append(ModelResult("random_forest",
                               roc_auc_score(y_test, p),
                               f1_score(y_test, (p > 0.5).astype(int)),
                               "nonlinear baseline"))

    iso = IsolationForest(n_estimators=200, contamination=0.2, random_state=seed)
    iso.fit(X_train)
    # convert -score (higher = more anomalous) to a probability-like ranking
    s = -iso.score_samples(X_test)
    # higher s should predict y==0 (low quality), so we invert
    try:
        results.append(ModelResult("isolation_forest",
                                   roc_auc_score(y_test, -s),
                                   f1_score(y_test, (s < np.median(s)).astype(int)),
                                   "unsupervised anomaly detector"))
    except ValueError:
        results.append(ModelResult("isolation_forest", float("nan"), float("nan"),
                                   "single-class fold"))
    return results
