"""Orphanidou-style SQI baseline tests."""
import numpy as np

from biomedical_signal_forensics_lab.signals.orphanidou_sqi import (
    orphanidou_ecg_sqi, orphanidou_ppg_sqi,
    batch_orphanidou, head_to_head,
)


def _clean_ppg(fs=64, seconds=5, hr_bpm=72, seed=0):
    rng = np.random.default_rng(seed)
    t = np.linspace(0, seconds, fs * seconds, endpoint=False)
    sig = np.sin(2 * np.pi * (hr_bpm / 60.0) * t)
    sig += 0.3 * np.sin(2 * np.pi * 2 * (hr_bpm / 60.0) * t)
    sig += 0.02 * rng.standard_normal(len(t))
    return sig


def _clean_ecg(fs=250, seconds=5, hr_bpm=72, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(0, seconds, 1 / fs)
    period = 60 / hr_bpm
    sig = np.zeros_like(t)
    for k in range(int(seconds / period) + 1):
        center = k * period
        sig += 1.2 * np.exp(-((t - center) ** 2) / (2 * 0.012 ** 2))
    sig += 0.02 * rng.standard_normal(t.size)
    return sig


def test_orphanidou_accepts_clean_ppg():
    sig = _clean_ppg()
    out = orphanidou_ppg_sqi(sig, fs=64)
    assert out.acceptable
    assert out.template_corr > 0.86
    assert 40 <= out.hr_bpm <= 180


def test_orphanidou_rejects_noisy_ppg():
    rng = np.random.default_rng(42)
    clean = _clean_ppg()
    noisy = clean + 2.0 * rng.standard_normal(len(clean))
    out = orphanidou_ppg_sqi(noisy, fs=64)
    assert not out.acceptable


def test_orphanidou_accepts_clean_ecg():
    sig = _clean_ecg()
    out = orphanidou_ecg_sqi(sig, fs=250)
    assert out.acceptable
    assert out.template_corr > 0.66


def test_orphanidou_rejects_flatline():
    sig = np.zeros(64 * 5)
    out = orphanidou_ppg_sqi(sig, fs=64)
    assert not out.acceptable
    assert out.n_beats < 2 or out.template_corr != out.template_corr


def test_orphanidou_rejects_out_of_range_hr():
    """Very fast oscillation should fail at least one of the four rules
    (in practice the bandpass aliases it, so it can fail via rr_ratio or
    template_corr rather than hr_range)."""
    fs = 64
    t = np.linspace(0, 5, fs * 5, endpoint=False)
    fast = np.sin(2 * np.pi * 8.0 * t)
    out = orphanidou_ppg_sqi(fast, fs=fs)
    assert not out.acceptable
    # At least one rule fails
    assert not all(out.rule_passed.values())


def test_batch_returns_one_per_window():
    rng = np.random.default_rng(0)
    n = 20
    windows = np.array([_clean_ppg(seed=i) + 0.05 * rng.standard_normal(64 * 5)
                        for i in range(n)])
    out = batch_orphanidou(windows, fs=64, modality="ppg")
    assert len(out) == n


def test_head_to_head_returns_agreement_summary():
    rng = np.random.default_rng(0)
    n = 30
    windows = []
    in_house = []
    # Mix: half clean, half noisy. In-house knows which is which.
    for i in range(n):
        clean_or_not = i % 2 == 0
        sig = _clean_ppg(seed=i)
        if not clean_or_not:
            sig = sig + 1.5 * rng.standard_normal(len(sig))
        windows.append(sig)
        in_house.append(0.95 if clean_or_not else 0.2)
    windows = np.array(windows)
    summary = head_to_head(windows, np.array(in_house), fs=64, modality="ppg")
    assert summary.n_windows == n
    assert 0 <= summary.orphanidou_acceptable_frac <= 1
    # If in-house and Orphanidou both correctly separate the clean half,
    # their agreement should be strongly positive.
    assert summary.point_biserial_with_binary > 0.5
