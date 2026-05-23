"""HRV metrics: RMSSD, SDNN, mean RR, artifact-corrected variants.

Operates on RR interval arrays (in milliseconds).
"""
from __future__ import annotations

import numpy as np


def rmssd(rr_ms: np.ndarray) -> float:
    if rr_ms.size < 2:
        return float("nan")
    diffs = np.diff(rr_ms)
    return float(np.sqrt(np.mean(diffs ** 2)))


def sdnn(rr_ms: np.ndarray) -> float:
    if rr_ms.size < 2:
        return float("nan")
    return float(np.std(rr_ms, ddof=1))


def mean_rr(rr_ms: np.ndarray) -> float:
    if rr_ms.size == 0:
        return float("nan")
    return float(np.mean(rr_ms))


def artifact_corrected_rmssd(rr_ms: np.ndarray, lo: int = 300, hi: int = 2000) -> float:
    """Drop impossible RRs, linearly interpolate, then compute RMSSD."""
    if rr_ms.size < 2:
        return float("nan")
    rr = rr_ms.astype(float)
    mask = (rr >= lo) & (rr <= hi)
    if mask.sum() < 2:
        return float("nan")
    # linear interp over invalid points
    idx = np.arange(len(rr))
    rr_clean = np.interp(idx, idx[mask], rr[mask])
    return rmssd(rr_clean)
