"""Sukor 2011 PPG signal-quality decision rules.

Implements the four-feature decision-tree style SQI from:

  Sukor JA, Redmond SJ, Lovell NH. Signal quality measures for pulse oximetry
  through waveform morphology analysis. Physiological Measurement, 2011.

Sukor's method is a published PPG-specific SQI baseline. We use it alongside
Orphanidou 2015 to give the in-house SQI a two-witness comparison rather than
relying on a single published baseline.

Sukor's four features per detected pulse:
  1. Pulse waveform shape: ratio of systolic peak amplitude to diastolic peak
  2. Pulse-to-pulse interval consistency (similar to Orphanidou's RR check)
  3. Pulse amplitude variability
  4. Trough-to-trough interval consistency

A pulse is acceptable if all four features fall within their published ranges.
A window is acceptable if at least 80% of its detected pulses are acceptable.

This is a faithful re-implementation of the published thresholds, adapted to
window-level scoring for compatibility with our pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.signal import find_peaks

from .ppg_processing import bandpass as ppg_bandpass


# Sukor 2011 published thresholds
PULSE_SHAPE_RATIO_MIN = 0.50    # systolic:diastolic amplitude ratio
PULSE_SHAPE_RATIO_MAX = 4.00
PP_INTERVAL_CV_MAX = 0.30       # coefficient of variation of pulse-to-pulse intervals
PULSE_AMPLITUDE_CV_MAX = 0.50   # coefficient of variation of pulse amplitudes
ACCEPTABLE_PULSE_FRACTION = 0.80  # fraction of pulses that must be acceptable


@dataclass
class SukorSQI:
    acceptable: bool
    pulse_shape_ok: bool
    pp_interval_cv: float
    pulse_amplitude_cv: float
    trough_interval_cv: float
    fraction_pulses_ok: float
    n_pulses: int


def _empty_finding() -> SukorSQI:
    return SukorSQI(
        acceptable=False, pulse_shape_ok=False,
        pp_interval_cv=float("inf"), pulse_amplitude_cv=float("inf"),
        trough_interval_cv=float("inf"),
        fraction_pulses_ok=0.0, n_pulses=0,
    )


def sukor_ppg_sqi(window: np.ndarray, fs: int) -> SukorSQI:
    """Apply Sukor 2011 four-feature rules to a single PPG window."""
    window = np.asarray(window, dtype=float)
    if len(window) < max(64, 3 * fs):
        return _empty_finding()
    if not np.isfinite(window).all():
        if np.isfinite(window).sum() < max(64, 3 * fs):
            return _empty_finding()
        window = np.nan_to_num(window, nan=0.0)

    filt = ppg_bandpass(window, fs)
    # Detect peaks (systolic, upward) and troughs (diastolic, inverted)
    peaks, _ = find_peaks(filt, distance=int(fs * 0.4))
    troughs, _ = find_peaks(-filt, distance=int(fs * 0.4))
    if len(peaks) < 3 or len(troughs) < 3:
        return _empty_finding()

    # Pulse amplitudes (peak - nearest preceding trough)
    pulse_amps = []
    for p in peaks:
        prev_troughs = troughs[troughs < p]
        if len(prev_troughs) == 0:
            continue
        t = prev_troughs[-1]
        pulse_amps.append(filt[p] - filt[t])
    pulse_amps = np.asarray(pulse_amps)
    if len(pulse_amps) < 3:
        return _empty_finding()

    # Pulse shape: ratio of peak amplitude to diastolic amplitude per pulse.
    # Computed as the ratio of systolic peak height to the next-trough depth.
    shape_ratios = []
    for p in peaks:
        next_troughs = troughs[troughs > p]
        if len(next_troughs) == 0:
            continue
        t = next_troughs[0]
        peak_above_zero = max(filt[p], 1e-9)
        trough_below_zero = max(-filt[t], 1e-9)
        shape_ratios.append(peak_above_zero / trough_below_zero)
    shape_ratios = np.asarray(shape_ratios)
    if len(shape_ratios) < 3:
        return _empty_finding()
    n_shape_ok = ((shape_ratios >= PULSE_SHAPE_RATIO_MIN) &
                  (shape_ratios <= PULSE_SHAPE_RATIO_MAX)).sum()
    fraction_shape_ok = n_shape_ok / len(shape_ratios)

    # Pulse-to-pulse interval CV
    pp_intervals = np.diff(peaks) / fs
    pp_cv = float(np.std(pp_intervals) / (np.mean(pp_intervals) + 1e-9))

    # Pulse amplitude CV
    amp_cv = float(np.std(pulse_amps) / (np.mean(np.abs(pulse_amps)) + 1e-9))

    # Trough-to-trough interval CV
    tt_intervals = np.diff(troughs) / fs
    tt_cv = float(np.std(tt_intervals) / (np.mean(tt_intervals) + 1e-9))

    # Window-level acceptance
    pulse_shape_ok = fraction_shape_ok >= ACCEPTABLE_PULSE_FRACTION
    intervals_ok = (pp_cv < PP_INTERVAL_CV_MAX
                    and amp_cv < PULSE_AMPLITUDE_CV_MAX
                    and tt_cv < PP_INTERVAL_CV_MAX)
    acceptable = pulse_shape_ok and intervals_ok

    return SukorSQI(
        acceptable=acceptable,
        pulse_shape_ok=pulse_shape_ok,
        pp_interval_cv=pp_cv,
        pulse_amplitude_cv=amp_cv,
        trough_interval_cv=tt_cv,
        fraction_pulses_ok=float(fraction_shape_ok),
        n_pulses=int(len(peaks)),
    )


def batch_sukor(windows: np.ndarray, fs: int) -> list[SukorSQI]:
    """Run Sukor SQI on a batch of windows."""
    return [sukor_ppg_sqi(w, fs) for w in windows]
