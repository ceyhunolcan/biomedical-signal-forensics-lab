"""Reliability primitives: ICC, test-retest, drift, device bias."""
import numpy as np
import pandas as pd

from src.reliability.intraclass_correlation import icc_2_1
from src.reliability.test_retest import split_half_correlation
from src.reliability.temporal_stability import drift_slope, rolling_cov
from src.reliability.device_bias import per_column_bias


def test_icc_high_when_raters_agree():
    rng = np.random.default_rng(0)
    truth = rng.normal(50, 10, 30)
    rater_a = truth + rng.normal(0, 0.5, 30)
    rater_b = truth + rng.normal(0, 0.5, 30)
    rater_c = truth + rng.normal(0, 0.5, 30)
    icc = icc_2_1(np.column_stack([rater_a, rater_b, rater_c]))
    assert icc > 0.8


def test_icc_low_when_raters_disagree():
    rng = np.random.default_rng(1)
    arr = rng.normal(0, 1, (30, 3))
    icc = icc_2_1(arr)
    assert icc < 0.5


def test_split_half_correlation_returns_finite():
    x = np.linspace(0, 1, 100) + 0.01 * np.random.default_rng(0).standard_normal(100)
    r = split_half_correlation(x)
    assert np.isfinite(r)
    assert -1.0 <= r <= 1.0


def test_drift_slope_detects_trend():
    n = 60
    drifting = np.linspace(50, 70, n)
    flat = np.full(n, 60.0) + 1e-3 * np.random.default_rng(0).standard_normal(n)
    d = drift_slope(drifting)
    f = drift_slope(flat)
    assert abs(d["slope"]) > abs(f["slope"])


def test_rolling_cov_returns_array():
    s = np.random.default_rng(0).normal(50, 5, 60)
    out = rolling_cov(s, window=7)
    assert len(out) == len(s)


def test_device_bias_against_reference():
    df = pd.DataFrame({
        "device_type": ["A"] * 20 + ["B"] * 20,
        "resting_hr": np.concatenate([np.full(20, 60.0), np.full(20, 64.0)]),
    })
    bias = per_column_bias(df, columns=["resting_hr"], reference="A")
    # bias is long-format with 'device', 'column', 'mean_diff'
    row = bias[(bias["device"] == "B") & (bias["column"] == "resting_hr")].iloc[0]
    assert row["mean_diff"] > 0
