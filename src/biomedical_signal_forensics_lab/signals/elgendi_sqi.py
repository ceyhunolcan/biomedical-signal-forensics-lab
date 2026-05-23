"""Elgendi 2016 PPG signal-quality indices.

Implements the skewness-based SQI (SSQI) from:

  Elgendi M. Optimal Signal Quality Index for Photoplethysmogram Signals.
  Bioengineering, 3(4):21, 2016. https://doi.org/10.3390/bioengineering3040021

Elgendi (2016) compared eight candidate per-window PPG SQI metrics on 106
annotated 60-second recordings labeled as 'excellent', 'acceptable', or
'unfit for diagnosis' by two independent reviewers with adjudication by a
third expert. Of the eight metrics, the skewness-based index (SSQI) had the
highest F1 score for the binary acceptable-versus-unfit decision and is
recommended as the headline metric. We expose SSQI as the primary baseline
and provide kurtosis (KSQI) and entropy (ESQI) as auxiliary metrics for
robustness checks.

The three statistics together cover a complementary set of failure modes:
  - SSQI: distribution asymmetry. A clean PPG has positive skew (long upper
    tail from systolic peaks). Saturated or flat signals lose this asymmetry.
  - KSQI: distribution tailedness. Heavy-tailed distributions indicate
    spike artifacts.
  - ESQI: amplitude entropy in moving sub-windows. Highly random amplitude
    distributions indicate broadband noise.

Elgendi's recommended thresholds were tuned on fingertip PPG; we report the
continuous statistics and let the recalibration machinery (Section 4.3)
re-tune binarization for wrist PPG. Default acceptance thresholds:
  SSQI > 0   (any positive skew)
  KSQI > 3   (super-Gaussian: heavier tail than normal)
  ESQI < 0.9 (not pure noise)

These defaults are intentionally lenient; users should recalibrate against
either expert labels or a reference SQI on their own data.

Each function operates on a single window (typically 5-30 seconds at 64 Hz
for wrist PPG or 125 Hz for fingertip PPG) and returns an ElgendiSQI
dataclass with the continuous statistics, the per-statistic acceptance
flags, and the overall binary acceptance verdict.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as sst

from .ppg_processing import bandpass as ppg_bandpass


# Elgendi 2016 default thresholds (lenient; intended for recalibration)
SSQI_MIN = 0.0   # accept any positive skew
KSQI_MIN = 3.0   # super-Gaussian
ESQI_MAX = 0.90  # accept windows with at least some structure


@dataclass
class ElgendiSQI:
    """Per-window Elgendi 2016 SQI report.

    Attributes:
        acceptable: overall pass (SSQI > SSQI_MIN AND KSQI > KSQI_MIN AND
            ESQI < ESQI_MAX). All three must pass for the window to be
            accepted under the default policy. Single-statistic users can
            inspect ssqi_ok, ksqi_ok, esqi_ok individually.
        skewness: third standardized moment of the window after bandpass.
            Clean PPG has positive skew; SSQI is its raw value.
        kurtosis: fourth standardized moment (Fisher convention, so
            normal-distribution kurtosis = 0). KSQI is `kurtosis + 3` in the
            Pearson convention used in Elgendi 2016.
        entropy: normalized Shannon entropy of the amplitude distribution
            computed over a 16-bin histogram, scaled to [0, 1].
        ssqi_ok, ksqi_ok, esqi_ok: per-statistic acceptance flags.
        n_samples: number of samples in the window after bandpass.
    """
    acceptable: bool
    skewness: float
    kurtosis: float
    entropy: float
    ssqi_ok: bool
    ksqi_ok: bool
    esqi_ok: bool
    n_samples: int


def _amplitude_entropy(x: np.ndarray, n_bins: int = 16) -> float:
    """Normalized Shannon entropy of the amplitude distribution.

    Returns a value in [0, 1] where 1 corresponds to a uniform distribution
    across n_bins (maximum entropy, indicating broadband noise) and 0
    corresponds to all samples in a single bin (degenerate). Real PPG falls
    in the 0.4-0.85 range; pure noise is closer to 1.0.
    """
    if len(x) < 4:
        return float("nan")
    finite = x[np.isfinite(x)]
    if len(finite) < 4 or np.ptp(finite) < 1e-12:
        return float("nan")
    counts, _ = np.histogram(finite, bins=n_bins)
    p = counts.astype(float) / counts.sum()
    p_pos = p[p > 0]
    h = -float(np.sum(p_pos * np.log2(p_pos)))
    h_max = np.log2(n_bins)
    return h / h_max if h_max > 0 else float("nan")


def elgendi_window(window: np.ndarray,
                   fs: int,
                   ssqi_min: float = SSQI_MIN,
                   ksqi_min: float = KSQI_MIN,
                   esqi_max: float = ESQI_MAX,
                   apply_bandpass: bool = True,
                   invert: bool = False,
                   ) -> ElgendiSQI:
    """Compute Elgendi 2016 SSQI / KSQI / ESQI on a single PPG window.

    Args:
        window: 1D PPG signal samples.
        fs: sampling rate in Hz.
        ssqi_min: SSQI acceptance threshold. See module constants.
        ksqi_min: KSQI acceptance threshold. See module constants.
        esqi_max: ESQI acceptance threshold. See module constants.
            docstring for defaults and recommended recalibration policy.
        apply_bandpass: if True, run the standard PPG bandpass filter
            (0.5-8 Hz, 4th-order Butterworth) before computing statistics.
        invert: if True, multiply the signal by -1 before computing
            statistics. Some devices (Empatica E4 wrist PPG in particular) report
            PPG inverted relative to fingertip conventions, which flips the
            sign of skewness. Use `batch_elgendi(..., auto_invert=True)` to
            auto-detect from the cohort.

    Returns:
        ElgendiSQI dataclass with the continuous statistics and acceptance
        flags. All NaN/empty edge cases return acceptable=False with
        statistics set to NaN.
    """
    x = np.asarray(window, dtype=float)
    if len(x) == 0:
        return ElgendiSQI(False, float("nan"), float("nan"), float("nan"),
                           False, False, False, 0)
    finite = x[np.isfinite(x)]
    if len(finite) < 8 or np.ptp(finite) < 1e-12:
        return ElgendiSQI(False, float("nan"), float("nan"), float("nan"),
                           False, False, False, len(finite))

    if apply_bandpass:
        try:
            x = ppg_bandpass(finite, fs)
        except (ValueError, RuntimeError):
            return ElgendiSQI(False, float("nan"), float("nan"), float("nan"),
                               False, False, False, len(finite))
    else:
        x = finite

    if invert:
        x = -x

    # Skewness: Fisher-corrected (sample skewness)
    try:
        skew = float(sst.skew(x, bias=False))
    except (ValueError, FloatingPointError):
        skew = float("nan")

    # Kurtosis: Fisher convention (normal = 0). Elgendi 2016 uses Pearson
    # convention (normal = 3), so we add 3 for direct comparison to the
    # published KSQI > 3 threshold.
    try:
        kurt = float(sst.kurtosis(x, fisher=True, bias=False)) + 3.0
    except (ValueError, FloatingPointError):
        kurt = float("nan")

    ent = _amplitude_entropy(x)

    ssqi_ok = bool(np.isfinite(skew) and skew > ssqi_min)
    ksqi_ok = bool(np.isfinite(kurt) and kurt > ksqi_min)
    esqi_ok = bool(np.isfinite(ent) and ent < esqi_max)
    acceptable = ssqi_ok and ksqi_ok and esqi_ok

    return ElgendiSQI(
        acceptable=acceptable,
        skewness=skew,
        kurtosis=kurt,
        entropy=ent,
        ssqi_ok=ssqi_ok,
        ksqi_ok=ksqi_ok,
        esqi_ok=esqi_ok,
        n_samples=int(len(x)),
    )


def batch_elgendi(windows: np.ndarray,
                  fs: int,
                  ssqi_min: float = SSQI_MIN,
                  ksqi_min: float = KSQI_MIN,
                  esqi_max: float = ESQI_MAX,
                  auto_invert: bool = True,
                  pilot_size: int = 100,
                  ) -> pd.DataFrame:
    """Compute Elgendi SQI on a batch of windows.

    Args:
        windows: 2D array of shape (n_windows, n_samples) or a list of 1D
            arrays. Variable-length windows are accepted by passing a list.
        fs: sampling rate in Hz.
        auto_invert: if True (default), compute Elgendi statistics on the
            first `pilot_size` windows, and if the median skewness across
            that pilot is negative, invert the entire batch before
            computing the full result. This handles devices that report PPG
            with reversed polarity (e.g., Empatica E4 wrist PPG). Set to
            False to disable polarity detection.
        pilot_size: number of windows used for polarity detection.

    Returns:
        DataFrame with one row per window containing all ElgendiSQI fields
        plus a `polarity_inverted` boolean column (True if auto_invert
        decided to invert).
    """
    if isinstance(windows, np.ndarray) and windows.ndim == 2:
        iterator = windows
    else:
        iterator = list(windows)

    polarity_inverted = False
    if auto_invert and len(iterator) > 0:
        pilot = []
        for i, w in enumerate(iterator):
            if i >= pilot_size:
                break
            r = elgendi_window(w, fs, ssqi_min=ssqi_min,
                               ksqi_min=ksqi_min, esqi_max=esqi_max,
                               invert=False)
            if np.isfinite(r.skewness):
                pilot.append(r.skewness)
        if len(pilot) >= 10:
            median_skew = float(np.median(pilot))
            polarity_inverted = median_skew < 0.0

    rows = []
    for w in iterator:
        r = elgendi_window(w, fs, ssqi_min=ssqi_min,
                           ksqi_min=ksqi_min, esqi_max=esqi_max,
                           invert=polarity_inverted)
        rows.append({
            "elgendi_acceptable": r.acceptable,
            "elgendi_skewness": r.skewness,
            "elgendi_kurtosis": r.kurtosis,
            "elgendi_entropy": r.entropy,
            "elgendi_ssqi_ok": r.ssqi_ok,
            "elgendi_ksqi_ok": r.ksqi_ok,
            "elgendi_esqi_ok": r.esqi_ok,
            "elgendi_n_samples": r.n_samples,
            "elgendi_polarity_inverted": polarity_inverted,
        })
    return pd.DataFrame(rows)


def four_way_sqi_agreement(in_house_pass: np.ndarray,
                           orphanidou_pass: np.ndarray,
                           sukor_pass: np.ndarray,
                           elgendi_pass: np.ndarray,
                           ) -> dict:
    """Compute pairwise Cohen's kappa and Spearman rho for all four SQIs.

    The 'all three published baselines agree against in-house' argument
    becomes stronger when there are three baselines instead of two; the
    headline statistic is the median pairwise kappa between Orphanidou,
    Sukor, and Elgendi.

    Returns:
        Dict with pairwise kappas, fraction of windows accepted by all
        published baselines, fraction accepted by in-house but not by any
        published baseline (the most damning category for the in-house SQI),
        and the median pairwise published-vs-published kappa.
    """
    from sklearn.metrics import cohen_kappa_score

    in_h = np.asarray(in_house_pass).astype(int)
    orph = np.asarray(orphanidou_pass).astype(int)
    suk = np.asarray(sukor_pass).astype(int)
    elg = np.asarray(elgendi_pass).astype(int)
    n = min(len(in_h), len(orph), len(suk), len(elg))
    if n < 5:
        return {"n_windows": int(n), "note": "insufficient windows for agreement"}
    in_h, orph, suk, elg = in_h[:n], orph[:n], suk[:n], elg[:n]

    def safe_kappa(a, b):
        if len(np.unique(a)) < 2 or len(np.unique(b)) < 2:
            return 0.0
        return float(cohen_kappa_score(a, b))

    pairwise = {
        "kappa_inhouse_vs_orph": safe_kappa(in_h, orph),
        "kappa_inhouse_vs_sukor": safe_kappa(in_h, suk),
        "kappa_inhouse_vs_elgendi": safe_kappa(in_h, elg),
        "kappa_orph_vs_sukor": safe_kappa(orph, suk),
        "kappa_orph_vs_elgendi": safe_kappa(orph, elg),
        "kappa_sukor_vs_elgendi": safe_kappa(suk, elg),
    }
    published_pairs = [
        pairwise["kappa_orph_vs_sukor"],
        pairwise["kappa_orph_vs_elgendi"],
        pairwise["kappa_sukor_vs_elgendi"],
    ]
    inhouse_pairs = [
        pairwise["kappa_inhouse_vs_orph"],
        pairwise["kappa_inhouse_vs_sukor"],
        pairwise["kappa_inhouse_vs_elgendi"],
    ]
    return {
        "n_windows": int(n),
        **pairwise,
        "median_kappa_published_only": float(np.median(published_pairs)),
        "median_kappa_inhouse_vs_published": float(np.median(inhouse_pairs)),
        "all_three_published_pass_rate": float(
            ((orph == 1) & (suk == 1) & (elg == 1)).mean()),
        "all_three_published_fail_rate": float(
            ((orph == 0) & (suk == 0) & (elg == 0)).mean()),
        "inhouse_passes_when_all_published_fail": float(
            (((orph == 0) & (suk == 0) & (elg == 0)) & (in_h == 1)).mean()),
    }
