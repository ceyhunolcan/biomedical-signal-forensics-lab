"""Reliability-diagram-style calibration data."""
from __future__ import annotations

import numpy as np


def reliability_curve(y_true, y_prob, n_bins: int = 10):
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    bins = np.linspace(0, 1, n_bins + 1)
    # Clip so that y_prob == 1.0 falls in the last bin
    idx = np.clip(np.digitize(y_prob, bins) - 1, 0, n_bins - 1)
    conf, acc = [], []
    for b in range(n_bins):
        mask = idx == b
        if mask.sum() == 0:
            continue
        conf.append(float(y_prob[mask].mean()))
        acc.append(float((y_true[mask] == (y_prob[mask] > 0.5)).mean()))
    return np.array(conf), np.array(acc)
