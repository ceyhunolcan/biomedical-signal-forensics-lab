"""Combine all artifact detectors into a per-window verdict."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from . import motion_artifacts, sensor_dropout, signal_noise
from .motion_artifacts import ArtifactFinding


@dataclass
class WindowArtifactReport:
    motion: ArtifactFinding
    dropout: ArtifactFinding
    spike: ArtifactFinding
    flatline: ArtifactFinding
    any_artifact: int
    artifact_burden: float

    def to_dict(self) -> dict[str, Any]:
        out = {f"motion_{k}": v for k, v in asdict(self.motion).items()}
        out.update({f"dropout_{k}": v for k, v in asdict(self.dropout).items()})
        out.update({f"spike_{k}": v for k, v in asdict(self.spike).items()})
        out.update({f"flatline_{k}": v for k, v in asdict(self.flatline).items()})
        out["any_artifact"] = self.any_artifact
        out["artifact_burden"] = self.artifact_burden
        return out


def evaluate_window(signal: np.ndarray, fs: int) -> WindowArtifactReport:
    m = motion_artifacts.detect(signal, fs)
    d = sensor_dropout.detect(signal)
    s = signal_noise.detect_noise_spikes(signal)
    f = signal_noise.detect_flatline(signal)
    any_flag = int(any(x.flag for x in (m, d, s, f)))
    burden = float(np.mean([m.severity, d.severity, s.severity, f.severity]))
    return WindowArtifactReport(m, d, s, f, any_flag, burden)


def evaluate_batch(signals: np.ndarray, fs: int) -> pd.DataFrame:
    rows = [evaluate_window(sig, fs).to_dict() for sig in signals]
    return pd.DataFrame(rows)
