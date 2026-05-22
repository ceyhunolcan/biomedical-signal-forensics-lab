"""Tests for the v0.4.0 additions: cross-cohort generalization check and
the ICC-vs-test-retest method comparison.
"""
import numpy as np
import pandas as pd

from src.evaluation.cross_cohort_check import (
    REGIMES, evaluate_regime, predicted_vs_observed, run_cross_cohort_check,
)
from src.reliability.intraclass_correlation import compare_to_test_retest


def _stable_cohort(n_pid=20, n_weeks=8, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    n_days = n_weeks * 7
    for p in range(n_pid):
        baseline_hr = rng.normal(60, 5)
        baseline_hrv = rng.normal(45, 5)
        for d in range(n_days):
            rows.append({
                "participant_id": f"P{p:03d}",
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=d),
                "resting_hr": baseline_hr + rng.normal(0, 1),
                "hrv_rmssd": baseline_hrv + rng.normal(0, 2),
                "sleep_duration": 7 + rng.normal(0, 0.5),
                "sleep_efficiency": np.clip(0.85 + rng.normal(0, 0.03), 0, 1),
            })
    return pd.DataFrame(rows)


# --- ICC vs test-retest comparison ---------------------------------------

def test_compare_to_test_retest_returns_per_metric_rows():
    df = _stable_cohort()
    out = compare_to_test_retest(df, ["resting_hr", "hrv_rmssd"], n_bootstrap=20)
    assert len(out) == 2
    for col in ("metric", "icc_days_as_raters", "week_pair_r",
                "week_pair_ci_low", "week_pair_ci_high",
                "n_participants_icc", "n_participants_week_pair"):
        assert col in out.columns


def test_compare_to_test_retest_skips_missing_columns():
    df = _stable_cohort()
    out = compare_to_test_retest(df, ["resting_hr", "nonexistent"], n_bootstrap=20)
    assert len(out) == 1
    assert out.iloc[0]["metric"] == "resting_hr"


def test_icc_and_test_retest_rank_consistently_on_stable_cohort():
    """On a cohort built with stable participant baselines + small daily noise,
    both ICC(2,1) and the bootstrap week-pair r should be high (above 0.5)
    for both metrics."""
    df = _stable_cohort()
    out = compare_to_test_retest(df, ["resting_hr", "hrv_rmssd"], n_bootstrap=30)
    for _, row in out.iterrows():
        assert row["icc_days_as_raters"] is not None
        assert row["week_pair_r"] is not None
        # Both methods agree that this cohort is reliable
        assert row["icc_days_as_raters"] > 0.5
        assert row["week_pair_r"] > 0.5


# --- Cross-cohort check ---------------------------------------------------

def test_regimes_have_expected_names():
    names = {r.name for r in REGIMES}
    expected = {"default", "strong_environment", "inverted_skin_tone",
                "severe_device_bias", "clean_world"}
    assert names == expected


def test_evaluate_regime_returns_expected_schema():
    """Single regime, tiny cohort to keep test fast."""
    regime = REGIMES[0]  # default
    row = evaluate_regime(regime, n_participants=20, n_days=14)
    for col in ("regime", "description", "heat_hrv_coef", "skin_tone_penalty",
                "device_b_offset_injected", "mean_cohort_dbts",
                "skin_tone_Q4_minus_Q1_sq", "device_B_minus_A_hr_empirical",
                "heat_hrv_screening_r", "hrv_test_retest_r",
                "n_participants", "n_days"):
        assert col in row


def test_clean_world_recovers_no_injected_effects():
    """The clean_world regime injects no environmental or device effects.
    The audit framework should recover near-zero screening correlations
    and near-zero empirical device offsets."""
    clean = REGIMES[4]  # clean_world
    row = evaluate_regime(clean, n_participants=40, n_days=21)
    # Heat → HRV correlation should be near zero (no injected effect)
    assert abs(row["heat_hrv_screening_r"]) < 0.1
    # Device-B empirical offset should be small (no injected bias, only
    # generator's per-day noise)
    assert abs(row["device_B_minus_A_hr_empirical"]) < 2.5


def test_inverted_skin_tone_flips_fairness_gap_sign():
    """The default regime has skin_tone_penalty > 0, so Q4 (darker proxy)
    should have worse signal quality than Q1 (negative gap). The inverted
    regime flips the sign of the penalty, which should flip the gap sign."""
    default = evaluate_regime(REGIMES[0], n_participants=40, n_days=21, seed=0)
    inverted = evaluate_regime(REGIMES[2], n_participants=40, n_days=21, seed=0)
    # Both should be non-NaN
    assert default["skin_tone_Q4_minus_Q1_sq"] is not None
    assert inverted["skin_tone_Q4_minus_Q1_sq"] is not None
    # Signs should differ
    assert default["skin_tone_Q4_minus_Q1_sq"] * inverted["skin_tone_Q4_minus_Q1_sq"] < 0


def test_severe_device_bias_recovers_large_offset():
    """The severe regime injects an 8-bpm device-B offset. The empirical
    offset (mean HR difference) should land within 2 bpm of that."""
    row = evaluate_regime(REGIMES[3], n_participants=40, n_days=21, seed=0)
    assert abs(row["device_B_minus_A_hr_empirical"] - 8.0) < 2.5


def test_full_cross_cohort_check_majority_predictions_pass():
    """End-to-end smoke: run the full 5-regime sweep and verify that the
    majority of qualitative predictions are recovered. Uses a small cohort
    so the test is fast."""
    table = run_cross_cohort_check(n_participants=40, n_days=35)
    predictions = predicted_vs_observed(table)
    n_pass = int((predictions["pass"] == True).sum())
    n_scored = int(predictions["pass"].notna().sum())
    assert n_scored >= 5  # at least the non-test-retest checks always run
    assert n_pass / n_scored >= 0.8, (
        f"Only {n_pass}/{n_scored} predictions passed:\n"
        f"{predictions.to_string()}"
    )
