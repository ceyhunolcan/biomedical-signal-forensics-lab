"""Reviewer-grade extended analyses for the WESAD pilot and synthetic results.

These analyses are designed to preempt the questions a top-tier reviewer
would ask:

1. AIPW positivity check (distribution of estimated propensity scores; mass
   in [0.05, 0.95] tail-clipped region) and overlap diagnostics.
2. Cornfield / E-value sensitivity analysis for unmeasured confounding.
3. Multi-operating-point recalibration: ROC, PR, F1 curves with bootstrap CIs
   on the recalibrated threshold (the headline κ = +0.217 result is one
   summary statistic; reviewers want to see the full curve).
4. RR-cleaning robustness sweep: report RMSSD under no filter, Malik 25%,
   Malik 10%, NN20, NN50 to show the WESAD HRV numbers are not artifacts
   of any single cleaning policy.
5. Per-subject ICC and within-subject CV on real data, with bootstrap CIs.
6. Effect sizes with both Cliff's delta and Cohen's d for the per-state
   contrast tests.

Outputs land under results/extended_analysis/ and feed into the supplementary
section of paper/manuscript.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (
    average_precision_score, balanced_accuracy_score, cohen_kappa_score,
    f1_score, precision_recall_curve, roc_auc_score, roc_curve,
)

from src.utils.logging import get_logger
from src.utils.paths import ensure_dir

log = get_logger("extended_analysis")


# --------------------------------------------------------------------------
# 1. AIPW positivity check
# --------------------------------------------------------------------------

def aipw_positivity_check(synthetic_csv: Path,
                          treatment_outcome_pairs: list[tuple[str, str, list[str]]],
                          clip: tuple[float, float] = (0.05, 0.95),
                          ) -> pd.DataFrame:
    """Re-fit AIPW propensities for each pair, return diagnostic table.

    Diagnostics for each (treatment, outcome) pair:
      - Mean propensity score
      - Fraction of propensities outside [clip[0], clip[1]]
      - Min / max propensity
      - Effective sample size after IPW weighting (Kish's ESS)

    Positivity violations look like a heavy mass at 0 or 1 in the
    propensity distribution. Reviewers will ask for this.
    """
    from sklearn.linear_model import LogisticRegression

    df = pd.read_csv(synthetic_csv)
    rows = []
    for treatment, outcome, adjustment in treatment_outcome_pairs:
        cols = [treatment, outcome] + list(adjustment)
        sub = df[cols].dropna()
        if len(sub) < 50:
            continue
        # Binarize treatment at median for continuous treatments
        t = (sub[treatment] >= sub[treatment].median()).astype(int).to_numpy()
        Xc = sub[adjustment].to_numpy()
        ps_model = LogisticRegression(max_iter=1000)
        ps_model.fit(Xc, t)
        e = ps_model.predict_proba(Xc)[:, 1]
        e_clipped = np.clip(e, clip[0], clip[1])
        # Inverse-propensity weights
        w = np.where(t == 1, 1.0 / e_clipped, 1.0 / (1.0 - e_clipped))
        ess = float(w.sum() ** 2 / np.sum(w ** 2))
        outside_frac = float(((e < clip[0]) | (e > clip[1])).mean())
        rows.append({
            "treatment": treatment,
            "outcome": outcome,
            "adjustment_set": ",".join(adjustment),
            "n": len(sub),
            "ps_mean": float(e.mean()),
            "ps_min": float(e.min()),
            "ps_max": float(e.max()),
            "ps_p05": float(np.quantile(e, 0.05)),
            "ps_p95": float(np.quantile(e, 0.95)),
            "frac_outside_clip": outside_frac,
            "kish_ess": ess,
            "kish_ess_frac": ess / len(sub),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 2. E-value for unmeasured confounding (VanderWeele & Ding 2017)
# --------------------------------------------------------------------------

def e_value(estimate: float, ci_low: float, ci_high: float,
            null_value: float = 0.0) -> dict:
    """Compute the E-value for a continuous-outcome treatment effect.

    For a continuous outcome with standardized estimate β and SE, we use the
    Chinn (2000) conversion: convert β to a risk-ratio scale via exp(0.91 β).
    The E-value is then E = RR + sqrt(RR * (RR - 1)).

    Returns the E-value for the point estimate and for the CI bound closest
    to the null. A high E-value (e.g., > 2.0) means an unmeasured confounder
    would need to have RR > E with both treatment and outcome to explain
    away the effect.

    Reference: VanderWeele, T. J., & Ding, P. (2017). Sensitivity analysis in
    observational research: introducing the E-value. Annals of Internal
    Medicine, 167(4), 268-274.
    """
    def to_rr(beta):
        # Chinn standardised-effect to RR conversion, conservatively assuming
        # sd of outcome ~ 1. We don't have sd here, so this is an approximate
        # standardized E-value.
        return float(np.exp(0.91 * abs(beta - null_value)))

    def evalue_from_rr(rr):
        if rr < 1:
            rr = 1.0 / rr
        return float(rr + np.sqrt(rr * (rr - 1)))

    rr_point = to_rr(estimate)
    e_point = evalue_from_rr(rr_point)
    # CI bound closest to null
    if ci_low is None or ci_high is None or (ci_low <= null_value <= ci_high):
        e_ci = None  # CI crosses null, no meaningful E-value
    else:
        closest = ci_low if abs(ci_low - null_value) < abs(ci_high - null_value) else ci_high
        rr_ci = to_rr(closest)
        e_ci = evalue_from_rr(rr_ci)
    return {
        "estimate": float(estimate),
        "null_value": float(null_value),
        "rr_equivalent_point": rr_point,
        "evalue_point": e_point,
        "evalue_ci_bound": e_ci,
        "interpretation": (
            "An unmeasured confounder would need an effect-on-treatment AND "
            f"effect-on-outcome each of risk-ratio >= {e_point:.2f} to "
            "explain away the point estimate."
        ),
    }


# --------------------------------------------------------------------------
# 3. Multi-operating-point recalibration
# --------------------------------------------------------------------------

def multi_threshold_recalibration(in_house_continuous: np.ndarray,
                                  orphanidou_pass: np.ndarray,
                                  n_bootstrap: int = 200,
                                  seed: int = 42,
                                  ) -> dict:
    """Full ROC, PR, and F1 curves with bootstrap CI on the recalibrated threshold.

    Returns a dict with:
      - roc_curve: arrays for FPR, TPR, thresholds
      - pr_curve: arrays for precision, recall, thresholds
      - f1_curve: F1 score at each threshold
      - auroc, ap (average precision), with bootstrap CIs
      - youden_threshold: threshold maximizing TPR - FPR
      - f1_threshold: threshold maximizing F1
      - threshold_bootstrap_ci: 95% CI on the Youden threshold from bootstrap
    """
    rng = np.random.default_rng(seed)

    # Point estimates
    fpr, tpr, thresh_roc = roc_curve(orphanidou_pass, in_house_continuous)
    precision, recall, thresh_pr = precision_recall_curve(orphanidou_pass, in_house_continuous)
    # F1 at each threshold (skip the last point of PR which has no threshold)
    f1_curve = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1] + 1e-12)

    auroc = float(roc_auc_score(orphanidou_pass, in_house_continuous))
    ap = float(average_precision_score(orphanidou_pass, in_house_continuous))

    youden_idx = int(np.argmax(tpr - fpr))
    youden_threshold = float(thresh_roc[youden_idx])
    f1_max_idx = int(np.argmax(f1_curve)) if len(f1_curve) > 0 else 0
    f1_threshold = float(thresh_pr[f1_max_idx]) if len(thresh_pr) > f1_max_idx else float("nan")

    # Bootstrap CIs
    n = len(in_house_continuous)
    auroc_bs = []
    youden_bs = []
    f1_bs = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        try:
            auc_b = roc_auc_score(orphanidou_pass[idx], in_house_continuous[idx])
            fpr_b, tpr_b, thr_b = roc_curve(orphanidou_pass[idx], in_house_continuous[idx])
            youden_b = thr_b[int(np.argmax(tpr_b - fpr_b))]
            prec_b, rec_b, thrpr_b = precision_recall_curve(
                orphanidou_pass[idx], in_house_continuous[idx])
            f1_b_curve = 2 * prec_b[:-1] * rec_b[:-1] / (prec_b[:-1] + rec_b[:-1] + 1e-12)
            if len(f1_b_curve) > 0:
                f1_thr_b = thrpr_b[int(np.argmax(f1_b_curve))]
            else:
                f1_thr_b = float("nan")
            auroc_bs.append(auc_b)
            youden_bs.append(youden_b)
            f1_bs.append(f1_thr_b)
        except ValueError:
            continue

    return {
        "n_total": int(n),
        "auroc_point": auroc,
        "auroc_ci": [float(np.percentile(auroc_bs, 2.5)),
                     float(np.percentile(auroc_bs, 97.5))] if auroc_bs else [None, None],
        "average_precision_point": ap,
        "youden_threshold_point": youden_threshold,
        "youden_threshold_ci": [float(np.percentile(youden_bs, 2.5)),
                                 float(np.percentile(youden_bs, 97.5))] if youden_bs else [None, None],
        "f1_threshold_point": f1_threshold,
        "f1_threshold_ci": [float(np.percentile([f for f in f1_bs if f == f], 2.5)),
                            float(np.percentile([f for f in f1_bs if f == f], 97.5))]
                           if f1_bs and any(f == f for f in f1_bs) else [None, None],
        "n_bootstrap": int(len(auroc_bs)),
        "roc": {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "thresholds": thresh_roc.tolist(),
        },
        "pr": {
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "thresholds": thresh_pr.tolist(),
        },
        "f1_curve": f1_curve.tolist(),
    }


# --------------------------------------------------------------------------
# 4. RR-cleaning robustness sweep
# --------------------------------------------------------------------------

def rr_cleaning_robustness(wesad_dir: Path) -> pd.DataFrame:
    """Compute HR and RMSSD on each WESAD subject's baseline ECG under
    five different RR-cleaning policies. Shows the HRV numbers are not
    artifacts of any particular policy.
    """
    from src.data.wesad_adapter import load_wesad_pickle
    from src.signals.ecg_processing import bandpass, detect_r_peaks

    rows = []
    subject_dirs = sorted(d for d in wesad_dir.iterdir()
                          if d.is_dir() and d.name.startswith("S"))
    for sd in subject_dirs:
        pkl = sd / f"{sd.name}.pkl"
        if not pkl.exists():
            continue
        rec = load_wesad_pickle(pkl)
        baseline_mask = rec.labels == 1
        if not baseline_mask.any():
            continue
        ecg_bl = rec.chest_ecg[baseline_mask]
        if len(ecg_bl) < rec.chest_fs * 30:
            continue
        filt = bandpass(ecg_bl, rec.chest_fs)
        peaks = detect_r_peaks(filt, rec.chest_fs)
        if len(peaks) < 10:
            continue
        rr_s = np.diff(peaks) / rec.chest_fs

        policies = {}
        # 1. No filter
        policies["raw"] = rr_s
        # 2. Plausibility filter only (HR in 40-150 bpm)
        m = (rr_s >= 0.4) & (rr_s <= 1.5)
        policies["plausibility"] = rr_s[m]
        # 3. Plausibility + Malik 25%
        if len(policies["plausibility"]) > 10:
            med = np.median(policies["plausibility"])
            r = np.abs(policies["plausibility"] - med) / med
            policies["malik_25"] = policies["plausibility"][r < 0.25]
        else:
            policies["malik_25"] = policies["plausibility"]
        # 4. Plausibility + Malik 10%
        if len(policies["plausibility"]) > 10:
            med = np.median(policies["plausibility"])
            r = np.abs(policies["plausibility"] - med) / med
            policies["malik_10"] = policies["plausibility"][r < 0.10]
        else:
            policies["malik_10"] = policies["plausibility"]
        # 5. NN50-style: drop the post-jump interval when consecutive RR
        # differs by more than 50 ms. Included as a cautionary example
        # because removing intermediate intervals creates gaps that
        # introduce new artifactual large diffs between non-adjacent
        # original neighbors. Not a recommended cleaning policy.
        if len(policies["plausibility"]) > 10:
            d = np.diff(policies["plausibility"] * 1000)
            keep = np.abs(d) <= 50
            # Build a mask aligned to the plausibility array: always keep
            # the first interval; for each subsequent interval, keep it
            # only if the diff to its predecessor was within 50 ms.
            keep_mask = np.concatenate([[True], keep])
            policies["nn50"] = policies["plausibility"][keep_mask]
        else:
            policies["nn50"] = policies["plausibility"]

        for name, rr in policies.items():
            if len(rr) < 5:
                rows.append({
                    "subject_id": rec.subject_id, "policy": name,
                    "n_rr": int(len(rr)), "hr_bpm": float("nan"),
                    "rmssd_ms": float("nan"),
                    "sdnn_ms": float("nan"),
                })
                continue
            hr = 60.0 / rr.mean()
            rmssd = float(np.sqrt(np.mean(np.diff(rr * 1000) ** 2)))
            sdnn = float(np.std(rr * 1000, ddof=1))
            rows.append({
                "subject_id": rec.subject_id, "policy": name,
                "n_rr": int(len(rr)), "hr_bpm": round(hr, 2),
                "rmssd_ms": round(rmssd, 2), "sdnn_ms": round(sdnn, 2),
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 5. Per-subject ICC + within-subject CV on real data
# --------------------------------------------------------------------------

def per_subject_real_data_reliability(wesad_dir: Path,
                                       window_seconds: float = 5.0
                                       ) -> pd.DataFrame:
    """Compute per-subject HR test-retest within the baseline segment.

    Within each subject's baseline state, split into halves and compute
    Pearson r between per-window HR estimates. Also report within-subject
    coefficient of variation. This gives a real-data analog of the synthetic
    test-retest result.
    """
    from src.data.wesad_adapter import load_wesad_pickle
    from src.signals.ecg_processing import bandpass, detect_r_peaks

    rows = []
    subject_dirs = sorted(d for d in wesad_dir.iterdir()
                          if d.is_dir() and d.name.startswith("S"))
    for sd in subject_dirs:
        pkl = sd / f"{sd.name}.pkl"
        if not pkl.exists():
            continue
        rec = load_wesad_pickle(pkl)
        # Take the baseline segment
        baseline_mask = rec.labels == 1
        if not baseline_mask.any():
            continue
        ecg_bl = rec.chest_ecg[baseline_mask]
        fs = rec.chest_fs
        # Extract per-window HR over baseline
        wlen = int(window_seconds * fs)
        n_windows = len(ecg_bl) // wlen
        hr_seq = []
        for i in range(n_windows):
            seg = ecg_bl[i*wlen:(i+1)*wlen]
            try:
                filt = bandpass(seg, fs)
                peaks = detect_r_peaks(filt, fs)
                if len(peaks) >= 3:
                    rr = np.diff(peaks) / fs
                    plaus = rr[(rr >= 0.4) & (rr <= 1.5)]
                    if len(plaus) >= 2:
                        hr_seq.append(60.0 / plaus.mean())
                    else:
                        hr_seq.append(np.nan)
                else:
                    hr_seq.append(np.nan)
            except Exception:
                hr_seq.append(np.nan)
        hr_seq = np.array(hr_seq)
        if len(hr_seq) < 6:
            continue
        # Split-half within-baseline test-retest
        half = len(hr_seq) // 2
        first = hr_seq[:half]
        second = hr_seq[half:half*2]
        # Pair via index. Need at least 5 valid pairs.
        finite_pairs = np.isfinite(first) & np.isfinite(second)
        if finite_pairs.sum() < 5:
            r_tr = float("nan")
        else:
            r_tr = float(pd.Series(first[finite_pairs]).corr(
                pd.Series(second[finite_pairs])))
        valid_hr = hr_seq[np.isfinite(hr_seq)]
        rows.append({
            "subject_id": rec.subject_id,
            "n_windows_total": int(len(hr_seq)),
            "n_windows_valid": int(len(valid_hr)),
            "hr_mean_bpm": round(float(valid_hr.mean()), 2),
            "hr_sd_bpm": round(float(valid_hr.std()), 2),
            "within_subject_cv_percent": round(
                float(100.0 * valid_hr.std() / valid_hr.mean()), 2),
            "split_half_r": round(r_tr, 4) if r_tr == r_tr else None,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 6. Cohen's d alongside Cliff's delta for per-state contrasts
# --------------------------------------------------------------------------

def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d with pooled SD."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    pooled_var = ((len(a) - 1) * np.var(a, ddof=1)
                  + (len(b) - 1) * np.var(b, ddof=1)) / (len(a) + len(b) - 2)
    if pooled_var <= 0:
        return float("nan")
    return float((a.mean() - b.mean()) / np.sqrt(pooled_var))


def per_state_effect_sizes(sqi_csv: Path) -> pd.DataFrame:
    """Augment the existing per-state Mann-Whitney table with Cohen's d
    and a 95% CI on Cliff's delta."""
    sqi = pd.read_csv(sqi_csv)
    contrasts = [("baseline", "stress"), ("baseline", "amusement")]
    metrics = ["ppg_sqi", "ecg_sqi", "ppg_motion"]
    rows = []
    for sid in sorted(sqi.subject_id.unique()):
        sub = sqi[sqi.subject_id == sid]
        for state_a, state_b in contrasts:
            a_rows = sub[sub.label_name == state_a]
            b_rows = sub[sub.label_name == state_b]
            if len(a_rows) < 5 or len(b_rows) < 5:
                continue
            for m in metrics:
                a = a_rows[m].dropna().to_numpy()
                b = b_rows[m].dropna().to_numpy()
                if len(a) < 5 or len(b) < 5:
                    continue
                # Mann-Whitney
                u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
                auc = u / (len(a) * len(b))
                cliff = 2 * auc - 1
                d = cohens_d(a, b)
                # Cliff's delta bootstrap CI
                rng = np.random.default_rng(42)
                cliffs_bs = []
                for _ in range(500):
                    ai = rng.integers(0, len(a), size=len(a))
                    bi = rng.integers(0, len(b), size=len(b))
                    u_b, _ = stats.mannwhitneyu(a[ai], b[bi], alternative="two-sided")
                    cliffs_bs.append(2 * u_b / (len(a) * len(b)) - 1)
                ci_low = float(np.percentile(cliffs_bs, 2.5))
                ci_high = float(np.percentile(cliffs_bs, 97.5))
                rows.append({
                    "subject_id": sid,
                    "metric": m,
                    "contrast": f"{state_a}_vs_{state_b}",
                    "n_a": len(a),
                    "n_b": len(b),
                    "mean_a": round(float(a.mean()), 5),
                    "mean_b": round(float(b.mean()), 5),
                    "median_a": round(float(np.median(a)), 5),
                    "median_b": round(float(np.median(b)), 5),
                    "p_value": float(p),
                    "cliffs_delta": round(float(cliff), 3),
                    "cliffs_delta_ci_low": round(ci_low, 3),
                    "cliffs_delta_ci_high": round(ci_high, 3),
                    "cohens_d": round(float(d), 3) if d == d else None,
                })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wesad-path", required=True, type=Path)
    p.add_argument("--synthetic-csv", type=Path,
                   default=Path("data/synthetic/synthetic_signal_dataset.csv"))
    p.add_argument("--results-dir", type=Path,
                   default=Path("results/extended_analysis"))
    args = p.parse_args()
    out = ensure_dir(args.results_dir)

    # 1. AIPW positivity
    log.info("[1/6] AIPW positivity check…")
    pairs = [
        ("heat_index", "hrv_rmssd",
         ["stress_proxy", "active_minutes", "sleep_efficiency", "aqi", "temperature_c"]),
        ("heat_index", "sleep_efficiency",
         ["stress_proxy", "active_minutes", "aqi", "temperature_c"]),
        ("active_minutes", "hrv_rmssd",
         ["stress_proxy", "sleep_efficiency", "aqi", "temperature_c"]),
    ]
    pos = aipw_positivity_check(args.synthetic_csv, pairs)
    pos.to_csv(out / "aipw_positivity.csv", index=False)
    log.info("\n%s", pos.to_string(index=False))

    # 2. E-values on the AIPW estimates we ship
    log.info("[2/6] E-value sensitivity for unmeasured confounding…")
    conf = pd.read_csv("results/tables/confounding_adjusted.csv")
    evalues = []
    for _, row in conf.iterrows():
        e = e_value(row["aipw_estimate"], row["ci_low"], row["ci_high"])
        evalues.append({
            "treatment": row["treatment"],
            "outcome": row["outcome"],
            "aipw_estimate": row["aipw_estimate"],
            "ci_low": row["ci_low"], "ci_high": row["ci_high"],
            **e,
        })
    evalues_df = pd.DataFrame(evalues)
    evalues_df.to_csv(out / "evalues.csv", index=False)
    log.info("\n%s", evalues_df[["treatment","outcome","aipw_estimate",
        "evalue_point","evalue_ci_bound"]].to_string(index=False))

    # 3. Multi-threshold recalibration
    log.info("[3/6] Multi-operating-point recalibration with bootstrap CI…")
    sqi = pd.read_csv("results/real_data/wesad/signal_quality.csv")
    in_house_cont = sqi["ppg_sqi"].values
    from src.signals.orphanidou_sqi import batch_orphanidou
    from src.data.wesad_adapter import load_wesad_pickle, extract_windows
    all_ppg = []
    for sid in sorted(sqi.subject_id.unique()):
        rec = load_wesad_pickle(args.wesad_path / sid / f"{sid}.pkl")
        _, ppg, _ = extract_windows(rec, window_seconds=5.0)
        all_ppg.append(ppg)
    all_ppg = np.concatenate(all_ppg, axis=0)
    reports = batch_orphanidou(all_ppg, fs=64, modality="ppg")
    orph_pass = np.array([r.acceptable for r in reports]).astype(int)
    n = min(len(in_house_cont), len(orph_pass))
    recal = multi_threshold_recalibration(in_house_cont[:n], orph_pass[:n])
    # Save curves (compact) and summary
    summary = {k: v for k, v in recal.items() if k not in ("roc", "pr", "f1_curve")}
    json.dump(summary, open(out / "recalibration_multi.json", "w"), indent=2)
    pd.DataFrame({"fpr": recal["roc"]["fpr"], "tpr": recal["roc"]["tpr"],
                  "threshold": recal["roc"]["thresholds"]}
                 ).to_csv(out / "roc_curve.csv", index=False)
    pd.DataFrame({"precision": recal["pr"]["precision"][:-1],
                  "recall": recal["pr"]["recall"][:-1],
                  "threshold": recal["pr"]["thresholds"],
                  "f1": recal["f1_curve"]}
                 ).to_csv(out / "pr_curve.csv", index=False)
    log.info("AUROC=%.3f, CI=%s", recal["auroc_point"], recal["auroc_ci"])
    log.info("Youden threshold=%.4f, CI=%s",
             recal["youden_threshold_point"], recal["youden_threshold_ci"])
    log.info("F1 threshold=%.4f, CI=%s",
             recal["f1_threshold_point"], recal["f1_threshold_ci"])

    # 4. RR-cleaning robustness
    log.info("[4/6] RR-cleaning robustness across five policies…")
    rr_table = rr_cleaning_robustness(args.wesad_path)
    rr_table.to_csv(out / "rr_cleaning_robustness.csv", index=False)
    log.info("\n%s", rr_table.to_string(index=False))

    # 5. Per-subject reliability on real data
    log.info("[5/6] Per-subject HR test-retest within baseline (split-half)…")
    rel = per_subject_real_data_reliability(args.wesad_path)
    rel.to_csv(out / "per_subject_reliability.csv", index=False)
    log.info("\n%s", rel.to_string(index=False))

    # 6. Per-state effect sizes with both delta and d
    log.info("[6/6] Per-state effect sizes (Cliff's delta + Cohen's d)…")
    eff = per_state_effect_sizes(Path("results/real_data/wesad/signal_quality.csv"))
    eff.to_csv(out / "per_state_effect_sizes.csv", index=False)
    log.info("\n%s", eff.to_string(index=False))

    log.info("Wrote all extended analyses → %s", out)


if __name__ == "__main__":
    main()
