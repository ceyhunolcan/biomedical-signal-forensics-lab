"""Change-point detection on participant time-series.

Firmware updates, manufacturer pipeline changes, and silent algorithm swaps
introduce step changes in wearable-derived signals. The reliability stack
already catches these as "low temporal stability," but never attributes them
to a discrete event. This module produces explicit change-point timestamps
and a before-vs-after stratification.

Two methods:

1. `bocpd`: a Bayesian online change-point detector with a constant hazard
   prior and a Normal-Inverse-Gamma model of run-length means. The full
   message-passing recursion is implemented in numpy with light bookkeeping.
2. `binary_segmentation`: a fast offline alternative that recursively splits
   on the most likely change-point under a sum-of-squared-errors criterion,
   stopping when the proposed segment fails an F-test.

The two methods agree on textbook step changes (see tests). They disagree on
ambiguous drifts, where bocpd is more conservative.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ChangePoint:
    index: int
    score: float
    before_mean: float
    after_mean: float
    delta: float
    method: str

    def to_dict(self) -> dict:
        return {
            "index": self.index, "score": round(self.score, 4),
            "before_mean": round(self.before_mean, 4),
            "after_mean": round(self.after_mean, 4),
            "delta": round(self.delta, 4), "method": self.method,
        }


# ---------------------------------------------------------------------------
# BOCPD (Bayesian online change-point detection)
# ---------------------------------------------------------------------------

def _student_t_pdf(x: float, mu: float, kappa: float, alpha: float, beta: float) -> float:
    """Posterior predictive of a Normal-Inverse-Gamma model is Student-t.
    See Murphy (2007), 'Conjugate Bayesian analysis of the Gaussian distribution'.
    """
    df = 2.0 * alpha
    scale_sq = beta * (kappa + 1.0) / (alpha * kappa)
    z = (x - mu) ** 2 / scale_sq
    # Student-t log-pdf, then exponentiate
    from math import lgamma, log, pi, exp
    log_norm = lgamma((df + 1) / 2) - lgamma(df / 2) - 0.5 * (log(df) + log(pi) + log(scale_sq))
    log_pdf = log_norm - ((df + 1) / 2) * log(1.0 + z / df)
    return float(exp(log_pdf))


def bocpd(values: np.ndarray, hazard: float = 1.0 / 50.0,
          mu0: float | None = None, kappa0: float = 1.0,
          alpha0: float = 1.0, beta0: float = 1.0,
          min_collapse: int = 5) -> list[ChangePoint]:
    """Bayesian online change-point detection.

    NaN samples are removed before processing. If you need to preserve
    absolute indices, mask externally before calling.

    Parameters
    ----------
    values
        1D array of observations.
    hazard
        Constant prior probability of a change at each step. 1/50 ≈ "one
        expected change per 50 samples". Lower = more conservative.
    mu0, kappa0, alpha0, beta0
        Normal-Inverse-Gamma prior hyperparameters. If `mu0` is None, it is
        initialized to the mean of the first 5 observations. Defaults
        elsewhere are weakly informative.
    min_collapse
        Required drop in the MAP run length to register a change-point. A
        change at time t shows up as `argmax(R_t)` collapsing from a large
        value (the length of the current stationary regime) back to 0 or 1.
    """
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    n = len(values)
    if n < 4:
        return []
    if mu0 is None:
        mu0 = float(np.mean(values[:min(5, n)]))
    R = np.array([1.0])
    mu = np.array([mu0])
    kappa = np.array([kappa0])
    alpha = np.array([alpha0])
    beta = np.array([beta0])

    found: list[ChangePoint] = []
    prev_map = 0

    for t in range(1, n + 1):
        x = float(values[t - 1])
        pred = np.array([_student_t_pdf(x, mu[i], kappa[i], alpha[i], beta[i])
                         for i in range(len(R))])
        growth = R * pred * (1.0 - hazard)
        change = float(np.sum(R * pred * hazard))
        R = np.concatenate([[change], growth])
        s = R.sum()
        if s > 0:
            R = R / s
        new_mu = np.concatenate([[mu0], (kappa * mu + x) / (kappa + 1)])
        new_kappa = np.concatenate([[kappa0], kappa + 1])
        new_alpha = np.concatenate([[alpha0], alpha + 0.5])
        new_beta = np.concatenate([[beta0],
                                   beta + (kappa * (x - mu) ** 2) / (2 * (kappa + 1))])
        mu, kappa, alpha, beta = new_mu, new_kappa, new_alpha, new_beta

        if len(R) > 200:
            R = R[:200]; mu = mu[:200]; kappa = kappa[:200]
            alpha = alpha[:200]; beta = beta[:200]
            R = R / R.sum()

        # MAP run-length collapse detection
        map_rl = int(np.argmax(R))
        if prev_map - map_rl >= min_collapse and t >= 5 and t <= n - 3:
            idx = t - 1
            before_mean = float(values[max(0, idx - 10):idx].mean())
            after_mean = float(values[idx:min(n, idx + 10)].mean())
            found.append(ChangePoint(
                index=idx, score=float(prev_map - map_rl),
                before_mean=before_mean, after_mean=after_mean,
                delta=after_mean - before_mean, method="bocpd",
            ))
            prev_map = map_rl
        else:
            prev_map = map_rl
    return found


# ---------------------------------------------------------------------------
# Binary segmentation (offline, fast, easy to interpret)
# ---------------------------------------------------------------------------

def _best_split(values: np.ndarray) -> tuple[int, float]:
    """Return (split_index, sse_reduction). split_index is the start of the right segment."""
    n = len(values)
    if n < 4:
        return -1, 0.0
    total_sse = float(((values - values.mean()) ** 2).sum())
    best_i, best_red = -1, 0.0
    cum = np.cumsum(values)
    cum2 = np.cumsum(values ** 2)
    for i in range(2, n - 2):
        left_n = i
        right_n = n - i
        left_sum = cum[i - 1]; left_sum2 = cum2[i - 1]
        right_sum = cum[-1] - left_sum; right_sum2 = cum2[-1] - left_sum2
        left_sse = left_sum2 - left_sum ** 2 / left_n
        right_sse = right_sum2 - right_sum ** 2 / right_n
        red = total_sse - (left_sse + right_sse)
        if red > best_red:
            best_red, best_i = float(red), i
    return best_i, best_red


def binary_segmentation(values: np.ndarray, min_segment: int = 7,
                         f_stat_threshold: float = 8.0,
                         detrend: bool = False) -> list[ChangePoint]:
    """Recursive binary segmentation with an F-statistic stopping rule.

    `f_stat_threshold` corresponds to a fairly aggressive p ~ 0.005 floor for
    typical sample sizes; raise for more conservative detection.

    NaN samples are stripped before processing. If `detrend=True`, a linear
    trend is subtracted from the series first; this helps avoid spurious
    change-points on slow continuous drifts (a known weakness of step-change
    detectors).
    """
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    n = len(values)
    if n < min_segment * 2:
        return []

    if detrend:
        x = np.arange(n, dtype=float)
        slope = np.polyfit(x, values, 1)[0]
        intercept = values.mean() - slope * x.mean()
        values = values - (slope * x + intercept) + values.mean()

    found: list[ChangePoint] = []

    def _recurse(lo: int, hi: int) -> None:
        segment = values[lo:hi]
        if len(segment) < min_segment * 2:
            return
        i, red = _best_split(segment)
        if i < 0:
            return
        # F-stat: SSE reduction relative to residual SSE
        left = segment[:i]; right = segment[i:]
        if len(left) < min_segment or len(right) < min_segment:
            return
        rss = float(((left - left.mean()) ** 2).sum()
                    + ((right - right.mean()) ** 2).sum())
        if rss <= 0:
            f_stat = float("inf")
        else:
            f_stat = (red / 1) / (rss / (len(segment) - 2))
        if f_stat < f_stat_threshold:
            return
        idx_global = lo + i
        before_mean = float(left.mean())
        after_mean = float(right.mean())
        found.append(ChangePoint(
            index=idx_global, score=float(f_stat),
            before_mean=before_mean, after_mean=after_mean,
            delta=after_mean - before_mean, method="binary_segmentation",
        ))
        _recurse(lo, idx_global)
        _recurse(idx_global, hi)

    _recurse(0, n)
    return sorted(found, key=lambda cp: cp.index)


# ---------------------------------------------------------------------------
# Per-participant scan over a long-format daily-summary frame
# ---------------------------------------------------------------------------

def scan_cohort(df: pd.DataFrame, metric: str,
                method: str = "binary_segmentation",
                **kwargs) -> pd.DataFrame:
    """Run change-point detection for every participant's series of `metric`."""
    rows = []
    detector = bocpd if method == "bocpd" else binary_segmentation
    for pid, g in df.groupby("participant_id"):
        s = g.sort_values("date")[metric].to_numpy()
        s = s[~np.isnan(s)]
        if len(s) < 14:
            continue
        cps = detector(s, **kwargs)
        for cp in cps:
            rows.append({"participant_id": pid, "metric": metric, **cp.to_dict()})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Before/after stratification
# ---------------------------------------------------------------------------

def stratify_before_after(values: np.ndarray, cp_index: int) -> dict:
    """Return summary statistics for the before and after segments."""
    if cp_index <= 0 or cp_index >= len(values):
        return {}
    before = values[:cp_index]; after = values[cp_index:]
    return {
        "before_n": int(len(before)),
        "before_mean": float(np.mean(before)),
        "before_std": float(np.std(before, ddof=1) if len(before) > 1 else float("nan")),
        "after_n": int(len(after)),
        "after_mean": float(np.mean(after)),
        "after_std": float(np.std(after, ddof=1) if len(after) > 1 else float("nan")),
        "delta_mean": float(np.mean(after) - np.mean(before)),
    }
