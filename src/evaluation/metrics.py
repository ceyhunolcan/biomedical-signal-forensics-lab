"""Common metrics used by the leaderboard and the audit report."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score, f1_score


def auroc(y_true, y_score) -> float:
    try:
        return float(roc_auc_score(y_true, y_score))
    except ValueError:
        return float("nan")


def f1(y_true, y_pred) -> float:
    try:
        return float(f1_score(y_true, y_pred))
    except ValueError:
        return float("nan")


def expected_calibration_error(y_true, y_prob, n_bins: int = 10) -> float:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    n = len(y_prob)
    if n == 0:
        return float("nan")
    bins = np.linspace(0, 1, n_bins + 1)
    # Clip so that y_prob == 1.0 falls in the last bin instead of off the end.
    idx = np.clip(np.digitize(y_prob, bins) - 1, 0, n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        mask = idx == b
        if mask.sum() == 0:
            continue
        conf = float(y_prob[mask].mean())
        acc = float((y_true[mask] == (y_prob[mask] > 0.5)).mean())
        ece += (mask.sum() / n) * abs(conf - acc)
    return float(ece)
