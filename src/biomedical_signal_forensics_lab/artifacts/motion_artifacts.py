"""Motion artifact detection on PPG/ECG-like windows."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class ArtifactFinding:
    flag: int
    severity: float
    explanation: str


def detect(signal: np.ndarray, fs: int,
           amplitude_var_threshold: float = 0.5,
           hf_power_threshold: float = 0.4) -> ArtifactFinding:
    """Flag motion artifacts via amplitude variance and high-frequency power.

    Two heuristics combined:
      1. Range-normalized variance above `amplitude_var_threshold`.
         Range normalization (variance divided by 95th-percentile absolute
         value squared) makes the metric dimensionless so the threshold is
         comparable across signals on different amplitude scales (mV ECG,
         normalized PPG, etc.).
      2. Power above 4 Hz as a fraction of total power, above
         `hf_power_threshold`. Already dimensionless.

    Severity is the average of the two overshoot ratios, clipped to [0, 1].
    Flag is 1 when at least one rule fires. Severity and flag are guaranteed
    consistent: severity > 0 iff flag == 1 iff at least one threshold crossed.
    """
    if signal.size < fs:
        return ArtifactFinding(0, 0.0, "Window too short to evaluate motion.")
    sig = np.asarray(signal, dtype=float)
    sig = sig[np.isfinite(sig)]
    if sig.size < fs:
        return ArtifactFinding(0, 0.0, "Too few finite samples to evaluate motion.")
    sig = sig - np.mean(sig)
    # Range-normalize: makes the threshold dimensionless
    scale = float(np.percentile(np.abs(sig), 95)) + 1e-9
    amp_var = float(np.var(sig)) / (scale * scale)

    fft = np.fft.rfft(sig)
    freqs = np.fft.rfftfreq(len(sig), 1.0 / fs)
    power = np.abs(fft) ** 2
    total = power.sum() + 1e-9
    hf_ratio = float(power[freqs > 4.0].sum() / total)

    # Per-rule overshoot ratios (0 if under threshold; >0 if over)
    amp_overshoot = max(0.0, amp_var - amplitude_var_threshold) / max(amplitude_var_threshold, 1e-6)
    hf_overshoot = max(0.0, hf_ratio - hf_power_threshold) / max(hf_power_threshold, 1e-6)

    # Severity blends a "rule fired at all" floor with the continuous overshoot.
    rules_fired = int(amp_overshoot > 0) + int(hf_overshoot > 0)
    if rules_fired == 0:
        severity = 0.0
    else:
        # Floor of 0.5 per rule fired, plus a continuous lift from the overshoot
        # so a barely-crossed threshold doesn't read as full severity.
        floor = 0.5 * rules_fired
        lift = 0.25 * (amp_overshoot + hf_overshoot)
        severity = float(np.clip(floor + lift, 0.0, 1.0))

    flag = int(severity > 0)
    explanation = (
        f"amp_var={amp_var:.3f} (thr={amplitude_var_threshold}, range-normalized), "
        f"hf_power_ratio={hf_ratio:.3f} (thr={hf_power_threshold})"
    )
    return ArtifactFinding(flag, severity, explanation)
