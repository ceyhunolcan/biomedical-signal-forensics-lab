"""Timestamp jitter / gap detection."""
from __future__ import annotations

import numpy as np

from .motion_artifacts import ArtifactFinding


def detect(timestamps_ms: np.ndarray, expected_interval_ms: float,
           jitter_ms: float = 5.0, max_gap_factor: float = 3.0) -> ArtifactFinding:
    if timestamps_ms.size < 2:
        return ArtifactFinding(0, 0.0, "Too few timestamps to evaluate.")
    diffs = np.diff(timestamps_ms)
    jitter_violations = int((np.abs(diffs - expected_interval_ms) > jitter_ms).sum())
    gap_violations = int((diffs > expected_interval_ms * max_gap_factor).sum())
    total = jitter_violations + gap_violations
    severity = float(np.clip(total / len(diffs), 0.0, 1.0))
    flag = int(total > 0)
    return ArtifactFinding(
        flag, severity,
        f"jitter_violations={jitter_violations}, gap_violations={gap_violations}",
    )
