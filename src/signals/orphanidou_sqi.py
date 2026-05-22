"""Template-matching signal quality, following Orphanidou et al. 2015.

Reference:
  Orphanidou, C., Bonnici, T., Charlton, P., Clifton, D., Vallance, D.,
  & Tarassenko, L. (2015). Signal-quality indices for the electrocardiogram
  and photoplethysmogram derived from optical pulse-rate measurements.
  IEEE J. Biomed. Health Inform., 19(3), 832-838.

The method has four rules that a window must satisfy to be 'acceptable':
  1. Heart-rate estimated from peaks is in [40, 180] bpm
  2. The maximum RR-interval gap is below a fixed threshold (3 s here)
  3. The maximum RR/min RR ratio is below 2.2
  4. The average correlation between each beat and the median beat template
     is above 0.66 for ECG (0.86 for PPG)

We expose:
  - `orphanidou_ecg_sqi(window, fs)` -> dict with continuous metrics and bool
  - `orphanidou_ppg_sqi(window, fs)` -> same shape, different thresholds
  - `head_to_head(windows, ground_truth, fs, modality)` -> agreement summary

The point of including this is not to compete with the in-house SQI but to
demonstrate that the in-house SQI agrees with an established published
method on the same windows. Agreement on synthetic data is necessary but
not sufficient. Anyone who runs the framework on real data should run this
side-by-side and report both.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from src.signals.ecg_processing import bandpass as ecg_bandpass, detect_r_peaks
from src.signals.ppg_processing import bandpass as ppg_bandpass, detect_pulse_peaks


ECG_TEMPLATE_CORR_THRESHOLD = 0.66
PPG_TEMPLATE_CORR_THRESHOLD = 0.86
HR_MIN_BPM = 40
HR_MAX_BPM = 180
MAX_RR_GAP_S = 3.0
MAX_RR_RATIO = 2.2


@dataclass
class OrphanidouSQI:
    acceptable: bool
    hr_bpm: float
    template_corr: float
    max_rr_gap_s: float
    max_rr_ratio: float
    n_beats: int
    rule_passed: dict[str, bool]


def _extract_beats(signal: np.ndarray, peaks: np.ndarray, fs: int,
                   half_window: float = 0.25) -> np.ndarray:
    """Cut a fixed-length window around each peak. Returns (n_beats, window_len).
    Beats too close to the signal edge are dropped."""
    hw = int(half_window * fs)
    out = []
    for p in peaks:
        if p - hw < 0 or p + hw >= len(signal):
            continue
        out.append(signal[p - hw : p + hw])
    if not out:
        return np.empty((0, 2 * hw))
    return np.array(out)


def _template_correlation(beats: np.ndarray) -> float:
    """Average Pearson correlation between each beat and the median template."""
    if beats.shape[0] < 2:
        return float("nan")
    template = np.median(beats, axis=0)
    if np.std(template) < 1e-9:
        return 0.0
    corrs = []
    for beat in beats:
        if np.std(beat) < 1e-9:
            continue
        corrs.append(float(np.corrcoef(beat, template)[0, 1]))
    return float(np.mean(corrs)) if corrs else float("nan")


def _evaluate(signal: np.ndarray, fs: int, peaks: np.ndarray,
              corr_threshold: float, modality: str) -> OrphanidouSQI:
    n_beats = len(peaks)
    if n_beats < 2:
        return OrphanidouSQI(
            acceptable=False, hr_bpm=float("nan"), template_corr=float("nan"),
            max_rr_gap_s=float("inf"), max_rr_ratio=float("inf"), n_beats=n_beats,
            rule_passed={"hr_range": False, "rr_gap": False,
                         "rr_ratio": False, "template_corr": False},
        )
    rr_samples = np.diff(peaks)
    rr_s = rr_samples / fs
    hr_bpm = 60.0 / rr_s.mean() if rr_s.mean() > 0 else float("nan")
    max_rr_gap = float(rr_s.max())
    min_rr = float(rr_s.min())
    max_rr_ratio = max_rr_gap / min_rr if min_rr > 0 else float("inf")

    beats = _extract_beats(signal, peaks, fs)
    template_corr = _template_correlation(beats)

    rule_passed = {
        "hr_range": HR_MIN_BPM <= hr_bpm <= HR_MAX_BPM,
        "rr_gap": max_rr_gap < MAX_RR_GAP_S,
        "rr_ratio": max_rr_ratio < MAX_RR_RATIO,
        "template_corr": template_corr == template_corr and template_corr > corr_threshold,
    }
    return OrphanidouSQI(
        acceptable=all(rule_passed.values()),
        hr_bpm=float(hr_bpm),
        template_corr=float(template_corr) if template_corr == template_corr else float("nan"),
        max_rr_gap_s=max_rr_gap,
        max_rr_ratio=max_rr_ratio,
        n_beats=n_beats,
        rule_passed=rule_passed,
    )


def _empty_finding(reason: str) -> "OrphanidouSQI":
    """Return an unacceptable result without running the pipeline."""
    return OrphanidouSQI(
        acceptable=False, hr_bpm=float("nan"), template_corr=float("nan"),
        max_rr_gap_s=float("inf"), max_rr_ratio=float("inf"), n_beats=0,
        rule_passed={"hr_range": False, "rr_gap": False,
                     "rr_ratio": False, "template_corr": False},
    )


def _is_processable(window: np.ndarray, fs: int) -> bool:
    """Window is long enough and has enough finite samples to filter and analyze."""
    if window is None or len(window) < max(64, 3 * fs):  # filtfilt padlen ~21, need headroom
        return False
    finite = np.isfinite(window)
    if finite.sum() < max(64, 3 * fs):
        return False
    return True


def orphanidou_ecg_sqi(window: np.ndarray, fs: int) -> OrphanidouSQI:
    """Apply Orphanidou's four ECG rules to a single window."""
    window = np.asarray(window, dtype=float)
    if not _is_processable(window, fs):
        return _empty_finding("window too short or too few finite samples")
    # Replace any leftover NaN with 0 before filtering; the finiteness check
    # above already guarantees most samples are valid.
    if not np.isfinite(window).all():
        window = np.nan_to_num(window, nan=0.0)
    filt = ecg_bandpass(window, fs)
    peaks = detect_r_peaks(filt, fs)
    return _evaluate(filt, fs, peaks, ECG_TEMPLATE_CORR_THRESHOLD, "ecg")


def orphanidou_ppg_sqi(window: np.ndarray, fs: int) -> OrphanidouSQI:
    """Apply Orphanidou's four PPG rules to a single window.

    Note: the PPG variant uses a stricter template correlation threshold
    because clean PPG pulses are more morphologically consistent than QRS
    complexes."""
    window = np.asarray(window, dtype=float)
    if not _is_processable(window, fs):
        return _empty_finding("window too short or too few finite samples")
    if not np.isfinite(window).all():
        window = np.nan_to_num(window, nan=0.0)
    filt = ppg_bandpass(window, fs)
    peaks = detect_pulse_peaks(filt, fs)
    return _evaluate(filt, fs, peaks, PPG_TEMPLATE_CORR_THRESHOLD, "ppg")


def batch_orphanidou(windows: np.ndarray, fs: int,
                     modality: Literal["ecg", "ppg"] = "ppg") -> list[OrphanidouSQI]:
    fn = orphanidou_ecg_sqi if modality == "ecg" else orphanidou_ppg_sqi
    return [fn(w, fs) for w in windows]


@dataclass
class AgreementSummary:
    n_windows: int
    in_house_mean: float
    orphanidou_acceptable_frac: float
    spearman_with_continuous: float
    point_biserial_with_binary: float
    crosstab: dict[str, int]  # quadrants of agreement


def head_to_head(windows: np.ndarray, in_house_sqi: np.ndarray, fs: int,
                 modality: Literal["ecg", "ppg"] = "ppg",
                 in_house_threshold: float = 0.7) -> AgreementSummary:
    """Compare the in-house SQI estimates against Orphanidou's rules.

    Parameters
    ----------
    windows
        (n_windows, window_len) array of signal windows.
    in_house_sqi
        (n_windows,) array of the in-house continuous SQI in [0, 1].
        If shorter than windows, both arrays are truncated to the common
        length and a warning is logged.
    fs
        Sampling rate of the windows.
    modality
        'ecg' or 'ppg'. Switches the Orphanidou template threshold.
    in_house_threshold
        Threshold for binarizing the in-house SQI when computing the
        crosstab. Default 0.7.
    """
    from scipy.stats import spearmanr, pointbiserialr
    import logging
    log = logging.getLogger("orphanidou_sqi")

    windows = np.asarray(windows)
    in_house_sqi = np.asarray(in_house_sqi, dtype=float)
    if len(in_house_sqi) != len(windows):
        n = min(len(windows), len(in_house_sqi))
        log.warning(
            "head_to_head: length mismatch (windows=%d, in_house=%d); "
            "truncating to common length %d.",
            len(windows), len(in_house_sqi), n,
        )
        windows = windows[:n]
        in_house_sqi = in_house_sqi[:n]
    if len(windows) == 0:
        return AgreementSummary(
            n_windows=0, in_house_mean=float("nan"),
            orphanidou_acceptable_frac=float("nan"),
            spearman_with_continuous=float("nan"),
            point_biserial_with_binary=float("nan"),
            crosstab={"both_pass": 0, "both_fail": 0,
                      "inhouse_pass_orph_fail": 0, "inhouse_fail_orph_pass": 0},
        )

    reports = batch_orphanidou(windows, fs, modality=modality)
    orph_accept = np.array([r.acceptable for r in reports], dtype=int)
    orph_continuous = np.array(
        [r.template_corr if r.template_corr == r.template_corr else 0.0
         for r in reports]
    )
    # Mask NaN entries in in_house_sqi consistently with the other arrays
    valid = np.isfinite(in_house_sqi)
    n_valid = int(valid.sum())
    ih_valid = in_house_sqi[valid]
    orph_accept_valid = orph_accept[valid]
    orph_cont_valid = orph_continuous[valid]
    in_house_binary_valid = (ih_valid >= in_house_threshold).astype(int)

    sp = float("nan")
    if n_valid >= 2 and np.std(ih_valid) > 1e-9 and np.std(orph_cont_valid) > 1e-9:
        rho, _ = spearmanr(ih_valid, orph_cont_valid)
        sp = float(rho) if rho == rho else float("nan")

    pb = float("nan")
    if n_valid >= 2 and 0 < orph_accept_valid.sum() < n_valid:
        r, _ = pointbiserialr(orph_accept_valid, ih_valid)
        pb = float(r) if r == r else float("nan")

    cross = {
        "both_pass": int(((in_house_binary_valid == 1) & (orph_accept_valid == 1)).sum()),
        "both_fail": int(((in_house_binary_valid == 0) & (orph_accept_valid == 0)).sum()),
        "inhouse_pass_orph_fail": int(((in_house_binary_valid == 1) & (orph_accept_valid == 0)).sum()),
        "inhouse_fail_orph_pass": int(((in_house_binary_valid == 0) & (orph_accept_valid == 1)).sum()),
    }
    return AgreementSummary(
        n_windows=len(windows),
        in_house_mean=float(np.nanmean(in_house_sqi)) if n_valid > 0 else float("nan"),
        orphanidou_acceptable_frac=float(orph_accept.mean()),
        spearman_with_continuous=sp,
        point_biserial_with_binary=pb,
        crosstab=cross,
    )
