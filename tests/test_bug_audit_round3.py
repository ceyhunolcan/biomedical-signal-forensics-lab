"""Regression tests for bug audit round 3.

Issues surfaced when adversarially probing the v0.3.0 additions
(Orphanidou baseline, bootstrap test-retest, generator stress test,
report-generator section helpers).
"""
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.signals.orphanidou_sqi import (
    orphanidou_ppg_sqi, orphanidou_ecg_sqi, head_to_head,
)
from biomedical_signal_forensics_lab.reports.report_generator import _orphanidou_comparison_section


# --- Bug 1: empty / too-short / NaN windows must not crash filtfilt ------

def test_orphanidou_empty_window_returns_unacceptable():
    out = orphanidou_ppg_sqi(np.array([], dtype=float), fs=64)
    assert out.acceptable is False
    assert out.n_beats == 0


def test_orphanidou_too_short_window_returns_unacceptable():
    """filtfilt has a padlen ~21; anything shorter would crash. The guard
    requires at least 3 seconds of data."""
    out = orphanidou_ppg_sqi(np.zeros(30), fs=64)
    assert out.acceptable is False


def test_orphanidou_all_nan_window_returns_unacceptable():
    out = orphanidou_ppg_sqi(np.full(320, np.nan), fs=64)
    assert out.acceptable is False
    assert out.hr_bpm != out.hr_bpm  # NaN


def test_orphanidou_partially_nan_window_succeeds_or_fails_cleanly():
    """A window with a few NaN samples sprinkled in should not crash."""
    rng = np.random.default_rng(0)
    t = np.linspace(0, 5, 320, endpoint=False)
    sig = np.sin(2 * np.pi * 1.2 * t) + 0.05 * rng.standard_normal(320)
    sig[50] = np.nan
    sig[100] = np.nan
    out = orphanidou_ppg_sqi(sig, fs=64)
    # Either acceptable or not, but should not throw
    assert isinstance(out.acceptable, bool) or hasattr(out, "acceptable")


def test_orphanidou_ecg_empty_window_returns_unacceptable():
    out = orphanidou_ecg_sqi(np.array([], dtype=float), fs=250)
    assert out.acceptable is False


# --- Bug 2: head_to_head with mismatched array lengths -------------------

def test_head_to_head_truncates_on_length_mismatch():
    rng = np.random.default_rng(0)
    windows = np.array([rng.normal(0, 1, 320) for _ in range(20)])
    in_house = np.array([0.5] * 5)
    s = head_to_head(windows, in_house, fs=64)
    # Should truncate to the common length 5, not crash
    assert s.n_windows == 5


def test_head_to_head_empty_inputs():
    s = head_to_head(np.empty((0, 320)), np.array([]), fs=64)
    assert s.n_windows == 0
    assert s.spearman_with_continuous != s.spearman_with_continuous  # NaN


def test_head_to_head_handles_nan_in_in_house_sqi():
    rng = np.random.default_rng(0)
    windows = np.array([rng.normal(0, 1, 320) for _ in range(10)])
    in_house = np.full(10, np.nan)
    s = head_to_head(windows, in_house, fs=64)
    # n_windows still 10; all valid stats are NaN
    assert s.n_windows == 10
    assert s.spearman_with_continuous != s.spearman_with_continuous


# --- Bug 3: malformed baseline-comparison CSV ----------------------------

def test_orphanidou_section_handles_malformed_csv(tmp_path):
    """The report-generator helper must not crash on a CSV with the wrong columns."""
    from biomedical_signal_forensics_lab.utils.paths import resolve
    p = resolve("results/tables/baseline_comparison_orphanidou.csv")
    backup = p.read_text() if p.exists() else None
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("not_a_real_column,nothing\n1,2\n")
        out = _orphanidou_comparison_section()
        # Should be the fallback message, not the populated table
        assert "unreadable" in out or "not yet computed" in out
    finally:
        if backup is not None:
            p.write_text(backup)
        else:
            p.unlink()


def test_orphanidou_section_handles_empty_csv():
    """An empty CSV (header only) should hit the empty-frame path."""
    from biomedical_signal_forensics_lab.utils.paths import resolve
    p = resolve("results/tables/baseline_comparison_orphanidou.csv")
    backup = p.read_text() if p.exists() else None
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("n_windows,in_house_mean_sqi\n")
        out = _orphanidou_comparison_section()
        assert "unreadable" in out or "not yet computed" in out
    finally:
        if backup is not None:
            p.write_text(backup)
        else:
            p.unlink()
