"""Smoke-level checks for the signal processing module."""
import numpy as np

from src.signals import ecg_processing as ecg
from src.signals import ppg_processing as ppg
from src.signals import hrv_processing as hrv


def _fake_ecg(fs=250, seconds=10, hr_bpm=70, noise=0.02, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(0, seconds, 1 / fs)
    period = 60 / hr_bpm
    sig = np.zeros_like(t)
    for k in range(int(seconds / period) + 1):
        center = k * period
        sig += 1.2 * np.exp(-((t - center) ** 2) / (2 * 0.01 ** 2))
    sig += noise * rng.standard_normal(t.size)
    return sig, fs


def _fake_ppg(fs=64, seconds=10, hr_bpm=70, noise=0.03, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(0, seconds, 1 / fs)
    pulse = np.sin(2 * np.pi * (hr_bpm / 60.0) * t)
    pulse += 0.3 * np.sin(2 * np.pi * 2 * (hr_bpm / 60.0) * t)
    pulse += noise * rng.standard_normal(t.size)
    return pulse, fs


def test_ecg_bandpass_preserves_length():
    sig, fs = _fake_ecg()
    out = ecg.bandpass(sig, fs)
    assert out.shape == sig.shape
    assert np.all(np.isfinite(out))


def test_ecg_r_peaks_recover_heart_rate():
    sig, fs = _fake_ecg(hr_bpm=72, seconds=20, noise=0.01)
    peaks = ecg.detect_r_peaks(sig, fs)
    assert len(peaks) >= 10
    rr = ecg.rr_intervals_ms(peaks, fs)
    assert 700 < np.median(rr) < 900  # ~833 ms at 72 bpm


def test_ppg_motion_score_grows_with_noise():
    clean, fs = _fake_ppg(noise=0.01)
    dirty, _ = _fake_ppg(noise=0.4)
    assert ppg.motion_artifact_score(clean, fs) < ppg.motion_artifact_score(dirty, fs)


def test_hrv_rmssd_positive_on_variable_rr():
    rr = np.array([800, 820, 790, 850, 810, 830, 800], dtype=float)
    assert hrv.rmssd(rr) > 0


def test_hrv_correction_removes_extreme_outliers():
    # 3000 ms is outside the default [300, 2000] window and should be interp'd out.
    rr_with_outlier = np.array([800, 820, 3000, 810, 820, 840], dtype=float)
    rr_clean = np.array([800, 820, 815, 810, 820, 840], dtype=float)
    fixed = hrv.artifact_corrected_rmssd(rr_with_outlier)
    raw = hrv.rmssd(rr_with_outlier)
    # raw includes the 3000 → huge diff → huge RMSSD; fixed should be smaller
    assert fixed < raw
    # corrected value should be close to what we'd get on a clean version
    expected = hrv.rmssd(rr_clean)
    assert abs(fixed - expected) < expected * 2  # within a factor of ~2
