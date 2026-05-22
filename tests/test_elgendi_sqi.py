"""Tests for the Elgendi 2016 PPG signal quality module."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.signals.elgendi_sqi import (
    ElgendiSQI,
    batch_elgendi,
    elgendi_window,
    four_way_sqi_agreement,
)


def _synthetic_ppg(n_seconds: float = 5.0, fs: int = 64,
                    snr_db: float = 20.0, seed: int = 0) -> np.ndarray:
    """Build a PPG-like signal with positive skew."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(n_seconds * fs)) / fs
    pulse = np.maximum(0, np.sin(2 * np.pi * 1.2 * t) ** 3)
    pulse = pulse - pulse.mean()
    signal_power = (pulse ** 2).mean()
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = rng.normal(0, np.sqrt(noise_power), len(t))
    return pulse + noise


def test_clean_ppg_passes_all_three_statistics():
    sig = _synthetic_ppg(snr_db=25)
    r = elgendi_window(sig, fs=64)
    assert r.acceptable
    assert r.skewness > 0
    assert r.ssqi_ok and r.ksqi_ok and r.esqi_ok


def test_pure_noise_fails():
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 1, 64 * 5)
    r = elgendi_window(noise, fs=64)
    assert not r.acceptable


def test_flatline_returns_unacceptable_with_nan_stats():
    flat = np.zeros(64 * 5)
    r = elgendi_window(flat, fs=64)
    assert not r.acceptable
    assert np.isnan(r.skewness)
    assert np.isnan(r.kurtosis)
    assert np.isnan(r.entropy)


def test_empty_window_returns_unacceptable():
    r = elgendi_window(np.array([]), fs=64)
    assert not r.acceptable
    assert r.n_samples == 0


def test_too_short_window_returns_unacceptable():
    r = elgendi_window(np.array([1.0, 2.0, 3.0]), fs=64)
    assert not r.acceptable


def test_all_nan_window_returns_unacceptable():
    r = elgendi_window(np.full(64 * 5, np.nan), fs=64)
    assert not r.acceptable
    assert np.isnan(r.skewness)


def test_partial_nan_window_handled():
    sig = _synthetic_ppg()
    sig[::10] = np.nan
    r = elgendi_window(sig, fs=64)
    # Some NaN is tolerated; the result should be a valid dataclass
    assert isinstance(r, ElgendiSQI)
    assert isinstance(r.acceptable, bool)


def test_invert_flips_skewness_sign():
    sig = _synthetic_ppg(snr_db=25)
    r_orig = elgendi_window(sig, fs=64, invert=False)
    r_inv = elgendi_window(sig, fs=64, invert=True)
    # Skewness changes sign under polarity inversion
    if np.isfinite(r_orig.skewness) and np.isfinite(r_inv.skewness):
        assert np.isclose(r_orig.skewness, -r_inv.skewness, atol=1e-6)


def test_batch_returns_one_row_per_window():
    sigs = np.array([_synthetic_ppg(seed=i) for i in range(10)])
    df = batch_elgendi(sigs, fs=64, auto_invert=False)
    assert len(df) == 10
    expected_cols = {
        "elgendi_acceptable", "elgendi_skewness", "elgendi_kurtosis",
        "elgendi_entropy", "elgendi_ssqi_ok", "elgendi_ksqi_ok",
        "elgendi_esqi_ok", "elgendi_n_samples", "elgendi_polarity_inverted",
    }
    assert expected_cols.issubset(set(df.columns))


def test_batch_auto_invert_detects_inverted_polarity():
    """If we feed inverted clean PPG, auto_invert should detect and correct."""
    sigs = np.array([-_synthetic_ppg(seed=i) for i in range(20)])
    df = batch_elgendi(sigs, fs=64, auto_invert=True)
    assert df["elgendi_polarity_inverted"].iloc[0]
    # After auto-inversion, skewness should be positive again
    median_skew = df["elgendi_skewness"].median()
    assert median_skew > 0


def test_batch_auto_invert_off_does_not_invert():
    sigs = np.array([-_synthetic_ppg(seed=i) for i in range(20)])
    df = batch_elgendi(sigs, fs=64, auto_invert=False)
    assert not df["elgendi_polarity_inverted"].iloc[0]
    median_skew = df["elgendi_skewness"].median()
    assert median_skew < 0  # stays negative


def test_batch_does_not_invert_when_clean_polarity():
    sigs = np.array([_synthetic_ppg(seed=i) for i in range(20)])
    df = batch_elgendi(sigs, fs=64, auto_invert=True)
    # Already-positive polarity should not be inverted
    assert not df["elgendi_polarity_inverted"].iloc[0]


def test_four_way_agreement_perfect_case():
    n = 100
    all_pass = np.ones(n, dtype=int)
    result = four_way_sqi_agreement(all_pass, all_pass, all_pass, all_pass)
    assert result["n_windows"] == n
    # All identical means kappa is undefined (constant arrays); function
    # returns 0.0 in that case
    assert result["kappa_inhouse_vs_orph"] == 0.0


def test_four_way_agreement_in_house_passes_when_others_fail():
    n = 100
    rng = np.random.default_rng(0)
    in_h = np.ones(n, dtype=int)
    orph = rng.integers(0, 2, n)
    suk = rng.integers(0, 2, n)
    elg = rng.integers(0, 2, n)
    result = four_way_sqi_agreement(in_h, orph, suk, elg)
    # in_house passes 100%; the rate at which it passes while all 3 fail
    # equals the rate that orph & suk & elg all fail
    expected = float(((orph == 0) & (suk == 0) & (elg == 0)).mean())
    assert abs(result["inhouse_passes_when_all_published_fail"] - expected) < 1e-9


def test_four_way_agreement_too_few_windows_returns_note():
    result = four_way_sqi_agreement(
        np.array([1, 0]), np.array([1, 0]),
        np.array([0, 1]), np.array([1, 1]),
    )
    assert "note" in result


def test_four_way_agreement_truncates_to_shortest():
    n_short = 20
    n_long = 50
    result = four_way_sqi_agreement(
        np.ones(n_long, dtype=int),
        np.ones(n_short, dtype=int),
        np.ones(n_long, dtype=int),
        np.ones(n_long, dtype=int),
    )
    assert result["n_windows"] == n_short
