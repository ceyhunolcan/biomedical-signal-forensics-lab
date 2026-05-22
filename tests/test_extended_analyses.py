"""Tests for the reviewer-grade extended analyses.

These tests use synthetic fixtures rather than touching real WESAD data,
so the suite runs in the sandbox without the dataset present.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the analysis functions from the script module
from scripts.run_extended_analyses import (
    aipw_positivity_check,
    cohens_d,
    e_value,
    multi_threshold_recalibration,
    per_state_effect_sizes,
)


def test_evalue_positive_estimate():
    """E-value for a moderate positive effect."""
    result = e_value(estimate=0.5, ci_low=0.2, ci_high=0.8)
    assert result["estimate"] == 0.5
    assert result["evalue_point"] > 1.0
    # CI excludes null, so CI bound E-value is defined
    assert result["evalue_ci_bound"] is not None
    # CI lower bound is closer to null, so its E-value should be smaller
    assert result["evalue_ci_bound"] < result["evalue_point"]


def test_evalue_negative_estimate():
    """E-value handles negative estimates by taking absolute value via RR conversion."""
    result = e_value(estimate=-0.5, ci_low=-0.8, ci_high=-0.2)
    assert result["evalue_point"] > 1.0
    assert result["evalue_ci_bound"] is not None


def test_evalue_ci_crosses_null():
    """When CI crosses null, the CI-bound E-value is None."""
    result = e_value(estimate=0.5, ci_low=-0.2, ci_high=1.2)
    assert result["evalue_point"] > 1.0
    assert result["evalue_ci_bound"] is None


def test_evalue_zero_effect():
    """E-value for null effect is 1.0."""
    result = e_value(estimate=0.0, ci_low=-0.5, ci_high=0.5)
    assert abs(result["evalue_point"] - 1.0) < 1e-6


def test_cohens_d_known_separation():
    """Cohen's d on two distributions with known separation."""
    rng = np.random.default_rng(42)
    a = rng.normal(0, 1, 200)
    b = rng.normal(1, 1, 200)
    d = cohens_d(a, b)
    # True d should be near -1.0
    assert -1.3 < d < -0.7


def test_cohens_d_identical():
    """Cohen's d of a sample with itself is 0."""
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 100)
    d = cohens_d(x, x)
    assert abs(d) < 1e-10


def test_cohens_d_empty():
    """Cohen's d returns NaN for empty inputs."""
    assert np.isnan(cohens_d(np.array([]), np.array([1.0, 2.0])))
    assert np.isnan(cohens_d(np.array([1.0]), np.array([1.0])))


def test_cohens_d_zero_variance():
    """Cohen's d returns NaN when both samples are constant."""
    a = np.ones(10)
    b = np.ones(10)
    assert np.isnan(cohens_d(a, b))


def test_multi_threshold_recalibration_shape():
    """The recalibration function returns expected fields."""
    rng = np.random.default_rng(42)
    n = 200
    # In-house score correlated with the label
    label = rng.integers(0, 2, n)
    score = label + rng.normal(0, 0.5, n)
    result = multi_threshold_recalibration(score, label, n_bootstrap=20, seed=42)
    assert "auroc_point" in result
    assert "auroc_ci" in result
    assert "youden_threshold_point" in result
    assert "youden_threshold_ci" in result
    assert "f1_threshold_point" in result
    assert "roc" in result
    assert "pr" in result
    assert len(result["roc"]["fpr"]) == len(result["roc"]["tpr"])
    # AUROC should be well above chance for this construction
    assert result["auroc_point"] > 0.7
    # CI should bracket the point estimate
    if result["auroc_ci"][0] is not None:
        assert result["auroc_ci"][0] <= result["auroc_point"] <= result["auroc_ci"][1]


def test_multi_threshold_recalibration_uninformative():
    """For an uninformative score, AUROC should be near 0.5."""
    rng = np.random.default_rng(42)
    n = 500
    label = rng.integers(0, 2, n)
    score = rng.normal(0, 1, n)  # No relationship
    result = multi_threshold_recalibration(score, label, n_bootstrap=20, seed=42)
    assert 0.3 < result["auroc_point"] < 0.7


def test_aipw_positivity_check_clean_overlap(tmp_path):
    """Positivity check on synthetic data with clean treatment overlap."""
    rng = np.random.default_rng(42)
    n = 500
    df = pd.DataFrame({
        "x1": rng.normal(0, 1, n),
        "x2": rng.normal(0, 1, n),
        "t": rng.normal(0, 1, n),
        "y": rng.normal(0, 1, n),
    })
    csv = tmp_path / "synth.csv"
    df.to_csv(csv, index=False)
    pairs = [("t", "y", ["x1", "x2"])]
    result = aipw_positivity_check(csv, pairs)
    assert len(result) == 1
    row = result.iloc[0]
    assert 0.4 < row["ps_mean"] < 0.6
    assert row["frac_outside_clip"] < 0.3
    assert row["kish_ess"] > 0.5 * n


def test_aipw_positivity_check_severe_violation(tmp_path):
    """Positivity check flags severe violations when the treatment is
    perfectly predicted by the covariates."""
    rng = np.random.default_rng(42)
    n = 500
    x1 = rng.normal(0, 1, n)
    # Treatment is essentially x1 > 0, so positivity fails
    t = x1.copy()
    df = pd.DataFrame({"x1": x1, "x2": rng.normal(0, 1, n), "t": t,
                       "y": rng.normal(0, 1, n)})
    csv = tmp_path / "synth.csv"
    df.to_csv(csv, index=False)
    pairs = [("t", "y", ["x1", "x2"])]
    result = aipw_positivity_check(csv, pairs)
    row = result.iloc[0]
    # Severe violation: at least 20% of propensities outside [0.05, 0.95]
    assert row["frac_outside_clip"] > 0.2


def test_per_state_effect_sizes_returns_dataframe(tmp_path):
    """The effect-size routine produces the expected schema."""
    rng = np.random.default_rng(42)
    # Build a tiny synthetic SQI dataframe matching the real schema
    rows = []
    for sid in ["S99", "S100"]:
        for label in ["baseline", "stress", "amusement"]:
            n_in_state = 30
            for i in range(n_in_state):
                rows.append({
                    "subject_id": sid,
                    "label_name": label,
                    "ppg_sqi": float(rng.normal(0.95 if label == "baseline" else 0.90, 0.05)),
                    "ecg_sqi": float(rng.normal(0.98, 0.02)),
                    "ppg_motion": float(rng.uniform(0.01, 0.05 if label == "baseline" else 0.10)),
                })
    df = pd.DataFrame(rows)
    csv = tmp_path / "sqi.csv"
    df.to_csv(csv, index=False)
    eff = per_state_effect_sizes(csv)
    expected_cols = {"subject_id", "metric", "contrast", "n_a", "n_b",
                     "mean_a", "mean_b", "median_a", "median_b",
                     "p_value", "cliffs_delta", "cliffs_delta_ci_low",
                     "cliffs_delta_ci_high", "cohens_d"}
    assert expected_cols.issubset(set(eff.columns))
    assert len(eff) > 0
    # Cliff's delta is bounded
    assert eff["cliffs_delta"].between(-1, 1).all()
    # Cliff's CI low ≤ Cliff's delta ≤ Cliff's CI high
    for _, row in eff.iterrows():
        if row["cliffs_delta_ci_low"] == row["cliffs_delta_ci_low"]:  # not NaN
            # Allow slight tolerance because bootstrap percentiles can occasionally
            # land tightly around the point estimate
            assert row["cliffs_delta_ci_low"] - 0.01 <= row["cliffs_delta"] <= row["cliffs_delta_ci_high"] + 0.01


def test_per_state_effect_sizes_small_n_skipped(tmp_path):
    """Contrasts with too-few samples are dropped from the output."""
    df = pd.DataFrame([
        {"subject_id": "S99", "label_name": "baseline",
         "ppg_sqi": 0.95, "ecg_sqi": 0.98, "ppg_motion": 0.02},
        {"subject_id": "S99", "label_name": "stress",
         "ppg_sqi": 0.90, "ecg_sqi": 0.97, "ppg_motion": 0.03},
    ])
    csv = tmp_path / "tiny.csv"
    df.to_csv(csv, index=False)
    eff = per_state_effect_sizes(csv)
    # n=1 per state is below the threshold, so no rows should appear
    assert len(eff) == 0
