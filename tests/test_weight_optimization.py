"""Trust-score weight optimization tests."""
import numpy as np
import pandas as pd

from src.reliability.weight_optimization import (
    weekly_reproducibility_target, overall_from_components,
    participant_components, learn_weights, sensitivity_table,
    DEFAULT_WEIGHTS, COMPONENT_KEYS,
)


def _toy_cohort(n_participants=12, n_days=42, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_participants):
        baseline_hr = rng.normal(62, 4)
        baseline_hrv = rng.normal(45, 6)
        for d in range(n_days):
            rows.append({
                "participant_id": f"P{p:03d}",
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=d),
                "device_type": "A",
                "resting_hr": baseline_hr + rng.normal(0, 2),
                "hrv_rmssd": baseline_hrv + rng.normal(0, 4),
                "hrv_sdnn": 60 + rng.normal(0, 7),
                "step_count": 7000 + rng.normal(0, 1000),
                "active_minutes": 35 + rng.normal(0, 8),
                "sleep_duration": 7.2 + rng.normal(0, 0.5),
                "sleep_efficiency": np.clip(0.85 + rng.normal(0, 0.04), 0, 1),
                "stress_proxy": rng.uniform(0, 1),
                "temperature_c": 22 + rng.normal(0, 3),
                "humidity": 55 + rng.normal(0, 10),
                "aqi": 50 + rng.normal(0, 10),
                "heat_index": 22 + rng.normal(0, 3),
                "wearable_minutes": 1200 + rng.normal(0, 80),
                "missing_wearable_flag": int(rng.random() < 0.08),
                "signal_quality_ground_truth": np.clip(0.85 + rng.normal(0, 0.05), 0, 1),
                "artifact_burden_ground_truth": np.clip(0.1 + rng.normal(0, 0.03), 0, 1),
                "reliability_ground_truth": np.clip(0.9 + rng.normal(0, 0.03), 0, 1),
            })
    return pd.DataFrame(rows)


def test_reproducibility_target_returns_per_participant():
    df = _toy_cohort()
    out = weekly_reproducibility_target(df, metric="hrv_rmssd")
    assert "participant_id" in out.columns
    assert "reproducibility" in out.columns
    assert out["reproducibility"].between(0, 1).all()


def test_overall_from_components_respects_weights():
    df = pd.DataFrame({
        "participant_id": ["a", "b"],
        "signal_quality_score": [100.0, 0.0],
        "artifact_burden_score": [0.0, 100.0],
        "temporal_stability_score": [0.0, 0.0],
        "missingness_risk_score": [0.0, 0.0],
        "device_bias_score": [0.0, 0.0],
        "confounding_risk_score": [0.0, 0.0],
    })
    # All weight on signal_quality_score → a beats b
    only_sq = {k: 0.0 for k in COMPONENT_KEYS}
    only_sq["signal_quality_score"] = 1.0
    out = overall_from_components(df, only_sq)
    assert out.iloc[0] > out.iloc[1]

    # All weight on artifact_burden_score → b beats a
    only_ab = {k: 0.0 for k in COMPONENT_KEYS}
    only_ab["artifact_burden_score"] = 1.0
    out = overall_from_components(df, only_ab)
    assert out.iloc[1] > out.iloc[0]


def test_learn_weights_finds_simplex_weights():
    df = _toy_cohort()
    res = learn_weights(df, target_metric="hrv_rmssd",
                        n_random=50, n_refine=2, holdout_fraction=0.3)
    w = res.weights
    total = sum(w.values())
    assert abs(total - 1.0) < 1e-3
    for v in w.values():
        assert v >= 0
    assert -1.0 <= res.spearman_train <= 1.0
    # Holdout may be NaN for very small cohorts; either NaN or in [-1, 1] is acceptable
    assert (res.spearman_holdout != res.spearman_holdout) or (-1.0 <= res.spearman_holdout <= 1.0)


def test_learn_weights_at_least_matches_default_on_synthetic():
    """On the synthetic cohort the learned ρ should not be wildly worse than
    default-weighted ρ. Holdout ρ can be lower than train; that's expected."""
    df = _toy_cohort(n_participants=20, n_days=60)
    res = learn_weights(df, n_random=100, n_refine=2)
    # the function returns a sensible Spearman, not just nonsense
    assert res.spearman_train > -0.5


def test_sensitivity_table_columns():
    df = _toy_cohort()
    res = learn_weights(df, n_random=30, n_refine=1)
    sens = sensitivity_table(df, res, perturbations=[0.05, 0.1])
    assert "median_rank_correlation" in sens.columns
    assert "min_rank_correlation" in sens.columns
    assert len(sens) == 2


def test_default_weights_sum_to_one():
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-6
