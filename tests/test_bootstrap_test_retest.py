"""Bootstrap test-retest tests."""
import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.reliability.test_retest import (
    cohort_test_retest, cohort_test_retest_table,
    week_pair_correlation, split_half_correlation,
)


def _stable_cohort(n_pid=20, n_weeks=8, seed=0):
    """Each participant has a stable baseline, weekly noise around it."""
    rng = np.random.default_rng(seed)
    rows = []
    n_days = n_weeks * 7
    for p in range(n_pid):
        baseline = rng.normal(60, 5)
        for d in range(n_days):
            rows.append({
                "participant_id": f"P{p:03d}",
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=d),
                "metric": baseline + rng.normal(0, 2),
            })
    return pd.DataFrame(rows)


def _noise_cohort(n_pid=20, n_weeks=8, seed=0):
    """No between-participant signal: pure noise."""
    rng = np.random.default_rng(seed)
    rows = []
    n_days = n_weeks * 7
    for p in range(n_pid):
        for d in range(n_days):
            rows.append({
                "participant_id": f"P{p:03d}",
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=d),
                "metric": rng.normal(0, 1),
            })
    return pd.DataFrame(rows)


def test_split_half_handles_nan_inputs():
    v = np.array([1.0, 2.0, np.nan, 3.0, 4.0, 5.0, 6.0])
    r = split_half_correlation(v)
    assert -1.0 <= r <= 1.0 or r != r


def test_week_pair_correlation_high_on_stable_cohort():
    df = _stable_cohort()
    r = week_pair_correlation(df, "metric", min_weeks=4)
    assert r > 0.7


def test_week_pair_correlation_low_on_pure_noise():
    df = _noise_cohort()
    r = week_pair_correlation(df, "metric", min_weeks=4)
    # Pure noise: r should hover around zero. Allow a generous bound.
    assert abs(r) < 0.4


def test_cohort_test_retest_returns_ci():
    df = _stable_cohort()
    res = cohort_test_retest(df, "metric", n_bootstrap=50)
    assert res.ci_low <= res.point_estimate <= res.ci_high
    assert res.n_participants == 20
    assert res.method == "week_pair"


def test_cohort_test_retest_table_handles_multiple_metrics():
    df = _stable_cohort()
    df["other"] = np.random.default_rng(0).normal(0, 1, len(df))
    out = cohort_test_retest_table(df, ["metric", "other"], n_bootstrap=30)
    assert len(out) == 2
    assert "point_estimate" in out.columns
    assert "ci_low" in out.columns


def test_cohort_test_retest_handles_missing_metric():
    df = _stable_cohort()
    # Asking for a column that doesn't exist returns an empty frame
    out = cohort_test_retest_table(df, ["nonexistent"], n_bootstrap=10)
    assert len(out) == 0


def test_cohort_test_retest_raises_without_participant_id():
    df = _stable_cohort().drop(columns=["participant_id"])
    try:
        cohort_test_retest(df, "metric")
    except KeyError:
        return
    raise AssertionError("Did not raise KeyError")


def test_split_half_method_works():
    df = _stable_cohort()
    res = cohort_test_retest(df, "metric", method="split_half", n_bootstrap=30)
    assert res.method == "split_half"
    assert res.point_estimate == res.point_estimate or res.n_participants == 0
