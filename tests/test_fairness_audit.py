"""Fairness audit tests."""
import numpy as np
import pandas as pd

from src.reliability.fairness_audit import (
    fairness_audit, disparity_summary, multi_stratify,
)


def _cohort_with_two_devices(n_per=20, days=30, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for d_idx, dev in enumerate(["A", "B"]):
        # device B is artificially worse on signal_quality_ground_truth
        quality_offset = 0.0 if dev == "A" else -0.3
        for pid in range(n_per):
            for day in range(days):
                rows.append({
                    "participant_id": f"{dev}{pid:03d}",
                    "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=day),
                    "device_type": dev,
                    "resting_hr": 60 + rng.normal(0, 3),
                    "hrv_rmssd": 45 + rng.normal(0, 5),
                    "hrv_sdnn": 60 + rng.normal(0, 7),
                    "step_count": 7000 + rng.normal(0, 1000),
                    "active_minutes": 35 + rng.normal(0, 8),
                    "sleep_duration": 7.2 + rng.normal(0, 0.6),
                    "sleep_efficiency": np.clip(0.85 + rng.normal(0, 0.04), 0, 1),
                    "stress_proxy": rng.uniform(0, 1),
                    "temperature_c": 22 + rng.normal(0, 3),
                    "humidity": 55 + rng.normal(0, 10),
                    "aqi": 50 + rng.normal(0, 10),
                    "heat_index": 22 + rng.normal(0, 3),
                    "wearable_minutes": 1200 + rng.normal(0, 80),
                    "missing_wearable_flag": int(rng.random() < 0.05),
                    "signal_quality_ground_truth": np.clip(0.85 + quality_offset + rng.normal(0, 0.05), 0, 1),
                    "artifact_burden_ground_truth": np.clip(0.1 + rng.normal(0, 0.03), 0, 1),
                    "reliability_ground_truth": np.clip(0.9 + rng.normal(0, 0.03), 0, 1),
                })
    return pd.DataFrame(rows)


def test_fairness_audit_per_device_finds_quality_gap():
    df = _cohort_with_two_devices()
    table = fairness_audit(df, stratify_by="device_type", n_bootstrap=20)
    assert set(table["stratum_value"]) == {"A", "B"}
    qa = float(table.loc[table["stratum_value"] == "A", "signal_quality_score"].iloc[0])
    qb = float(table.loc[table["stratum_value"] == "B", "signal_quality_score"].iloc[0])
    assert qa > qb  # A is better; B has injected penalty


def test_fairness_audit_includes_confidence_intervals():
    df = _cohort_with_two_devices()
    table = fairness_audit(df, stratify_by="device_type", n_bootstrap=20)
    for _, row in table.iterrows():
        assert row["ci_low"] is not None
        assert row["ci_high"] is not None
        assert row["ci_low"] <= row["overall_trust_score"] <= row["ci_high"]


def test_disparity_summary_orders_by_gap():
    df = _cohort_with_two_devices()
    table = fairness_audit(df, stratify_by="device_type", n_bootstrap=10)
    disp = disparity_summary(table)
    # signal_quality should be near the top
    assert "signal_quality_score" in set(disp["component"])
    # disparity column descends
    diffs = disp["disparity"].to_numpy()
    assert all(diffs[i] >= diffs[i + 1] for i in range(len(diffs) - 1))


def test_numeric_stratifier_is_quartile_binned():
    df = _cohort_with_two_devices()
    # add an arbitrary numeric column
    df["age"] = np.linspace(20, 80, len(df))
    table = fairness_audit(df, stratify_by="age", n_bootstrap=0)
    # Should produce up to 4 strata named Q1..Q4
    assert set(table["stratum_value"]).issubset({"Q1", "Q2", "Q3", "Q4"})


def test_multi_stratify_returns_dict():
    df = _cohort_with_two_devices()
    out = multi_stratify(df, stratify_columns=["device_type"], n_bootstrap=0)
    assert "device_type" in out
    assert isinstance(out["device_type"], pd.DataFrame)
