"""PPG processing: smoothing, pulse-peak detection, motion estimation, SQI."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks


def smooth(signal: np.ndarray, window: int = 7) -> np.ndarray:
    if window <= 1 or signal.size == 0:
        return signal
    kernel = np.ones(window) / window
    return np.convolve(signal, kernel, mode="same")


def bandpass(signal: np.ndarray, fs: int, lo: float = 0.5, hi: float = 8.0,
             order: int = 3) -> np.ndarray:
    nyq = 0.5 * fs
    b, a = butter(order, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, signal)


def detect_pulse_peaks(signal: np.ndarray, fs: int) -> np.ndarray:
    if signal.size == 0:
        return np.array([], dtype=int)
    sig = bandpass(signal, fs)
    distance = int(fs * 0.4)  # min 0.4s between pulses
    peaks, _ = find_peaks(sig, distance=max(distance, 1))
    return peaks


def motion_artifact_score(signal: np.ndarray, fs: int) -> float:
    """High-frequency / low-frequency power ratio. Higher → more motion."""
    if signal.size < fs:
        return 0.0
    fft = np.fft.rfft(signal - np.mean(signal))
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / fs)
    power = np.abs(fft) ** 2
    low = power[(freqs >= 0.5) & (freqs <= 4.0)].sum() + 1e-9
    high = power[(freqs > 4.0) & (freqs <= 15.0)].sum()
    return float(np.clip(high / (low + high), 0.0, 1.0))


def signal_quality_index(signal: np.ndarray, fs: int) -> float:
    if signal.size == 0:
        return 0.0
    var = float(np.var(signal))
    if var < 1e-5:
        return 0.0
    motion = motion_artifact_score(signal, fs)
    peaks = detect_pulse_peaks(signal, fs)
    seconds = max(len(signal) / fs, 1e-3)
    bpm = len(peaks) / seconds * 60.0
    bpm_score = 1.0 if 40 <= bpm <= 180 else max(0.0, 1.0 - abs(bpm - 70) / 200.0)
    return float(np.clip(0.55 * (1 - motion) + 0.45 * bpm_score, 0.0, 1.0))
