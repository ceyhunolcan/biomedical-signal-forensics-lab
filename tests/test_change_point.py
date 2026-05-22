"""Change-point detection tests."""
import numpy as np
import pandas as pd

from src.reliability.change_point import (
    bocpd, binary_segmentation, scan_cohort, stratify_before_after,
)


def _step_series(n_before=40, n_after=40, mu1=60.0, mu2=68.0, sigma=2.0, seed=0):
    rng = np.random.default_rng(seed)
    return np.concatenate([rng.normal(mu1, sigma, n_before),
                           rng.normal(mu2, sigma, n_after)])


def test_binseg_finds_textbook_step_change():
    sig = _step_series()
    cps = binary_segmentation(sig)
    # filter to "real" change-points (|delta| > 3)
    real = [cp for cp in cps if abs(cp.delta) > 3.0]
    assert len(real) >= 1
    # Detection should be within +/- 3 samples of true index (40)
    assert any(abs(cp.index - 40) <= 3 for cp in real)


def test_binseg_quiet_on_stationary_series():
    rng = np.random.default_rng(7)
    sig = rng.normal(60, 2, 100)
    cps = binary_segmentation(sig)
    real = [cp for cp in cps if abs(cp.delta) > 3.0]
    assert len(real) == 0


def test_bocpd_finds_large_step_change():
    sig = _step_series(mu1=60.0, mu2=72.0)
    cps = bocpd(sig, hazard=1.0 / 30.0)
    real = [cp for cp in cps if abs(cp.delta) > 5.0]
    assert len(real) >= 1


def test_bocpd_runs_on_short_series_without_error():
    sig = np.array([1.0, 2.0, 3.0])
    out = bocpd(sig)
    assert out == []


def test_stratify_before_after():
    sig = _step_series()
    s = stratify_before_after(sig, 40)
    assert s["before_n"] == 40
    assert s["after_n"] == 40
    assert s["delta_mean"] > 5.0  # ~+8 expected


def test_scan_cohort_returns_long_frame():
    n = 60
    rng = np.random.default_rng(0)
    pid_a_series = np.concatenate([rng.normal(60, 2, 30), rng.normal(70, 2, 30)])
    pid_b_series = rng.normal(60, 2, n)  # stable
    df = pd.concat([
        pd.DataFrame({"participant_id": "A", "date": pd.date_range("2024-01-01", periods=n),
                      "resting_hr": pid_a_series}),
        pd.DataFrame({"participant_id": "B", "date": pd.date_range("2024-01-01", periods=n),
                      "resting_hr": pid_b_series}),
    ])
    out = scan_cohort(df, metric="resting_hr", method="binary_segmentation")
    # filter to substantial changes
    out = out[out["delta"].abs() > 3.0]
    assert "A" in set(out["participant_id"])
    assert "B" not in set(out["participant_id"])
