"""Noise spike and flatline detection."""
from __future__ import annotations

import numpy as np

from .motion_artifacts import ArtifactFinding


def detect_noise_spikes(signal: np.ndarray, z_threshold: float = 4.0) -> ArtifactFinding:
    if signal.size < 4:
        return ArtifactFinding(0, 0.0, "Too short for spike detection.")
    sig = signal - np.median(signal)
    mad = float(np.median(np.abs(sig - np.median(sig))) + 1e-6)
    z = np.abs(sig) / (1.4826 * mad)
    n_spikes = int((z > z_threshold).sum())
    severity = float(np.clip(n_spikes / max(len(signal) * 0.02, 1.0), 0.0, 1.0))
    return ArtifactFinding(int(n_spikes > 0), severity,
                           f"n_spikes={n_spikes}, z_threshold={z_threshold}")


def detect_flatline(signal: np.ndarray, min_flat_samples: int = 64,
                    variance_threshold: float = 1.0e-4) -> ArtifactFinding:
    if signal.size < min_flat_samples:
        return ArtifactFinding(0, 0.0, "Window too short for flatline check.")
    # rolling variance via cumulative trick
    window = min_flat_samples
    sq = signal.astype(float) ** 2
    s = np.cumsum(signal)
    s2 = np.cumsum(sq)
    means = (s[window - 1:] - np.concatenate([[0], s[:-window]])) / window
    var = (s2[window - 1:] - np.concatenate([[0], s2[:-window]])) / window - means ** 2
    flat_windows = int((var < variance_threshold).sum())
    flag = int(flat_windows > 0)
    severity = float(np.clip(flat_windows / max(len(var) * 0.1, 1.0), 0.0, 1.0))
    return ArtifactFinding(flag, severity,
                           f"flat_windows={flat_windows}, threshold={variance_threshold}")
