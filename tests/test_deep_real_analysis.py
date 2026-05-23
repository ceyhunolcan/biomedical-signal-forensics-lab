"""Tests for the deep real-data analysis module.

These tests use synthetic per-window tables (not actual WESAD data) so they
run end-to-end in the sandbox. The WESAD adapter has its own tests in
test_wesad_adapter.py.
"""
import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.evaluation.deep_real_analysis import (
    cohens_kappa,
    cross_modality_hr_agreement,
    motion_effect_analysis,
    per_state_comparison,
    recalibrate_inhouse_sqi,
    three_way_sqi_agreement,
    hr_from_ecg_window,
    hr_from_ppg_window,
)


def _synth_window_table(n=200, seed=0):
    """Build a synthetic per-window table that mimics the deep analysis output."""
    rng = np.random.default_rng(seed)
    states = rng.choice(["baseline", "stress", "amusement"], size=n, p=[0.5, 0.3, 0.2])
    state_label = {"baseline": 1, "stress": 2, "amusement": 3}
    subjects = rng.choice(["S2", "S3"], size=n)
    # baseline HR ~70, +10 in stress
    hr_ecg = 70.0 + 10.0 * (states == "stress") + rng.normal(0, 5, n)
    hr_ppg = hr_ecg + rng.normal(0, 3, n) + 1.0  # small bias
    motion = 0.02 + 0.01 * (states == "stress") + rng.exponential(0.01, n)
    sqi_inhouse = np.clip(1.0 - 5 * motion + rng.normal(0, 0.02, n), 0, 1)
    return pd.DataFrame({
        "window_idx": np.arange(n),
        "subject_id": subjects,
        "label_name": states,
        "label": [state_label[s] for s in states],
        "hr_ecg": hr_ecg,
        "hr_ppg": hr_ppg,
        "hr_abs_diff": np.abs(hr_ecg - hr_ppg),
        "inhouse_ecg_sqi": np.clip(0.95 + rng.normal(0, 0.02, n), 0, 1),
        "inhouse_ppg_sqi": sqi_inhouse,
        "inhouse_ppg_motion": motion,
        "orphanidou_acceptable": (sqi_inhouse > 0.7).astype(int),
        "orphanidou_template_corr": np.clip(sqi_inhouse + rng.normal(0, 0.1, n), 0, 1),
        "sukor_acceptable": (sqi_inhouse > 0.75).astype(int),
        "sukor_pp_cv": rng.uniform(0.05, 0.4, n),
        "sukor_amp_cv": rng.uniform(0.1, 0.6, n),
    })


# --- HR window estimators -------------------------------------------------

def test_hr_from_ecg_window_recovers_synthetic_hr():
    """Synthesize 5 s of ECG-like signal at 72 bpm; recover within 5 bpm."""
    fs = 700
    t = np.arange(5 * fs) / fs
    # Period 60/72 = 0.833 s
    period = 60.0 / 72.0
    sig = np.zeros_like(t)
    for k in range(int(5 / period) + 2):
        sig += np.exp(-((t - k * period) ** 2) / (2 * 0.012 ** 2))
    rng = np.random.default_rng(0)
    sig += 0.05 * rng.standard_normal(len(sig))
    hr = hr_from_ecg_window(sig, fs=fs)
    assert 65 <= hr <= 80, f"recovered HR {hr} outside expected range"


def test_hr_from_ppg_window_recovers_synthetic_hr():
    fs = 64
    t = np.arange(5 * fs) / fs
    hr_target = 80.0
    sig = np.sin(2 * np.pi * (hr_target / 60.0) * t)
    sig += 0.05 * np.random.default_rng(0).standard_normal(len(sig))
    hr = hr_from_ppg_window(sig, fs=fs)
    assert 70 <= hr <= 90, f"recovered PPG HR {hr} outside expected range"


def test_hr_estimators_return_nan_on_short_input():
    assert hr_from_ecg_window(np.zeros(10), fs=700) != hr_from_ecg_window(np.zeros(10), fs=700)
    assert hr_from_ppg_window(np.zeros(10), fs=64) != hr_from_ppg_window(np.zeros(10), fs=64)


# --- Cross-modality agreement --------------------------------------------

def test_cross_modality_hr_agreement_recovers_bias():
    """Build a table where HR_PPG = HR_ECG + 10 exactly. Bias should be +10."""
    n = 50
    hr_ecg = 70 + np.random.default_rng(0).normal(0, 5, n)
    df = pd.DataFrame({"hr_ecg": hr_ecg, "hr_ppg": hr_ecg + 10.0,
                       "label_name": ["baseline"] * n,
                       "subject_id": ["S2"] * n,
                       "hr_abs_diff": np.full(n, 10.0),
                       "inhouse_ppg_motion": np.zeros(n),
                       "inhouse_ppg_sqi": np.full(n, 0.95),
                       "orphanidou_template_corr": np.full(n, 0.85)})
    r = cross_modality_hr_agreement(df)
    assert abs(r.bias_ppg_minus_ecg_bpm - 10.0) < 0.5
    assert r.mean_absolute_error_bpm > 9 and r.mean_absolute_error_bpm < 11
    # Perfect correlation (HR_PPG is a shifted copy of HR_ECG)
    assert r.pearson_r > 0.99


def test_cross_modality_hr_agreement_empty():
    r = cross_modality_hr_agreement(pd.DataFrame())
    assert r.n_windows == 0
    assert r.mean_absolute_error_bpm != r.mean_absolute_error_bpm  # NaN


def test_cross_modality_hr_agreement_handles_nan():
    df = pd.DataFrame({"hr_ecg": [70, np.nan, 72, 74],
                       "hr_ppg": [72, 76, np.nan, 76]})
    r = cross_modality_hr_agreement(df)
    # Only rows 0 and 3 have both non-NaN
    assert r.n_windows == 2


# --- Per-state paired comparisons ----------------------------------------

def test_per_state_comparison_returns_one_row_per_subject_per_metric():
    df = _synth_window_table(n=200, seed=1)
    out = per_state_comparison(df, "baseline", "stress")
    # Two subjects × ~5 metrics each (some may drop if NaN-heavy)
    assert len(out) >= 5
    assert "subject_id" in out.columns
    assert "wilcoxon_p" in out.columns


def test_per_state_comparison_detects_injected_effect():
    """In _synth_window_table, stress windows have +10 bpm HR. The hr_abs_diff
    metric (which is np.abs(hr_ecg - hr_ppg) where hr_ppg = hr_ecg + small noise)
    shouldn't shift much, but the inhouse_ppg_motion metric does shift."""
    df = _synth_window_table(n=400, seed=2)
    out = per_state_comparison(df, "baseline", "stress")
    motion_rows = out[out["metric"] == "inhouse_ppg_motion"]
    assert len(motion_rows) >= 1
    # All subjects should show stress > baseline motion (positive delta)
    deltas = motion_rows["delta_b_minus_a"].dropna()
    assert (deltas > 0).all()


# --- Three-way SQI agreement ---------------------------------------------

def test_three_way_sqi_agreement_with_perfect_agreement():
    """Build a table where all three methods give identical pass/fail."""
    n = 100
    pass_or_fail = (np.arange(n) >= n // 2).astype(int)
    df = pd.DataFrame({
        "inhouse_ppg_sqi": np.where(pass_or_fail, 0.95, 0.5),
        "orphanidou_acceptable": pass_or_fail,
        "sukor_acceptable": pass_or_fail,
        "orphanidou_template_corr": np.where(pass_or_fail, 0.85, 0.4),
        "sukor_amp_cv": np.where(pass_or_fail, 0.2, 0.7),
    })
    r = three_way_sqi_agreement(df, inhouse_threshold=0.7)
    # All three should pass identically: kappa = 1
    assert r.kappa_inhouse_vs_orph > 0.95
    assert r.kappa_orph_vs_sukor > 0.95
    assert r.fraction_all_three_pass == 0.5


def test_three_way_sqi_agreement_handles_zero_variance_inhouse():
    """If in-house is constant (all pass), kappa with anything else is 0."""
    df = pd.DataFrame({
        "inhouse_ppg_sqi": np.full(50, 0.95),
        "orphanidou_acceptable": np.random.default_rng(0).integers(0, 2, 50),
        "sukor_acceptable": np.random.default_rng(1).integers(0, 2, 50),
        "orphanidou_template_corr": np.random.default_rng(2).uniform(0, 1, 50),
        "sukor_amp_cv": np.random.default_rng(3).uniform(0.1, 0.6, 50),
    })
    r = three_way_sqi_agreement(df, inhouse_threshold=0.7)
    # In-house is all-pass; kappa against varying truth is 0 (no above-chance agreement)
    assert abs(r.kappa_inhouse_vs_orph) < 0.01


def test_three_way_sqi_agreement_empty():
    r = three_way_sqi_agreement(pd.DataFrame())
    assert r.n_windows == 0


# --- Cohen's kappa --------------------------------------------------------

def test_cohens_kappa_perfect_agreement():
    a = np.array([0, 1, 0, 1, 1])
    assert abs(cohens_kappa(a, a) - 1.0) < 1e-9


def test_cohens_kappa_chance_agreement():
    """Perfectly random labels should give kappa near zero."""
    rng = np.random.default_rng(0)
    a = rng.integers(0, 2, 1000)
    b = rng.integers(0, 2, 1000)
    k = cohens_kappa(a, b)
    assert abs(k) < 0.1


def test_cohens_kappa_handles_zero_variance():
    """If one rater is constant, kappa is mathematically 0 or NaN depending on
    convention. Our implementation returns 0 when p_observed equals p_chance
    (no agreement above chance) and NaN when p_chance saturates at 1.0."""
    # Constant rater + varying rater. p_a = 1, p_chance = p_b, p_observed = p_b → 0
    a = np.array([1, 1, 1, 1, 1])
    b = np.array([0, 1, 0, 1, 1])
    k = cohens_kappa(a, b)
    assert k == 0.0

    # Both raters constant and agreeing: p_chance saturates → NaN
    a = np.array([1, 1, 1, 1, 1])
    b = np.array([1, 1, 1, 1, 1])
    k = cohens_kappa(a, b)
    assert k != k  # NaN


# --- Motion effect --------------------------------------------------------

def test_motion_effect_correlates_negatively_with_sqi():
    """If we inject motion ~ -SQI, the correlation should be very negative."""
    n = 100
    rng = np.random.default_rng(0)
    motion = rng.uniform(0, 0.2, n)
    sqi = 1.0 - 5 * motion + rng.normal(0, 0.01, n)
    df = pd.DataFrame({"inhouse_ppg_motion": motion,
                       "inhouse_ppg_sqi": sqi,
                       "hr_abs_diff": rng.uniform(0, 20, n),
                       "orphanidou_template_corr": sqi + rng.normal(0, 0.05, n)})
    r = motion_effect_analysis(df)
    assert r.spearman_motion_vs_inhouse_sqi < -0.9


def test_motion_effect_empty():
    r = motion_effect_analysis(pd.DataFrame())
    assert r.n_windows == 0


# --- Recalibration --------------------------------------------------------

def test_recalibrate_improves_holdout_kappa():
    """Build a dataset where the in-house SQI matches Orphanidou at threshold 0.5
    but the original 0.7 threshold misclassifies many. Recalibration should help."""
    rng = np.random.default_rng(0)
    n = 200
    true_pass = rng.integers(0, 2, n)
    # In-house SQI is true_pass + noise centered at 0.5
    inhouse_sqi = np.where(true_pass, 0.55, 0.45) + rng.normal(0, 0.04, n)
    inhouse_sqi = np.clip(inhouse_sqi, 0, 1)
    df = pd.DataFrame({"inhouse_ppg_sqi": inhouse_sqi,
                       "orphanidou_acceptable": true_pass})
    r = recalibrate_inhouse_sqi(df, original_threshold=0.7, seed=42)
    # At threshold 0.7, nothing passes → low agreement
    # At threshold ~0.5, agreement should be much higher
    assert r.recalibrated_holdout_kappa_vs_orph > r.original_holdout_kappa_vs_orph
    # The new threshold should be near 0.5
    assert 0.3 < r.recalibrated_threshold < 0.6


def test_recalibrate_handles_small_data():
    """On <20 rows, return NaN gracefully."""
    df = pd.DataFrame({"inhouse_ppg_sqi": [0.5, 0.6, 0.7],
                       "orphanidou_acceptable": [0, 1, 1]})
    r = recalibrate_inhouse_sqi(df)
    assert r.n_calibration == 0
    assert r.recalibrated_holdout_kappa_vs_orph != r.recalibrated_holdout_kappa_vs_orph
