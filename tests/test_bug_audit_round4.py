"""Regression tests for bug audit round 4 (deep file-by-file read).

Issues surfaced during the file-by-file deep audit of every Python source
file. Each test corresponds to a specific bug found and fixed.
"""
import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.artifacts.motion_artifacts import detect as motion_detect
from biomedical_signal_forensics_lab.artifacts.sensor_dropout import detect as dropout_detect
from biomedical_signal_forensics_lab.evaluation.metrics import expected_calibration_error
from biomedical_signal_forensics_lab.evaluation.calibration import reliability_curve
from biomedical_signal_forensics_lab.evaluation.robustness import perturbation_stability
from biomedical_signal_forensics_lab.models.anomaly_detector import train_baselines
from biomedical_signal_forensics_lab.reliability.device_bias import per_column_bias, bias_severity
from biomedical_signal_forensics_lab.reliability.temporal_stability import drift_slope
from biomedical_signal_forensics_lab.reports.figure_builder import (
    trust_radar, confounding_scatter, trust_distribution,
)
from biomedical_signal_forensics_lab.signals.signal_quality import per_window_sqi, daily_signal_quality
from biomedical_signal_forensics_lab.data.preprocessing import add_derived_columns, add_rolling_features


def _assert_raises(exc_type, fn, match_substring=None):
    try:
        fn()
    except exc_type as e:
        if match_substring is not None:
            assert match_substring in str(e), f"expected {match_substring!r} in {e!r}"
        return
    raise AssertionError(f"Did not raise {exc_type.__name__}")


# --- Bug A: motion-artifact severity and flag must be consistent ---------

def test_motion_severity_consistent_with_flag():
    """A signal that crosses one threshold should have flag=1 AND severity>0."""
    rng = np.random.default_rng(0)
    fs = 64
    # Build a high-amplitude-variance signal
    t = np.linspace(0, 5, 5 * fs)
    sig = 5 * np.sin(2 * np.pi * 1.5 * t) + 2 * rng.standard_normal(len(t))
    out = motion_detect(sig, fs=fs)
    # If flag fires, severity should be > 0. If severity > 0, flag should be 1.
    if out.flag == 1:
        assert out.severity > 0, f"flag=1 but severity={out.severity}"
    if out.severity > 0:
        assert out.flag == 1, f"severity={out.severity} but flag={out.flag}"


def test_motion_clean_signal_no_artifact():
    rng = np.random.default_rng(0)
    fs = 64
    t = np.linspace(0, 5, 5 * fs)
    clean = np.sin(2 * np.pi * 1.2 * t) + 0.02 * rng.standard_normal(len(t))
    out = motion_detect(clean, fs=fs)
    assert out.flag == 0
    assert out.severity == 0.0


def test_motion_handles_nan_input():
    fs = 64
    sig = np.full(5 * fs, np.nan)
    out = motion_detect(sig, fs=fs)
    assert out.flag == 0


# --- Bug C: dropout detector must catch NaN runs --------------------------

def test_dropout_detects_nan_runs():
    sig = np.ones(500)
    sig[100:200] = np.nan
    out = dropout_detect(sig)
    assert out.flag == 1
    assert out.severity > 0


# --- Bug D: ECE handles p=1.0 and empty input -----------------------------

def test_ece_includes_prob_equal_one():
    """A perfectly-calibrated prediction at p=1.0 must contribute to ECE."""
    y_true = np.array([1, 1, 1, 1])
    y_prob = np.array([1.0, 1.0, 1.0, 1.0])
    ece = expected_calibration_error(y_true, y_prob)
    assert ece == 0.0  # perfectly calibrated


def test_ece_empty_returns_nan():
    ece = expected_calibration_error(np.array([]), np.array([]))
    assert ece != ece  # NaN


# --- Bug E: perturbation_stability is reproducible ------------------------

class _FakeReport:
    def __init__(self, v): self.overall_trust_score = v


def test_perturbation_stability_is_deterministic():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    def scorer(d):
        return _FakeReport(50.0 + d["x"].sum())
    a = perturbation_stability(scorer, df, ["x"], seed=42, n_trials=5)
    b = perturbation_stability(scorer, df, ["x"], seed=42, n_trials=5)
    assert a == b


# --- Bug F: reliability_curve handles p=1.0 -------------------------------

def test_reliability_curve_handles_prob_one():
    y_true = np.array([1, 1, 0, 1])
    y_prob = np.array([1.0, 0.95, 0.1, 0.85])
    conf, acc = reliability_curve(y_true, y_prob, n_bins=10)
    # No crash; output arrays have same length
    assert len(conf) == len(acc)


# --- Bug G: train_baselines handles single-class targets -----------------

def test_train_baselines_handles_single_class():
    rng = np.random.default_rng(0)
    n = 100
    df = pd.DataFrame({
        "resting_hr": rng.normal(60, 3, n),
        "hrv_rmssd": rng.normal(45, 5, n),
        "hrv_sdnn": rng.normal(60, 5, n),
        "step_count": rng.normal(8000, 1000, n),
        "active_minutes": rng.normal(35, 10, n),
        "sleep_duration": rng.normal(7, 0.5, n),
        "sleep_efficiency": rng.normal(0.85, 0.03, n),
        "stress_proxy": rng.normal(0.4, 0.1, n),
        "heat_index": rng.normal(22, 2, n),
        "humidity": rng.normal(55, 5, n),
        "aqi": rng.normal(50, 10, n),
        "wearable_minutes": rng.normal(1200, 60, n),
        "signal_quality_ground_truth": np.full(n, 0.95),  # all above threshold
    })
    results = train_baselines(df)
    assert len(results) == 3
    for r in results:
        # All metrics NaN, all notes mention single-class
        assert r.auroc != r.auroc
        assert "single-class" in r.notes


def test_train_baselines_raises_on_missing_target():
    df = pd.DataFrame({"resting_hr": [60.0] * 50})
    _assert_raises(KeyError, lambda: train_baselines(df), "signal_quality_ground_truth")


# --- Bug H: drift_slope strips NaN ----------------------------------------

def test_drift_slope_strips_nan():
    v = np.array([60.0, 61.0, np.nan, np.nan, 62.0, 63.0, 64.0, 65.0])
    out = drift_slope(v)
    assert np.isfinite(out["slope"])
    assert out["slope"] > 0


# --- Bug J: per_column_bias rejects unknown reference ---------------------

def test_per_column_bias_rejects_bad_reference():
    df = pd.DataFrame({"device_type": ["A", "B", "A"],
                       "resting_hr": [60.0, 62.0, 61.0]})
    _assert_raises(KeyError,
                   lambda: per_column_bias(df, ["resting_hr"], reference="Z"),
                   "Z")


def test_per_column_bias_empty_devices_returns_empty_schema():
    df = pd.DataFrame({"device_type": [None, None],
                       "resting_hr": [60.0, 61.0]})
    out = per_column_bias(df, ["resting_hr"])
    assert list(out.columns) == ["device", "reference", "column", "mean_diff", "n_obs"]
    assert len(out) == 0


def test_bias_severity_empty_returns_zero():
    assert bias_severity(pd.DataFrame()) == 0.0


# --- Bug L/M: per_window_sqi and daily_signal_quality on minimal input ----

def test_per_window_sqi_empty_input_returns_schema():
    out = per_window_sqi(np.empty((0, 1250)), np.empty((0, 320)), 250, 64)
    assert set(["window_idx", "ecg_sqi", "ppg_sqi", "ppg_motion"]).issubset(out.columns)
    assert len(out) == 0


def test_daily_signal_quality_handles_missing_columns():
    df = pd.DataFrame({"some_other_col": [1, 2, 3]})
    out = daily_signal_quality(df)
    assert len(out) == 3
    assert all(v != v for v in out)  # all NaN

    # With only wearable_minutes
    df2 = pd.DataFrame({"wearable_minutes": [1200, 1200, 1200]})
    out2 = daily_signal_quality(df2)
    assert all(np.isfinite(v) for v in out2)


# --- Bug P: preprocessing handles missing source columns ------------------

def test_add_derived_columns_skips_missing():
    df = pd.DataFrame({"wearable_minutes": [1200] * 5})
    out = add_derived_columns(df)
    assert "wearable_coverage_frac" in out.columns
    assert "heat_load" not in out.columns  # source missing → skip


def test_add_rolling_features_skips_missing():
    df = pd.DataFrame({
        "participant_id": ["p"] * 14,
        "date": pd.date_range("2024-01-01", periods=14),
        "resting_hr": np.arange(14, dtype=float),
    })
    out = add_rolling_features(df)
    assert "resting_hr_roll7_mean" in out.columns
    assert "hrv_rmssd_roll7_mean" not in out.columns


# --- Bug Q, S: figure_builder doesn't crash on empty/missing input -------

def test_trust_radar_handles_empty_components(tmp_path):
    out = trust_radar({}, out=str(tmp_path / "radar.png"))
    assert out.exists()


def test_confounding_scatter_handles_missing_columns(tmp_path):
    df = pd.DataFrame({"only_col": [1, 2, 3]})
    out = confounding_scatter(df, out=str(tmp_path / "scatter.png"))
    assert out.exists()


def test_confounding_scatter_handles_all_nan(tmp_path):
    df = pd.DataFrame({"heat_index": [np.nan] * 5, "hrv_rmssd": [np.nan] * 5})
    out = confounding_scatter(df, out=str(tmp_path / "scatter.png"))
    assert out.exists()


def test_trust_distribution_handles_empty(tmp_path):
    out = trust_distribution(np.array([]), out=str(tmp_path / "dist.png"))
    assert out.exists()


# --- Bug V: AIPW point estimate doesn't crash on empty treatment arms ---

def test_aipw_handles_imbalanced_resamples():
    """A bootstrap-style stress test: highly imbalanced treatment should not
    crash the point estimate."""
    from biomedical_signal_forensics_lab.confounding.causal_inference import aipw
    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame({
        "T": (rng.random(n) > 0.95).astype(int),  # ~5% treated
        "C": rng.normal(0, 1, n),
        "Y": rng.normal(0, 1, n),
    })
    res = aipw(df, "T", "Y", ["C"], n_bootstrap=10)
    # Either a finite estimate or a clear NaN with a meaningful note
    assert res.point_estimate == res.point_estimate or "failed" in res.notes
