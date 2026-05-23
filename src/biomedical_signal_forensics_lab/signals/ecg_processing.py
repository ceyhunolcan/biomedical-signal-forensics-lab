"""ECG processing: bandpass, R-peak detection, RR intervals, SQI.

Deliberately classical methods. No deep learning here: the point is
that the downstream forensics layer should work even when the signal
processing is plain-vanilla.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks


def bandpass(signal: np.ndarray, fs: int, lo: float = 0.5, hi: float = 40.0,
             order: int = 3) -> np.ndarray:
    nyq = 0.5 * fs
    b, a = butter(order, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, signal)


def detect_r_peaks(signal: np.ndarray, fs: int, refractory_ms: int = 250) -> np.ndarray:
    """Very simple amplitude-threshold detector after bandpass + squaring."""
    if signal.size == 0:
        return np.array([], dtype=int)
    sig = bandpass(signal, fs)
    sig_sq = sig ** 2
    thr = max(np.mean(sig_sq) + 2 * np.std(sig_sq), 1e-6)
    distance = int(fs * refractory_ms / 1000.0)
    peaks, _ = find_peaks(sig_sq, height=thr, distance=max(distance, 1))
    return peaks


def rr_intervals_ms(peaks: np.ndarray, fs: int) -> np.ndarray:
    if peaks.size < 2:
        return np.array([])
    return np.diff(peaks) * 1000.0 / fs


def signal_quality_index(signal: np.ndarray, fs: int) -> float:
    """A bounded [0, 1] SQI: penalize flatness, saturation, and very high noise."""
    if signal.size == 0:
        return 0.0
    std = float(np.std(signal))
    if std < 1e-4:
        return 0.0
    # ratio of in-band power to total
    sig = bandpass(signal, fs, 0.5, 40.0)
    in_band = float(np.var(sig))
    total = float(np.var(signal)) + 1e-9
    band_ratio = np.clip(in_band / total, 0.0, 1.0)
    # peak count plausibility (40–180 bpm over the window)
    peaks = detect_r_peaks(signal, fs)
    seconds = max(len(signal) / fs, 1e-3)
    bpm = len(peaks) / seconds * 60.0
    bpm_score = 1.0 if 40 <= bpm <= 180 else max(0.0, 1.0 - abs(bpm - 70) / 200.0)
    return float(np.clip(0.6 * band_ratio + 0.4 * bpm_score, 0.0, 1.0))
