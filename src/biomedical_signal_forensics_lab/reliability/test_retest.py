"""Test-retest reliability for daily-summary time series.

Three functions, in increasing order of methodological seriousness:

- `split_half_correlation`: Pearson between the first half and the second
  half of a single participant's series. Quick, simple, suitable for
  ranking participants. Single point estimate; no CI.

- `week_pair_correlation`: For each pair of adjacent non-overlapping weeks
  within a participant, correlate the within-week means. Standard
  test-retest formulation when daily measurements are pooled by week.

- `cohort_test_retest`: Pool participants and report between-participant
  test-retest reliability of any weekly aggregate of choice. Returns a
  point estimate plus a participant-level bootstrap 95% CI. This is the
  one to put in a paper.

The 'classical' (Shrout & Fleiss 1979) ICC is over in
intraclass_correlation.py. We deliberately keep the two separate because
they answer different questions: this module asks 'is the same participant
consistent week to week?', ICC asks 'how much of the total variance is
between-participant?'.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def split_half_correlation(values: np.ndarray) -> float:
    """Pearson correlation between the first and second halves of a series."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if values.size < 4:
        return float("nan")
    half = len(values) // 2
    a = values[:half]
    b = values[half:half * 2]
    if np.std(a) < 1e-9 or np.std(b) < 1e-9:
        return float("nan")
    r, _ = pearsonr(a, b)
    return float(r)


def per_participant(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Per-participant split-half correlation (no CI)."""
    rows = []
    for pid, g in df.groupby("participant_id"):
        g_sorted = g.sort_values("date")
        rows.append({
            "participant_id": pid,
            f"{column}_test_retest_r": split_half_correlation(
                g_sorted[column].to_numpy()
            ),
        })
    return pd.DataFrame(rows)


@dataclass
class TestRetestResult:
    metric: str
    point_estimate: float
    ci_low: float
    ci_high: float
    n_participants: int
    n_pairs: int
    method: str
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "point_estimate": round(self.point_estimate, 4) if self.point_estimate == self.point_estimate else None,
            "ci_low": round(self.ci_low, 4) if self.ci_low == self.ci_low else None,
            "ci_high": round(self.ci_high, 4) if self.ci_high == self.ci_high else None,
            "n_participants": self.n_participants,
            "n_pairs": self.n_pairs,
            "method": self.method,
            "notes": self.notes,
        }


def _weekly_means(g: pd.DataFrame, column: str) -> np.ndarray:
    """7-day non-overlapping means of `column` for one participant, sorted by date."""
    s = g.sort_values("date").copy()
    s["date"] = pd.to_datetime(s["date"])
    s = s.set_index("date")
    return s[column].resample("7D").mean().dropna().to_numpy()


def week_pair_correlation(df: pd.DataFrame, column: str,
                          min_weeks: int = 4) -> float:
    """Pool all (week_t, week_{t+1}) pairs across participants, correlate.

    A participant with at least `min_weeks` weeks of data contributes
    `n_weeks - 1` pairs. Returns the Pearson correlation across all pooled
    pairs.
    """
    pairs_x, pairs_y = [], []
    for _, g in df.groupby("participant_id"):
        w = _weekly_means(g, column)
        if len(w) < min_weeks:
            continue
        pairs_x.extend(w[:-1])
        pairs_y.extend(w[1:])
    pairs_x = np.array(pairs_x)
    pairs_y = np.array(pairs_y)
    if len(pairs_x) < 4 or np.std(pairs_x) < 1e-9 or np.std(pairs_y) < 1e-9:
        return float("nan")
    r, _ = pearsonr(pairs_x, pairs_y)
    return float(r)


def cohort_test_retest(df: pd.DataFrame, column: str,
                       method: str = "week_pair",
                       n_bootstrap: int = 500,
                       min_weeks: int = 4,
                       seed: int = 0) -> TestRetestResult:
    """Pool participants, compute a single test-retest estimate, bootstrap the CI.

    Bootstrap resamples participants (cluster bootstrap), which is the
    appropriate unit for clustered repeated-measures data.
    """
    if "participant_id" not in df.columns:
        raise KeyError("participant_id column required")
    pids = list(df["participant_id"].unique())

    # Precompute per-participant pair arrays once. Bootstrap then just
    # samples participant indices and stacks the cached arrays.
    if method == "week_pair":
        per_pid_pairs: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for pid, g in df.groupby("participant_id"):
            w = _weekly_means(g, column)
            if len(w) >= min_weeks:
                per_pid_pairs[pid] = (w[:-1].astype(float), w[1:].astype(float))
        if not per_pid_pairs:
            return TestRetestResult(
                metric=column, point_estimate=float("nan"),
                ci_low=float("nan"), ci_high=float("nan"),
                n_participants=0, n_pairs=0, method=method,
                notes=f"no participant had ≥{min_weeks} weeks of data",
            )

        def _scored(sampled_pids):
            xs = np.concatenate([per_pid_pairs[p][0] for p in sampled_pids])
            ys = np.concatenate([per_pid_pairs[p][1] for p in sampled_pids])
            if len(xs) < 4 or np.std(xs) < 1e-9 or np.std(ys) < 1e-9:
                return float("nan")
            r, _ = pearsonr(xs, ys)
            return float(r) if r == r else float("nan")

        contributing_pids = list(per_pid_pairs.keys())
        point = _scored(contributing_pids)
        n_contributing = len(contributing_pids)
        n_pairs = sum(len(x) for x, _ in per_pid_pairs.values())

    elif method == "split_half":
        per_pid_score: dict[str, float] = {}
        for pid, g in df.groupby("participant_id"):
            v = split_half_correlation(g.sort_values("date")[column].to_numpy())
            if v == v:
                per_pid_score[pid] = v
        if not per_pid_score:
            return TestRetestResult(
                metric=column, point_estimate=float("nan"),
                ci_low=float("nan"), ci_high=float("nan"),
                n_participants=0, n_pairs=0, method=method,
                notes="no participant had usable split-half data",
            )

        def _scored(sampled_pids):
            vals = [per_pid_score[p] for p in sampled_pids if p in per_pid_score]
            return float(np.mean(vals)) if vals else float("nan")

        contributing_pids = list(per_pid_score.keys())
        point = _scored(contributing_pids)
        n_contributing = len(contributing_pids)
        n_pairs = n_contributing
    else:
        raise ValueError(f"unknown method {method!r}")

    rng = np.random.default_rng(seed)
    boot = []
    n_pids = len(contributing_pids)
    for _ in range(n_bootstrap):
        sampled = list(rng.choice(contributing_pids, size=n_pids, replace=True))
        s = _scored(sampled)
        if s == s:
            boot.append(s)

    if boot:
        lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    else:
        lo, hi = float("nan"), float("nan")

    return TestRetestResult(
        metric=column,
        point_estimate=point,
        ci_low=lo,
        ci_high=hi,
        n_participants=n_contributing,
        n_pairs=n_pairs,
        method=method,
        notes=f"cluster bootstrap, n_boot={len(boot)}",
    )


def cohort_test_retest_table(df: pd.DataFrame, metrics: Iterable[str],
                             **kwargs) -> pd.DataFrame:
    """Run cohort_test_retest for several metrics and return a tidy table."""
    rows = []
    for m in metrics:
        if m not in df.columns:
            continue
        rows.append(cohort_test_retest(df, m, **kwargs).to_dict())
    return pd.DataFrame(rows)
