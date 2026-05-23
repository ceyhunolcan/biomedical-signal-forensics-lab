"""Regression tests for bug audit round 2.

Each test corresponds to a specific issue surfaced during the round-2
adversarial sweep. These tests use plain try/except so they run under both
pytest and the sandbox's minimal test runner.
"""
import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.confounding.causal_inference import DAG, aipw, _binarize
from biomedical_signal_forensics_lab.data.real_data_adapter import FitbitLikeAdapter
from biomedical_signal_forensics_lab.reliability.biomarker_trust_score import DigitalBiomarkerTrustScore
from biomedical_signal_forensics_lab.reliability.weight_optimization import learn_weights


def _assert_raises(exc_type, fn, match_substring=None):
    try:
        fn()
    except exc_type as e:
        if match_substring is not None:
            assert match_substring in str(e), f"expected {match_substring!r} in {e!r}"
        return
    raise AssertionError(f"Did not raise {exc_type.__name__}")


# --- Bug A: AIPW with non-numeric multi-level treatment ------------------

def test_aipw_raises_on_multi_level_string_treatment():
    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame({
        "T": rng.choice(["low", "mid", "high"], n),
        "C": rng.normal(0, 1, n),
        "Y": rng.normal(0, 1, n),
    })
    _assert_raises(ValueError,
                   lambda: aipw(df, "T", "Y", ["C"], n_bootstrap=5),
                   match_substring="non-numeric")


def test_binarize_handles_binary_strings():
    s = pd.Series(["yes", "no", "yes", "no"])
    out = _binarize(s)
    assert set(out.dropna().unique()) == {0.0, 1.0}


def test_binarize_handles_already_binary_ints():
    s = pd.Series([0, 1, 0, 1, 0])
    out = _binarize(s)
    assert set(out.dropna().unique()) == {0.0, 1.0}


def test_binarize_handles_binary_floats():
    s = pd.Series([1.0, 2.0, 1.0, 2.0])
    out = _binarize(s)
    assert set(out.dropna().unique()) == {0.0, 1.0}


def test_binarize_continuous_falls_back_to_median():
    s = pd.Series(np.arange(20, dtype=float))
    out = _binarize(s)
    # Median is 9.5, so 10 values above (1), 10 at/below (0)
    counts = out.value_counts().sort_index()
    assert counts.iloc[0] == 10 and counts.iloc[1] == 10


# --- Bug B: adapter when both source AND canonical target columns exist --

def test_adapter_handles_existing_canonical_column():
    """If the input already has a column named like the canonical target,
    the source column wins (after a warning)."""
    df = pd.DataFrame({
        "user_id": ["u1", "u2", "u3"],
        "participant_id": ["pre_existing_x", "pre_existing_y", "pre_existing_z"],
    })
    out, rep = FitbitLikeAdapter().adapt(df)
    assert len(out) == 3
    # The source column 'user_id' should have been renamed to 'participant_id'
    # and the original 'participant_id' should have been dropped first.
    assert list(out["participant_id"]) == ["u1", "u2", "u3"]


# --- Concern 1: DAG.back_door with treatment == outcome ------------------

def test_dag_back_door_rejects_self_loop_query():
    g = DAG()
    g.add_edge("A", "B")
    g.add_edge("C", "A")
    _assert_raises(ValueError,
                   lambda: g.back_door_adjustment_set("A", "A"),
                   match_substring="same node")


# --- Concern 2: learn_weights with too-small cohort ----------------------

def test_learn_weights_handles_too_small_cohort():
    """Two participants, 14 days each: not enough for a meaningful search.
    Should return NaN scores with a clear notes string, not a -2.0 sentinel."""
    rng = np.random.default_rng(0)
    n = 28
    df = pd.DataFrame({
        "participant_id": ["p1"] * 14 + ["p2"] * 14,
        "date": list(pd.date_range("2024-01-01", periods=14)) * 2,
        "device_type": ["A"] * n,
        "resting_hr": 60 + rng.normal(0, 2, n),
        "hrv_rmssd": 45 + rng.normal(0, 4, n),
        "sleep_duration": [7.0] * n,
        "sleep_efficiency": [0.85] * n,
        "wearable_minutes": [1200] * n,
        "missing_wearable_flag": [0] * n,
        "temperature_c": [22.0] * n,
        "aqi": [50.0] * n,
        "step_count": [8000] * n,
        "heat_index": [22.0] * n,
    })
    res = learn_weights(df, n_random=20, n_refine=1, holdout_fraction=0.3)
    # Should be NaN, never the -2.0 sentinel
    assert res.spearman_train != res.spearman_train  # NaN
    assert res.spearman_train > -1.5 or res.spearman_train != res.spearman_train
    # Should fall back to defaults
    from biomedical_signal_forensics_lab.reliability.weight_optimization import DEFAULT_WEIGHTS
    for k, v in DEFAULT_WEIGHTS.items():
        assert abs(res.weights[k] - v) < 1e-9


# --- Concern 3: device_bias when HR all-NaN even with multiple devices ---

def test_device_bias_is_nan_when_hr_all_nan_even_with_multiple_devices():
    n = 30
    df = pd.DataFrame({
        "participant_id": ["p"] * n,
        "date": pd.date_range("2024-01-01", periods=n),
        "device_type": ["A"] * 15 + ["B"] * 15,
        "resting_hr": [np.nan] * n,
        "hrv_rmssd": [45.0] * n,
        "sleep_duration": [7] * n,
        "sleep_efficiency": [0.85] * n,
        "wearable_minutes": [1200] * n,
        "missing_wearable_flag": [0] * n,
        "temperature_c": [22] * n,
        "aqi": [50] * n,
        "step_count": [8000] * n,
        "heat_index": [22] * n,
    })
    out = DigitalBiomarkerTrustScore().cohort_scores(df)
    db = out["device_bias_score"].iloc[0]
    assert db != db  # NaN


# --- Sanity: every fix above doesn't break the happy path -----------------

def test_aipw_binary_string_treatment_still_works():
    rng = np.random.default_rng(0)
    n = 200
    high = rng.normal(2, 1, n)
    low = rng.normal(0, 1, n)
    T = rng.choice(["control", "treated"], n)
    df = pd.DataFrame({
        "T": T,
        "C": rng.normal(0, 1, n),
        "Y": np.where(T == "treated", high, low) + 0.5 * rng.normal(0, 1, n),
    })
    e = aipw(df, "T", "Y", ["C"], n_bootstrap=20)
    # treated - control ≈ 2, so estimate should be positive
    assert e.point_estimate > 0
    assert np.isfinite(e.point_estimate)
