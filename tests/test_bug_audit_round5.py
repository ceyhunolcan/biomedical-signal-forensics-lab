"""Regression tests for bug audit round 5.

Issues surfaced when adversarially probing the v0.4.0 additions:
the ICC method comparison, the cross-cohort generalization check, and
the demoted PyTorch autoencoder.
"""
import numpy as np
import pandas as pd

from src.evaluation.cross_cohort_check import (
    CohortRegime, _generate_regime, predicted_vs_observed,
)


def _assert_raises(exc_type, fn, match_substring=None):
    try:
        fn()
    except exc_type as e:
        if match_substring is not None:
            assert match_substring in str(e), f"expected {match_substring!r} in {e!r}"
        return
    raise AssertionError(f"Did not raise {exc_type.__name__}")


# --- Bug A: predicted_vs_observed handles empty input ---------------------

def test_predicted_vs_observed_empty_dataframe():
    out = predicted_vs_observed(pd.DataFrame())
    assert list(out.columns) == ["check", "predicted", "observed", "pass"]
    assert len(out) == 0


def test_predicted_vs_observed_no_regime_column():
    """A table that has rows but no 'regime' column should be treated like empty."""
    table = pd.DataFrame({
        "something_else": ["x", "y"],
        "heat_hrv_screening_r": [-0.1, -0.2],
    })
    out = predicted_vs_observed(table)
    assert len(out) == 0


def test_predicted_vs_observed_one_regime_handles_missing_predictions():
    """When some regimes are missing from the table, get() returns NaN and
    those checks should report 'observed=nan' without crashing."""
    table = pd.DataFrame([{
        "regime": "default",
        "heat_hrv_screening_r": -0.1,
        "skin_tone_Q4_minus_Q1_sq": -5.0,
        "device_B_minus_A_hr_empirical": 3.0,
        "hrv_test_retest_r": 0.9,
    }])
    out = predicted_vs_observed(table)
    assert len(out) > 0
    # Several checks reference regimes that aren't in the table; their
    # observed values should be NaN, not crash the call.
    obs_strs = [str(v) for v in out["observed"]]
    assert any("nan" in s.lower() for s in obs_strs)


# --- Bug B: _generate_regime refuses non-finite coefficients --------------

def test_generate_regime_rejects_nan_coefficient():
    bad = CohortRegime(
        name="weird", heat_hrv_coef=float("nan"),
        skin_tone_penalty=0.0, device_b_offset=0.0,
        device_c_offset=0.0, description="",
    )
    _assert_raises(ValueError,
                   lambda: _generate_regime(bad, n_participants=10, n_days=7),
                   match_substring="non-finite")


def test_generate_regime_rejects_inf_coefficient():
    bad = CohortRegime(
        name="huge", heat_hrv_coef=0.0,
        skin_tone_penalty=float("inf"), device_b_offset=0.0,
        device_c_offset=0.0, description="",
    )
    _assert_raises(ValueError,
                   lambda: _generate_regime(bad, n_participants=10, n_days=7),
                   match_substring="non-finite")


def test_generate_regime_accepts_zero_coefficients():
    """Zero is finite and should be allowed (it disables an effect)."""
    clean = CohortRegime(
        name="z", heat_hrv_coef=0.0,
        skin_tone_penalty=0.0, device_b_offset=0.0,
        device_c_offset=0.0, description="",
    )
    df = _generate_regime(clean, n_participants=10, n_days=7)
    assert len(df) > 0
    # HRV should be finite (the only way it would be NaN is if HEAT_HRV_COEF was NaN)
    assert df["hrv_rmssd"].notna().any()


# --- Bug C: report includes the new ICC comparison section ----------------

def test_report_generator_has_icc_comparison_helper():
    """The helper function should exist and be callable, even with no CSV."""
    from src.reports.report_generator import _icc_comparison_section
    out = _icc_comparison_section()
    assert isinstance(out, str)
    assert len(out) > 0


def test_icc_comparison_section_handles_missing_csv():
    """Should fall back gracefully when the CSV doesn't exist."""
    from src.reports.report_generator import _icc_comparison_section
    from src.utils.paths import resolve
    p = resolve("results/tables/icc_vs_test_retest.csv")
    backup = p.read_text() if p.exists() else None
    try:
        if p.exists():
            p.unlink()
        out = _icc_comparison_section()
        assert "not yet computed" in out
    finally:
        if backup is not None:
            p.write_text(backup)


def test_icc_comparison_section_handles_malformed_csv():
    """Should fall back gracefully when the CSV is malformed."""
    from src.reports.report_generator import _icc_comparison_section
    from src.utils.paths import resolve
    p = resolve("results/tables/icc_vs_test_retest.csv")
    backup = p.read_text() if p.exists() else None
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("garbage,nonsense\n1,2\n")
        out = _icc_comparison_section()
        assert "unreadable" in out or "not yet computed" in out
    finally:
        if backup is not None:
            p.write_text(backup)
        else:
            if p.exists():
                p.unlink()


# --- Reproducibility check ------------------------------------------------

def test_evaluate_regime_is_reproducible_with_same_seed():
    from src.evaluation.cross_cohort_check import evaluate_regime, REGIMES
    a = evaluate_regime(REGIMES[0], n_participants=20, n_days=14, seed=42)
    b = evaluate_regime(REGIMES[0], n_participants=20, n_days=14, seed=42)
    for field in ("mean_cohort_dbts", "skin_tone_Q4_minus_Q1_sq",
                  "heat_hrv_screening_r"):
        assert a[field] == b[field], f"field {field} differs: {a[field]} vs {b[field]}"


# --- Train script with --include-extensions flag ---

def test_train_quality_model_main_signature_accepts_flag():
    """Confirm the public main() function has the include_extensions kwarg."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "tqm", str(Path(__file__).resolve().parents[1] / "scripts" / "train_quality_model.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import inspect
    sig = inspect.signature(mod.main)
    assert "include_extensions" in sig.parameters
    # Default should be False (baselines only)
    assert sig.parameters["include_extensions"].default is False
