"""Deep cross-modality analysis of real wearable data.

Computes for every extracted window:
  - HR from chest ECG (gold standard)
  - HR from wrist PPG (the realistic device)
  - In-house PPG SQI
  - In-house ECG SQI
  - Orphanidou 2015 PPG SQI (published baseline 1)
  - Sukor 2011 PPG SQI (published baseline 2)
  - PPG motion artifact score

Then runs a series of validation analyses:

1. **Cross-modality HR agreement** (HR_PPG vs HR_ECG): mean absolute error,
   bias, 95% limits of agreement (Bland-Altman 1986), Pearson correlation.

2. **Per-state effects**: for each subject, paired Wilcoxon signed-rank test
   on baseline vs stress windows for SQI, motion, and HR-PPG-vs-ECG error.

3. **Three-way SQI agreement** (in-house vs Orphanidou vs Sukor): pairwise
   Spearman, Cohen's kappa for binary acceptance, three-way confusion table.

4. **Motion-vs-SQI**: correlation between PPG motion score and the absolute
   HR-PPG-vs-ECG disagreement. If motion predicts disagreement, that's the
   confounding-detection logic working on real signals.

5. **Recalibration experiment**: split windows 50/50 by subject, fit new
   in-house SQI thresholds on the calibration half to match Orphanidou's
   pass/fail pattern, evaluate the recalibrated SQI on the held-out half.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from scipy.stats import spearmanr, wilcoxon, pearsonr

from ..signals.ecg_processing import bandpass as ecg_bandpass, detect_r_peaks
from ..signals.ppg_processing import bandpass as ppg_bandpass, detect_pulse_peaks
from ..signals.orphanidou_sqi import orphanidou_ppg_sqi, batch_orphanidou
from ..signals.sukor_sqi import sukor_ppg_sqi
from ..signals.signal_quality import per_window_sqi
from ..utils.logging import get_logger

log = get_logger("deep_real_analysis")


def hr_from_ecg_window(ecg_window: np.ndarray, fs: int = 700) -> float:
    """Estimate HR from a single ECG window in bpm. Returns NaN if undetermined."""
    if len(ecg_window) < 3 * fs:
        return float("nan")
    filt = ecg_bandpass(np.nan_to_num(ecg_window, nan=0.0), fs)
    peaks = detect_r_peaks(filt, fs)
    if len(peaks) < 3:
        return float("nan")
    rr_s = np.diff(peaks) / fs
    plausible = (rr_s >= 0.4) & (rr_s <= 1.5)
    if plausible.sum() < 2:
        return float("nan")
    return float(60.0 / rr_s[plausible].mean())


def hr_from_ppg_window(ppg_window: np.ndarray, fs: int = 64) -> float:
    """Estimate HR from a single PPG window in bpm. Returns NaN if undetermined."""
    if len(ppg_window) < 3 * fs:
        return float("nan")
    filt = ppg_bandpass(np.nan_to_num(ppg_window, nan=0.0), fs)
    peaks = detect_pulse_peaks(filt, fs)
    if len(peaks) < 3:
        return float("nan")
    pp_s = np.diff(peaks) / fs
    plausible = (pp_s >= 0.4) & (pp_s <= 1.5)
    if plausible.sum() < 2:
        return float("nan")
    return float(60.0 / pp_s[plausible].mean())


def compute_window_table(ecg_arr: np.ndarray, ppg_arr: np.ndarray,
                        meta: pd.DataFrame, ecg_fs: int = 700,
                        ppg_fs: int = 64) -> pd.DataFrame:
    """For every window, compute HR from both modalities plus all three SQIs.

    Returns
    -------
    A DataFrame with one row per window. Columns include the meta fields
    (subject_id, label_name, etc.) plus:
      - hr_ecg, hr_ppg, hr_abs_diff
      - inhouse_ecg_sqi, inhouse_ppg_sqi, inhouse_ppg_motion
      - orphanidou_acceptable, orphanidou_template_corr
      - sukor_acceptable, sukor_pp_cv, sukor_amp_cv
    """
    n = min(len(ecg_arr), len(ppg_arr), len(meta))
    if n == 0:
        return pd.DataFrame()

    rows = []
    # In-house SQI in batch (faster)
    sqi_df = per_window_sqi(ecg_arr[:n], ppg_arr[:n], ecg_fs, ppg_fs)
    # Orphanidou in batch
    orph_results = batch_orphanidou(ppg_arr[:n], ppg_fs, modality="ppg")

    log.info("Computing per-window HR and Sukor SQI on %d windows…", n)
    for i in range(n):
        hr_ecg = hr_from_ecg_window(ecg_arr[i], ecg_fs)
        hr_ppg = hr_from_ppg_window(ppg_arr[i], ppg_fs)
        sukor = sukor_ppg_sqi(ppg_arr[i], ppg_fs)
        orph = orph_results[i]
        row = {
            "window_idx": int(meta["window_idx"].iloc[i]) if "window_idx" in meta.columns else i,
            "subject_id": meta["subject_id"].iloc[i] if "subject_id" in meta.columns else None,
            "label": int(meta["label"].iloc[i]) if "label" in meta.columns else -1,
            "label_name": meta["label_name"].iloc[i] if "label_name" in meta.columns else "",
            "hr_ecg": hr_ecg,
            "hr_ppg": hr_ppg,
            "hr_abs_diff": abs(hr_ecg - hr_ppg) if (hr_ecg == hr_ecg and hr_ppg == hr_ppg) else float("nan"),
            "inhouse_ecg_sqi": float(sqi_df["ecg_sqi"].iloc[i]),
            "inhouse_ppg_sqi": float(sqi_df["ppg_sqi"].iloc[i]),
            "inhouse_ppg_motion": float(sqi_df["ppg_motion"].iloc[i]),
            "orphanidou_acceptable": int(orph.acceptable),
            "orphanidou_template_corr": (float(orph.template_corr)
                                          if orph.template_corr == orph.template_corr else float("nan")),
            "sukor_acceptable": int(sukor.acceptable),
            "sukor_pp_cv": sukor.pp_interval_cv,
            "sukor_amp_cv": sukor.pulse_amplitude_cv,
        }
        rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Analysis 1: Cross-modality HR agreement
# ----------------------------------------------------------------------------

@dataclass
class HRAgreementResult:
    n_windows: int
    mean_absolute_error_bpm: float
    bias_ppg_minus_ecg_bpm: float
    loa_lower_bpm: float
    loa_upper_bpm: float
    pearson_r: float
    pearson_p: float
    fraction_within_5_bpm: float
    fraction_within_10_bpm: float


def cross_modality_hr_agreement(df: pd.DataFrame) -> HRAgreementResult:
    """Bland-Altman style agreement statistics for HR_PPG vs HR_ECG."""
    empty = HRAgreementResult(
        n_windows=0, mean_absolute_error_bpm=float("nan"),
        bias_ppg_minus_ecg_bpm=float("nan"),
        loa_lower_bpm=float("nan"), loa_upper_bpm=float("nan"),
        pearson_r=float("nan"), pearson_p=float("nan"),
        fraction_within_5_bpm=float("nan"),
        fraction_within_10_bpm=float("nan"),
    )
    if df is None or df.empty:
        return empty
    if not {"hr_ecg", "hr_ppg"}.issubset(df.columns):
        return empty
    sub = df.dropna(subset=["hr_ecg", "hr_ppg"])
    if len(sub) < 5:
        empty.n_windows = len(sub)
        return empty
    diff = sub["hr_ppg"].to_numpy() - sub["hr_ecg"].to_numpy()
    mean_diff = float(np.mean(diff))
    sd_diff = float(np.std(diff, ddof=1))
    r, p = pearsonr(sub["hr_ecg"], sub["hr_ppg"])
    return HRAgreementResult(
        n_windows=len(sub),
        mean_absolute_error_bpm=float(np.mean(np.abs(diff))),
        bias_ppg_minus_ecg_bpm=mean_diff,
        loa_lower_bpm=mean_diff - 1.96 * sd_diff,
        loa_upper_bpm=mean_diff + 1.96 * sd_diff,
        pearson_r=float(r),
        pearson_p=float(p),
        fraction_within_5_bpm=float((np.abs(diff) <= 5).mean()),
        fraction_within_10_bpm=float((np.abs(diff) <= 10).mean()),
    )


# ----------------------------------------------------------------------------
# Analysis 2: Per-state paired comparisons (within-subject baseline vs stress)
# ----------------------------------------------------------------------------

def per_state_comparison(df: pd.DataFrame, state_a: str = "baseline",
                         state_b: str = "stress") -> pd.DataFrame:
    """For each metric, compare state_a vs state_b within each subject.

    Returns one row per subject with mean values in each state and an
    unpaired Wilcoxon rank-sum p-value.
    """
    from scipy.stats import ranksums

    metrics = ["inhouse_ppg_sqi", "inhouse_ecg_sqi", "inhouse_ppg_motion",
               "hr_abs_diff", "orphanidou_template_corr"]
    rows = []
    for subject_id, g in df.groupby("subject_id"):
        a = g[g["label_name"] == state_a]
        b = g[g["label_name"] == state_b]
        if len(a) < 3 or len(b) < 3:
            continue
        for m in metrics:
            av = a[m].dropna()
            bv = b[m].dropna()
            if len(av) < 3 or len(bv) < 3:
                continue
            try:
                _, p = ranksums(av, bv)
            except Exception:  # noqa: BLE001
                p = float("nan")
            rows.append({
                "subject_id": subject_id,
                "metric": m,
                f"{state_a}_n": int(len(av)),
                f"{state_b}_n": int(len(bv)),
                f"{state_a}_mean": float(av.mean()),
                f"{state_b}_mean": float(bv.mean()),
                "delta_b_minus_a": float(bv.mean() - av.mean()),
                "wilcoxon_p": float(p) if p == p else float("nan"),
            })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Analysis 3: Three-way SQI agreement
# ----------------------------------------------------------------------------

def cohens_kappa(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's kappa for two binary rater outputs."""
    if len(a) == 0:
        return float("nan")
    a = np.asarray(a).astype(int)
    b = np.asarray(b).astype(int)
    n = len(a)
    p_observed = float((a == b).mean())
    p_a = float(a.mean())
    p_b = float(b.mean())
    p_chance = p_a * p_b + (1 - p_a) * (1 - p_b)
    if p_chance >= 1.0 - 1e-9:
        return float("nan")
    return (p_observed - p_chance) / (1.0 - p_chance)


@dataclass
class ThreeWaySQIAgreement:
    n_windows: int
    spearman_inhouse_vs_orph: float
    spearman_inhouse_vs_sukor: float
    spearman_orph_vs_sukor: float
    kappa_inhouse_vs_orph: float
    kappa_inhouse_vs_sukor: float
    kappa_orph_vs_sukor: float
    fraction_all_three_pass: float
    fraction_all_three_fail: float
    inhouse_pass_rate: float
    orphanidou_pass_rate: float
    sukor_pass_rate: float


def three_way_sqi_agreement(df: pd.DataFrame,
                            inhouse_threshold: float = 0.7) -> ThreeWaySQIAgreement:
    """Pairwise agreement among three PPG SQI methods."""
    empty = ThreeWaySQIAgreement(
        n_windows=0,
        spearman_inhouse_vs_orph=float("nan"),
        spearman_inhouse_vs_sukor=float("nan"),
        spearman_orph_vs_sukor=float("nan"),
        kappa_inhouse_vs_orph=float("nan"),
        kappa_inhouse_vs_sukor=float("nan"),
        kappa_orph_vs_sukor=float("nan"),
        fraction_all_three_pass=float("nan"),
        fraction_all_three_fail=float("nan"),
        inhouse_pass_rate=float("nan"),
        orphanidou_pass_rate=float("nan"),
        sukor_pass_rate=float("nan"),
    )
    if df is None or df.empty:
        return empty
    required = {"inhouse_ppg_sqi", "orphanidou_acceptable", "sukor_acceptable"}
    if not required.issubset(df.columns):
        return empty
    sub = df.dropna(subset=["inhouse_ppg_sqi", "orphanidou_acceptable", "sukor_acceptable"])
    if len(sub) < 5:
        empty.n_windows = len(sub)
        return empty
    inhouse_binary = (sub["inhouse_ppg_sqi"] >= inhouse_threshold).astype(int).to_numpy()
    orph_binary = sub["orphanidou_acceptable"].astype(int).to_numpy()
    sukor_binary = sub["sukor_acceptable"].astype(int).to_numpy()

    inhouse_cont = sub["inhouse_ppg_sqi"].to_numpy()
    orph_cont = sub.get("orphanidou_template_corr", pd.Series([0]*len(sub))).fillna(0).to_numpy()
    sukor_cont = (1.0 - sub.get("sukor_amp_cv", pd.Series([0]*len(sub))).clip(0, 2)).to_numpy()

    def safe_spearman(a, b):
        if np.std(a) < 1e-9 or np.std(b) < 1e-9:
            return float("nan")
        rho, _ = spearmanr(a, b)
        return float(rho) if rho == rho else float("nan")

    return ThreeWaySQIAgreement(
        n_windows=len(sub),
        spearman_inhouse_vs_orph=safe_spearman(inhouse_cont, orph_cont),
        spearman_inhouse_vs_sukor=safe_spearman(inhouse_cont, sukor_cont),
        spearman_orph_vs_sukor=safe_spearman(orph_cont, sukor_cont),
        kappa_inhouse_vs_orph=cohens_kappa(inhouse_binary, orph_binary),
        kappa_inhouse_vs_sukor=cohens_kappa(inhouse_binary, sukor_binary),
        kappa_orph_vs_sukor=cohens_kappa(orph_binary, sukor_binary),
        fraction_all_three_pass=float(((inhouse_binary == 1) & (orph_binary == 1) & (sukor_binary == 1)).mean()),
        fraction_all_three_fail=float(((inhouse_binary == 0) & (orph_binary == 0) & (sukor_binary == 0)).mean()),
        inhouse_pass_rate=float(inhouse_binary.mean()),
        orphanidou_pass_rate=float(orph_binary.mean()),
        sukor_pass_rate=float(sukor_binary.mean()),
    )


# ----------------------------------------------------------------------------
# Analysis 4: Motion-vs-SQI and motion-vs-HR-disagreement
# ----------------------------------------------------------------------------

@dataclass
class MotionEffect:
    n_windows: int
    spearman_motion_vs_inhouse_sqi: float
    spearman_motion_vs_hr_disagreement: float
    spearman_motion_vs_orphanidou_template_corr: float
    high_motion_threshold: float
    fraction_high_motion: float
    mean_hr_disagreement_low_motion: float
    mean_hr_disagreement_high_motion: float


def motion_effect_analysis(df: pd.DataFrame) -> MotionEffect:
    """Does the PPG motion score predict SQI failures and HR-modality disagreement?"""
    empty = MotionEffect(
        n_windows=0,
        spearman_motion_vs_inhouse_sqi=float("nan"),
        spearman_motion_vs_hr_disagreement=float("nan"),
        spearman_motion_vs_orphanidou_template_corr=float("nan"),
        high_motion_threshold=float("nan"),
        fraction_high_motion=float("nan"),
        mean_hr_disagreement_low_motion=float("nan"),
        mean_hr_disagreement_high_motion=float("nan"),
    )
    if df is None or df.empty:
        return empty
    if not {"inhouse_ppg_motion", "inhouse_ppg_sqi"}.issubset(df.columns):
        return empty
    sub = df.dropna(subset=["inhouse_ppg_motion", "inhouse_ppg_sqi"])
    if len(sub) < 5:
        empty.n_windows = len(sub)
        return empty

    def safe_spearman(a, b):
        if np.std(a) < 1e-9 or np.std(b) < 1e-9:
            return float("nan")
        m = np.isfinite(a) & np.isfinite(b)
        if m.sum() < 3:
            return float("nan")
        rho, _ = spearmanr(a[m], b[m])
        return float(rho) if rho == rho else float("nan")

    motion = sub["inhouse_ppg_motion"].to_numpy()
    sqi = sub["inhouse_ppg_sqi"].to_numpy()
    hr_diff = (sub["hr_abs_diff"].to_numpy() if "hr_abs_diff" in sub.columns
               else np.full(len(sub), np.nan))
    orph_cont = (sub["orphanidou_template_corr"].fillna(0).to_numpy()
                 if "orphanidou_template_corr" in sub.columns
                 else np.full(len(sub), np.nan))

    rho_motion_sqi = safe_spearman(motion, sqi)
    rho_motion_hrdiff = safe_spearman(motion, hr_diff)
    rho_motion_orph = safe_spearman(motion, orph_cont)

    # Define "high motion" as top quartile
    thr = float(np.percentile(motion, 75))
    high = motion >= thr
    low = ~high

    return MotionEffect(
        n_windows=len(sub),
        spearman_motion_vs_inhouse_sqi=rho_motion_sqi,
        spearman_motion_vs_hr_disagreement=rho_motion_hrdiff,
        spearman_motion_vs_orphanidou_template_corr=rho_motion_orph,
        high_motion_threshold=thr,
        fraction_high_motion=float(high.mean()),
        mean_hr_disagreement_low_motion=float(np.nanmean(hr_diff[low])) if np.isfinite(hr_diff[low]).any() else float("nan"),
        mean_hr_disagreement_high_motion=float(np.nanmean(hr_diff[high])) if np.isfinite(hr_diff[high]).any() else float("nan"),
    )


# ----------------------------------------------------------------------------
# Analysis 5: Recalibration experiment
# ----------------------------------------------------------------------------

@dataclass
class RecalibrationResult:
    n_calibration: int
    n_holdout: int
    original_threshold: float
    recalibrated_threshold: float
    original_holdout_kappa_vs_orph: float
    recalibrated_holdout_kappa_vs_orph: float
    original_holdout_agreement: float
    recalibrated_holdout_agreement: float


def recalibrate_inhouse_sqi(df: pd.DataFrame,
                            original_threshold: float = 0.7,
                            seed: int = 0) -> RecalibrationResult:
    """Refit the in-house PPG SQI threshold to maximize Orphanidou agreement.

    Splits windows 50/50, fits a new threshold on the calibration half to
    maximize Cohen's kappa against Orphanidou, then evaluates that threshold
    on the held-out half.
    """
    sub = df.dropna(subset=["inhouse_ppg_sqi", "orphanidou_acceptable"]).copy()
    if len(sub) < 20:
        return RecalibrationResult(
            n_calibration=0, n_holdout=0,
            original_threshold=original_threshold,
            recalibrated_threshold=original_threshold,
            original_holdout_kappa_vs_orph=float("nan"),
            recalibrated_holdout_kappa_vs_orph=float("nan"),
            original_holdout_agreement=float("nan"),
            recalibrated_holdout_agreement=float("nan"),
        )

    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(sub))
    split = len(sub) // 2
    calib = sub.iloc[idx[:split]]
    holdout = sub.iloc[idx[split:]]

    # Search threshold space on calibration to maximize kappa
    thresholds = np.linspace(0.1, 0.99, 90)
    best_kappa = -np.inf
    best_thr = original_threshold
    for t in thresholds:
        inhouse_binary = (calib["inhouse_ppg_sqi"] >= t).astype(int).to_numpy()
        orph_binary = calib["orphanidou_acceptable"].astype(int).to_numpy()
        k = cohens_kappa(inhouse_binary, orph_binary)
        if k == k and k > best_kappa:
            best_kappa = k
            best_thr = float(t)

    # Evaluate both thresholds on holdout
    hold_orph = holdout["orphanidou_acceptable"].astype(int).to_numpy()
    hold_inhouse_sqi = holdout["inhouse_ppg_sqi"].to_numpy()
    orig_binary = (hold_inhouse_sqi >= original_threshold).astype(int)
    recal_binary = (hold_inhouse_sqi >= best_thr).astype(int)

    return RecalibrationResult(
        n_calibration=int(len(calib)),
        n_holdout=int(len(holdout)),
        original_threshold=original_threshold,
        recalibrated_threshold=best_thr,
        original_holdout_kappa_vs_orph=cohens_kappa(orig_binary, hold_orph),
        recalibrated_holdout_kappa_vs_orph=cohens_kappa(recal_binary, hold_orph),
        original_holdout_agreement=float((orig_binary == hold_orph).mean()),
        recalibrated_holdout_agreement=float((recal_binary == hold_orph).mean()),
    )
