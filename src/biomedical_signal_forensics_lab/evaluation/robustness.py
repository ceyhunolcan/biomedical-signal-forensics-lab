"""Robustness: how stable is a metric under input perturbations?"""
from __future__ import annotations

import numpy as np
import pandas as pd


def perturbation_stability(scorer, df: pd.DataFrame, columns: list[str],
                           noise_std: float = 0.05, n_trials: int = 10,
                           seed: int = 0) -> float:
    """Add Gaussian noise to selected columns, see how much the score moves.

    A seeded local RNG is used so successive calls with the same seed produce
    identical results. Returns NaN if the scorer fails on every perturbation.
    """
    rng = np.random.default_rng(seed)
    base = float(scorer(df).overall_trust_score)
    if base != base:  # NaN
        return float("nan")
    diffs = []
    for trial in range(n_trials):
        perturbed = df.copy()
        for c in columns:
            if c in perturbed.columns:
                col_std = float(perturbed[c].std())
                if col_std != col_std:  # NaN std
                    col_std = 0.0
                perturbed[c] = perturbed[c] + rng.normal(
                    0, noise_std * (col_std + 1e-6), len(perturbed)
                )
        try:
            new = float(scorer(perturbed).overall_trust_score)
        except Exception:  # noqa: BLE001
            continue
        if new == new:  # not NaN
            diffs.append(abs(new - base))
    if not diffs:
        return float("nan")
    return float(1.0 - min(np.mean(diffs) / 100.0, 1.0))
