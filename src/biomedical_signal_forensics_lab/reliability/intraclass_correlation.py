"""ICC(2,1): two-way random, single rater, absolute agreement.

Treats each participant as a 'target' and each day as a 'rater'.
This is an unconventional use of the formula. The classical
Shrout & Fleiss (1979) ICC assumes a small fixed set of human raters scoring
each subject. Here we substitute calendar days within a participant as the
'raters'. The substitution is empirically defensible (see
`compare_to_test_retest` below): on the bundled synthetic cohort, the ICC
ranking matches the proper week-pair test-retest ranking, with the ICC
being uniformly more conservative because it counts day-to-day fluctuation
as rater disagreement.

The classical numerical implementation here was sanity-checked against the
textbook example from Shrout & Fleiss (1979) Table 1 and recovers the
published ICC(2,1) value of 0.290.

For a clinical paper the better metric is probably the bootstrap week-pair
correlation in `reliability/test_retest.py`. The ICC value here is included
for backward compatibility and as a within-participant noise-floor signal.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MethodComparison:
    """Empirical comparison of ICC(2,1) days-as-raters against bootstrap week-pair r."""
    metric: str
    icc_days_as_raters: float
    week_pair_r: float
    week_pair_ci_low: float
    week_pair_ci_high: float
    n_participants_icc: int
    n_participants_week_pair: int

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "icc_days_as_raters": round(self.icc_days_as_raters, 4)
                                  if self.icc_days_as_raters == self.icc_days_as_raters else None,
            "week_pair_r": round(self.week_pair_r, 4)
                           if self.week_pair_r == self.week_pair_r else None,
            "week_pair_ci_low": round(self.week_pair_ci_low, 4)
                                if self.week_pair_ci_low == self.week_pair_ci_low else None,
            "week_pair_ci_high": round(self.week_pair_ci_high, 4)
                                 if self.week_pair_ci_high == self.week_pair_ci_high else None,
            "n_participants_icc": self.n_participants_icc,
            "n_participants_week_pair": self.n_participants_week_pair,
        }


def icc_2_1(matrix: np.ndarray, nan_policy: str = "drop") -> float:
    """Intraclass correlation, ICC(2,1) form: two-way random, single rater,
    absolute agreement.

    Parameters
    ----------
    matrix : np.ndarray
        Shape (n_subjects, n_raters).
    nan_policy : {'drop', 'raise'}
        - 'drop' (default): drop any subject row that contains a NaN.
        - 'raise': raise ValueError if any NaN is present.

    Returns
    -------
    float
        ICC value, or NaN if the cleaned input has fewer than 2 subjects or
        2 raters.
    """
    matrix = np.asarray(matrix, dtype=float)
    if matrix.size == 0 or matrix.ndim != 2:
        return float("nan")
    if np.isnan(matrix).any():
        if nan_policy == "raise":
            raise ValueError("ICC input contains NaN values; set nan_policy='drop' to filter")
        complete_mask = ~np.isnan(matrix).any(axis=1)
        matrix = matrix[complete_mask]
    if matrix.shape[0] < 2 or matrix.shape[1] < 2:
        return float("nan")
    n, k = matrix.shape
    mean_subjects = matrix.mean(axis=1)
    mean_raters = matrix.mean(axis=0)
    grand_mean = matrix.mean()

    ss_between_subjects = k * np.sum((mean_subjects - grand_mean) ** 2)
    ss_between_raters = n * np.sum((mean_raters - grand_mean) ** 2)
    ss_total = np.sum((matrix - grand_mean) ** 2)
    ss_error = ss_total - ss_between_subjects - ss_between_raters

    ms_between_subjects = ss_between_subjects / (n - 1)
    ms_between_raters = ss_between_raters / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))

    denom = ms_between_subjects + (k - 1) * ms_error + k * (ms_between_raters - ms_error) / n
    if denom <= 0:
        return float("nan")
    return float((ms_between_subjects - ms_error) / denom)


def compute_from_dataframe(df: pd.DataFrame, column: str, window_days: int = 7) -> float:
    """Take first `window_days` per participant, drop incomplete, compute ICC."""
    rows = []
    for pid, g in df.groupby("participant_id"):
        vals = g.sort_values("date")[column].to_numpy()[:window_days]
        if len(vals) == window_days and np.isfinite(vals).all():
            rows.append(vals)
    if len(rows) < 2:
        return float("nan")
    return icc_2_1(np.array(rows))


def compare_to_test_retest(df: pd.DataFrame, columns: list[str],
                           icc_window_days: int = 7,
                           n_bootstrap: int = 200) -> pd.DataFrame:
    """Empirical comparison: ICC(2,1) days-as-raters against bootstrap week-pair r.

    This is the formal defense of the unconventional ICC use. If the two
    methods rank metrics consistently and the ICC is monotonically related
    to the proper test-retest correlation, the ICC is doing useful work
    even though the rater interpretation is unusual.

    Returns one row per metric with both estimates and the week-pair CI.
    """
    from .test_retest import cohort_test_retest

    rows = []
    for col in columns:
        if col not in df.columns:
            continue
        icc_val = compute_from_dataframe(df, col, window_days=icc_window_days)
        # Count participants who contributed to the ICC
        n_icc = 0
        for _, g in df.groupby("participant_id"):
            vals = g.sort_values("date")[col].to_numpy()[:icc_window_days]
            if len(vals) == icc_window_days and np.isfinite(vals).all():
                n_icc += 1

        tr = cohort_test_retest(df, col, n_bootstrap=n_bootstrap)
        rows.append(MethodComparison(
            metric=col,
            icc_days_as_raters=icc_val,
            week_pair_r=tr.point_estimate,
            week_pair_ci_low=tr.ci_low,
            week_pair_ci_high=tr.ci_high,
            n_participants_icc=n_icc,
            n_participants_week_pair=tr.n_participants,
        ).to_dict())
    return pd.DataFrame(rows)
