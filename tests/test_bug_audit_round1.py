"""Regression tests for the bug audit (round 1).

Each test corresponds to a specific issue found during the systematic
edge-case sweep. If any of these break in the future, look at the linked
bug number in the commit history.

These tests use plain try/except rather than pytest.raises so that they
run both under pytest and under the sandbox's minimal test runner.
"""
import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.confounding.causal_inference import DAG
from biomedical_signal_forensics_lab.data.real_data_adapter import FitbitLikeAdapter
from biomedical_signal_forensics_lab.data.validation import validate
from biomedical_signal_forensics_lab.reliability.biomarker_trust_score import DigitalBiomarkerTrustScore
from biomedical_signal_forensics_lab.reliability.change_point import binary_segmentation, bocpd
from biomedical_signal_forensics_lab.reliability.fairness_audit import fairness_audit, disparity_summary
from biomedical_signal_forensics_lab.reliability.intraclass_correlation import icc_2_1
from biomedical_signal_forensics_lab.reliability.weight_optimization import weekly_reproducibility_target


def _assert_raises(exc_type, fn, match_substring=None):
    try:
        fn()
    except exc_type as e:
        if match_substring is not None:
            assert match_substring in str(e), f"expected {match_substring!r} in {e!r}"
        return
    raise AssertionError(f"Did not raise {exc_type.__name__}")


def _minimal_frame(n=30, device="A", quality=0.85, artifacts=0.1, missing=0.05, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "participant_id": ["p1"] * n,
        "date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "device_type": [device] * n,
        "resting_hr": 60 + rng.normal(0, 2, n),
        "hrv_rmssd": 45 + rng.normal(0, 4, n),
        "sleep_duration": 7.0 + rng.normal(0, 0.4, n),
        "sleep_efficiency": np.clip(0.85 + rng.normal(0, 0.03, n), 0, 1),
        "step_count": 8000 + rng.normal(0, 500, n),
        "wearable_minutes": 1200 + rng.normal(0, 60, n),
        "temperature_c": 22 + rng.normal(0, 2, n),
        "heat_index": 22 + rng.normal(0, 3, n),
        "aqi": 50 + rng.normal(0, 5, n),
        "missing_wearable_flag": (rng.random(n) < missing).astype(int),
        "signal_quality_ground_truth": np.full(n, quality),
        "artifact_burden_ground_truth": np.full(n, artifacts),
        "reliability_ground_truth": np.full(n, 1 - artifacts),
    })


# --- Bug 1: NaN overall must yield an 'insufficient_data' category ---------

def test_all_nan_inputs_produce_insufficient_data_category():
    """All-NaN biomarker columns should not pose as 'unreliable'."""
    df = pd.DataFrame({
        "participant_id": ["p"] * 10,
        "date": pd.date_range("2024-01-01", periods=10),
        "device_type": ["A"] * 10,
        "resting_hr": [np.nan] * 10,
        "hrv_rmssd": [np.nan] * 10,
        "sleep_duration": [np.nan] * 10,
        "sleep_efficiency": [np.nan] * 10,
        "step_count": [np.nan] * 10,
        "wearable_minutes": [np.nan] * 10,
        "temperature_c": [np.nan] * 10,
        "aqi": [np.nan] * 10,
        "missing_wearable_flag": [np.nan] * 10,
    })
    r = DigitalBiomarkerTrustScore().score(df)
    assert r.category == "insufficient_data"
    assert r.overall_trust_score != r.overall_trust_score  # NaN


# --- Bug 5: cohort_scores must error clearly without participant_id --------

def test_cohort_scores_without_participant_id_raises():
    df = _minimal_frame().drop(columns=["participant_id"])
    _assert_raises(ValueError,
                   lambda: DigitalBiomarkerTrustScore().cohort_scores(df),
                   match_substring="participant_id")


# --- Bug 6: single-device cohort gets device_bias = 100, not 75 -----------

def test_single_device_cohort_has_perfect_device_bias_score():
    r = DigitalBiomarkerTrustScore().score(_minimal_frame(device="A"))
    assert r.components.device_bias_score == 100.0


# --- Bug 7: constant heat -> 100 confounding score, not 60 ----------------

def test_constant_heat_yields_perfect_confounding_score():
    df = _minimal_frame()
    df["heat_index"] = 22.0
    r = DigitalBiomarkerTrustScore().score(df)
    assert r.components.confounding_risk_score == 100.0


# --- Bug 2: change-point should tolerate NaN gaps -------------------------

def test_change_point_detectors_handle_nan_input():
    rng = np.random.default_rng(0)
    sig = np.concatenate([rng.normal(60, 2, 40), [np.nan] * 5, rng.normal(70, 2, 40)])
    bs = binary_segmentation(sig)
    bo = bocpd(sig)
    real_bs = [cp for cp in bs if abs(cp.delta) > 3.0]
    real_bo = [cp for cp in bo if abs(cp.delta) > 3.0 and cp.delta == cp.delta]
    assert len(real_bs) >= 1
    # No NaN deltas should ever appear in either output
    for cp in bs + bo:
        assert cp.delta == cp.delta  # not NaN


# --- Bug 3: validation flags all-NaN columns ------------------------------

def test_validation_flags_all_nan_columns():
    df = pd.DataFrame({c: [np.nan] * 10 for c in [
        "participant_id", "date", "resting_hr", "hrv_rmssd", "hrv_sdnn",
        "step_count", "active_minutes", "sleep_duration", "sleep_efficiency",
        "stress_proxy", "temperature_c", "humidity", "aqi", "heat_index",
        "wearable_minutes", "missing_wearable_flag",
        "signal_quality_ground_truth", "artifact_burden_ground_truth",
        "reliability_ground_truth",
    ]})
    vres = validate(df)
    assert not vres.ok
    assert "resting_hr" in vres.all_nan_columns


def test_adapter_with_wrong_schema_does_not_silently_pass_validation():
    """If the adapter can't map anything, validation must NOT report OK."""
    df = pd.DataFrame({"foo": [1, 2, 3], "bar": [4, 5, 6]})
    out, rep = FitbitLikeAdapter().adapt(df)
    # All canonical columns are NaN → validation should not be OK
    assert not rep.validation.ok
    assert len(rep.validation.all_nan_columns) > 0


# --- Bug 4: ICC drops NaN rows with documented behavior -------------------

def test_icc_drops_nan_rows():
    rng = np.random.default_rng(0)
    arr = rng.normal(50, 5, (20, 3))
    arr[5, 1] = np.nan
    arr[10, 2] = np.nan
    # default policy drops, returns finite ICC
    val = icc_2_1(arr)
    assert np.isfinite(val)


def test_icc_raise_policy_raises_on_nan():
    arr = np.array([[1.0, 2.0], [np.nan, 3.0]])
    _assert_raises(ValueError, lambda: icc_2_1(arr, nan_policy="raise"))


# --- Bug 11: disparity_summary returns empty on single-stratum input ------

def test_disparity_summary_empty_when_single_stratum():
    df = _minimal_frame(device="A")
    table = fairness_audit(df, stratify_by="device_type", n_bootstrap=5)
    assert len(table) == 1
    disp = disparity_summary(table)
    # Empty result with proper schema, no KeyError
    expected_cols = {"component", "min", "max", "disparity",
                     "min_stratum", "max_stratum"}
    assert expected_cols.issubset(set(disp.columns))
    assert len(disp) == 0


# --- Bug 12: DAG cycle is detected and raised -----------------------------

def test_dag_cycle_raises_on_back_door_query():
    g = DAG()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "A")
    assert g.has_cycle()
    _assert_raises(ValueError,
                   lambda: g.back_door_adjustment_set("A", "B"),
                   match_substring="cycle")


def test_dag_acyclic_passes():
    g = DAG()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("A", "D")
    assert not g.has_cycle()


# --- Bug 8: weekly_reproducibility_target empty frame has named columns ---

def test_weekly_reproducibility_empty_has_columns():
    df = pd.DataFrame({"participant_id": ["p1"] * 3,
                       "date": pd.date_range("2024-01-01", periods=3),
                       "hrv_rmssd": [40.0, 41.0, 42.0]})
    out = weekly_reproducibility_target(df)
    assert "participant_id" in out.columns
    assert "reproducibility" in out.columns
    assert len(out) == 0


# --- Sanity: clean inputs still work as before ----------------------------

def test_clean_inputs_unchanged_after_fixes():
    df = _minimal_frame(quality=0.9, artifacts=0.05, missing=0.02)
    r = DigitalBiomarkerTrustScore().score(df)
    # Should be in 'high' or 'moderate' on clean data; never NaN
    assert r.category in {"high", "moderate"}
    assert 60.0 <= r.overall_trust_score <= 100.0
