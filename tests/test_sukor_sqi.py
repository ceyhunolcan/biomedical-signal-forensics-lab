"""Tests for the Sukor 2011 PPG SQI baseline."""
import numpy as np

from biomedical_signal_forensics_lab.signals.sukor_sqi import (
    PP_INTERVAL_CV_MAX, PULSE_AMPLITUDE_CV_MAX,
    SukorSQI, batch_sukor, sukor_ppg_sqi,
)


def _clean_ppg(seconds=5, fs=64, hr_bpm=72, seed=0):
    """A clean PPG-like signal at the given HR."""
    rng = np.random.default_rng(seed)
    t = np.arange(seconds * fs) / fs
    f = hr_bpm / 60.0
    sig = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    sig += 0.02 * rng.standard_normal(len(sig))
    return sig


def _noisy_ppg(seconds=5, fs=64, seed=0):
    """A signal with no pulsatile structure."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal(seconds * fs)


def test_sukor_clean_signal_acceptable():
    sig = _clean_ppg()
    result = sukor_ppg_sqi(sig, fs=64)
    assert isinstance(result, SukorSQI)
    assert result.n_pulses >= 3
    assert result.acceptable


def test_sukor_noisy_signal_rejected():
    sig = _noisy_ppg()
    result = sukor_ppg_sqi(sig, fs=64)
    assert not result.acceptable


def test_sukor_empty_window_rejected():
    result = sukor_ppg_sqi(np.array([]), fs=64)
    assert not result.acceptable
    assert result.n_pulses == 0


def test_sukor_too_short_rejected():
    """Less than 3 seconds of data should reject without crashing."""
    result = sukor_ppg_sqi(np.zeros(30), fs=64)
    assert not result.acceptable


def test_sukor_nan_only_rejected():
    result = sukor_ppg_sqi(np.full(320, np.nan), fs=64)
    assert not result.acceptable


def test_sukor_partial_nan_does_not_crash():
    sig = _clean_ppg()
    sig[50:60] = np.nan
    result = sukor_ppg_sqi(sig, fs=64)
    # No assertion on the outcome; just must not crash
    assert isinstance(result, SukorSQI)


def test_batch_sukor_returns_one_per_window():
    windows = np.stack([_clean_ppg(seed=i) for i in range(5)])
    results = batch_sukor(windows, fs=64)
    assert len(results) == 5
    for r in results:
        assert isinstance(r, SukorSQI)


def test_sukor_intervals_within_published_ranges_on_clean_data():
    """A clean steady-rate signal should have small interval CV."""
    sig = _clean_ppg(hr_bpm=72)
    result = sukor_ppg_sqi(sig, fs=64)
    assert result.pp_interval_cv < PP_INTERVAL_CV_MAX
    assert result.pulse_amplitude_cv < PULSE_AMPLITUDE_CV_MAX
