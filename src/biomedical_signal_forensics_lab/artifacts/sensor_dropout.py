"""Sensor dropout detection: long runs of zeros / NaNs."""
from __future__ import annotations

import numpy as np

from .motion_artifacts import ArtifactFinding


def detect(signal: np.ndarray, min_dropout_samples: int = 32,
           zero_tolerance: float = 0.02) -> ArtifactFinding:
    """Detect runs of effectively-zero or NaN samples.

    A sample counts as 'dropout' if it is NaN or its absolute value is below
    `zero_tolerance`. Returns a binary flag (longest run >= threshold) plus a
    continuous severity that saturates at 4x the threshold length.
    """
    if signal.size == 0:
        return ArtifactFinding(0, 0.0, "Empty signal.")
    arr = np.asarray(signal, dtype=float)
    # NaN counts as dropout. `np.abs(nan) <= tol` returns False, so we have
    # to explicitly OR the NaN mask in.
    mask = ~np.isfinite(arr) | (np.abs(arr) <= zero_tolerance)
    if not mask.any():
        return ArtifactFinding(0, 0.0, "No dropout segments detected.")
    runs = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    starts = np.where(runs == 1)[0]
    ends = np.where(runs == -1)[0]
    lengths = ends - starts
    if lengths.size == 0:
        return ArtifactFinding(0, 0.0, "No dropout segments detected.")
    longest = int(lengths.max())
    flag = int(longest >= min_dropout_samples)
    severity = float(np.clip(longest / (min_dropout_samples * 4), 0.0, 1.0))
    return ArtifactFinding(flag, severity,
                           f"longest_dropout={longest} samples (thr={min_dropout_samples})")
