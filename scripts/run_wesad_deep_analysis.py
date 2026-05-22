"""Deep analysis of the WESAD real-data pilot.

Produces:
  results/real_data/wesad/orphanidou_per_subject.csv
  results/real_data/wesad/state_tests_within_subject.csv
  results/real_data/wesad/recalibration_roc.csv
  results/real_data/wesad/recalibration_summary.csv
  results/real_data/wesad/figure_pilot.png

This runs on top of `scripts/run_real_data_pilot.py`, which must be run first
to produce the input CSVs (signal_quality.csv, windows_meta.csv, etc.).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import balanced_accuracy_score, roc_auc_score, roc_curve

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.data.wesad_adapter import extract_windows, load_wesad_pickle
from src.signals.orphanidou_sqi import batch_orphanidou, head_to_head
from src.utils.logging import get_logger
from src.utils.paths import ensure_dir
from src.utils.plotting import apply_style

log = get_logger("wesad_deep_analysis")


def per_subject_orphanidou(sqi_df: pd.DataFrame, wesad_dir: Path) -> pd.DataFrame:
    """Compute the Orphanidou agreement stats separately for each subject."""
    rows = []
    for sid in sorted(sqi_df.subject_id.unique()):
        rec = load_wesad_pickle(wesad_dir / sid / f"{sid}.pkl")
        ecg_arr, ppg_arr, _ = extract_windows(rec, window_seconds=5.0)
        in_house = sqi_df[sqi_df.subject_id == sid]["ppg_sqi"].values
        n = min(len(in_house), len(ppg_arr))
        agree = head_to_head(ppg_arr[:n], in_house[:n], fs=64, modality="ppg")
        rows.append({
            "subject_id": sid,
            "n_windows": agree.n_windows,
            "in_house_mean": round(agree.in_house_mean, 4),
            "orphanidou_acceptable_frac": round(agree.orphanidou_acceptable_frac, 4),
            "spearman": (round(agree.spearman_with_continuous, 4)
                         if agree.spearman_with_continuous == agree.spearman_with_continuous
                         else None),
            "point_biserial": (round(agree.point_biserial_with_binary, 4)
                               if agree.point_biserial_with_binary == agree.point_biserial_with_binary
                               else None),
            **agree.crosstab,
        })
    return pd.DataFrame(rows)


def within_subject_state_tests(sqi_df: pd.DataFrame) -> pd.DataFrame:
    """Mann-Whitney U test on each (subject, metric, baseline vs state) pair.

    Returns a long-form DataFrame with one row per (subject, metric, contrast).
    """
    rows = []
    contrasts = [("baseline", "stress"), ("baseline", "amusement")]
    metrics = ["ppg_sqi", "ecg_sqi", "ppg_motion"]
    for sid in sorted(sqi_df.subject_id.unique()):
        sub = sqi_df[sqi_df.subject_id == sid]
        for state_a, state_b in contrasts:
            a = sub[sub.label_name == state_a]
            b = sub[sub.label_name == state_b]
            if len(a) < 5 or len(b) < 5:
                continue
            for m in metrics:
                if m not in sub.columns:
                    continue
                ax = a[m].dropna().values
                bx = b[m].dropna().values
                if len(ax) < 5 or len(bx) < 5:
                    continue
                # For SQI metrics: state_a (baseline) should be higher
                # For motion: state_b (stress/amusement) should be higher, flip
                if m in ("ppg_sqi", "ecg_sqi"):
                    alternative = "greater"  # baseline > state
                else:  # ppg_motion
                    alternative = "less"     # baseline < state
                u, p = stats.mannwhitneyu(ax, bx, alternative=alternative)
                auc = u / (len(ax) * len(bx))
                cliff_delta = 2 * auc - 1
                rows.append({
                    "subject_id": sid,
                    "metric": m,
                    "contrast": f"{state_a}_vs_{state_b}",
                    "n_a": len(ax),
                    "n_b": len(bx),
                    "median_a": round(float(np.median(ax)), 5),
                    "median_b": round(float(np.median(bx)), 5),
                    "p_value": round(float(p), 4),
                    "cliffs_delta": round(float(cliff_delta), 3),
                })
    return pd.DataFrame(rows)


def recalibration_analysis(sqi_df: pd.DataFrame, wesad_dir: Path,
                           default_threshold: float = 0.7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute the ROC curve for in-house continuous SQI vs Orphanidou binary,
    plus a summary at default and Youden's-J-optimal thresholds.

    Returns (roc_df, summary_df).
    """
    # Re-extract PPG windows to feed batch_orphanidou; same code path as the
    # pilot script for consistency.
    all_ppg = []
    for sid in sorted(sqi_df.subject_id.unique()):
        rec = load_wesad_pickle(wesad_dir / sid / f"{sid}.pkl")
        _, ppg_arr, _ = extract_windows(rec, window_seconds=5.0)
        all_ppg.append(ppg_arr)
    all_ppg = np.concatenate(all_ppg, axis=0)

    reports = batch_orphanidou(all_ppg, fs=64, modality="ppg")
    orph_pass = np.array([r.acceptable for r in reports]).astype(int)
    in_house = sqi_df["ppg_sqi"].values
    n = min(len(in_house), len(orph_pass))
    in_house = in_house[:n]
    orph_pass = orph_pass[:n]

    # AUROC
    auroc = roc_auc_score(orph_pass, in_house)
    fpr, tpr, thresh = roc_curve(orph_pass, in_house)
    youden = tpr - fpr
    best_idx = int(np.argmax(youden))
    best_threshold = float(thresh[best_idx])

    roc_df = pd.DataFrame({
        "threshold": thresh, "tpr": tpr, "fpr": fpr, "youden_j": youden,
    })

    default_pass = (in_house >= default_threshold).astype(int)
    recal_pass = (in_house >= best_threshold).astype(int)

    summary = pd.DataFrame([
        {
            "threshold_name": "default",
            "threshold_value": default_threshold,
            "in_house_pass_rate": float(default_pass.mean()),
            "orphanidou_pass_rate": float(orph_pass.mean()),
            "agreement_rate": float((default_pass == orph_pass).mean()),
            "balanced_accuracy": float(balanced_accuracy_score(orph_pass, default_pass)),
            "auroc": float(auroc),
        },
        {
            "threshold_name": "recalibrated_youden",
            "threshold_value": best_threshold,
            "in_house_pass_rate": float(recal_pass.mean()),
            "orphanidou_pass_rate": float(orph_pass.mean()),
            "agreement_rate": float((recal_pass == orph_pass).mean()),
            "balanced_accuracy": float(balanced_accuracy_score(orph_pass, recal_pass)),
            "auroc": float(auroc),
        },
    ])
    return roc_df, summary


def build_figure(sqi_df: pd.DataFrame, wesad_dir: Path, summary: pd.DataFrame,
                 roc_df: pd.DataFrame, out_path: Path) -> Path:
    """Compose the 4-panel pilot figure."""
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))

    # Re-extract orphanidou predictions for the scatter
    all_ppg = []
    for sid in sorted(sqi_df.subject_id.unique()):
        rec = load_wesad_pickle(wesad_dir / sid / f"{sid}.pkl")
        _, ppg_arr, _ = extract_windows(rec, window_seconds=5.0)
        all_ppg.append(ppg_arr)
    all_ppg = np.concatenate(all_ppg, axis=0)
    reports = batch_orphanidou(all_ppg, fs=64, modality="ppg")
    orph_pass = np.array([r.acceptable for r in reports]).astype(int)
    orph_continuous = np.array([
        r.template_corr if r.template_corr == r.template_corr else 0.0
        for r in reports
    ])
    in_house = sqi_df["ppg_sqi"].values
    n = min(len(in_house), len(orph_pass))
    in_house = in_house[:n]
    orph_pass = orph_pass[:n]
    orph_continuous = orph_continuous[:n]

    # Panel A: SQI distribution by labeled state
    ax = axes[0, 0]
    states = ["baseline", "stress", "amusement"]
    data_by_state = [sqi_df[sqi_df.label_name == s].ppg_sqi.values for s in states]
    parts = ax.violinplot(data_by_state, positions=[1, 2, 3],
                          showmedians=True, widths=0.7)
    for pc in parts['bodies']:
        pc.set_alpha(0.5)
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(states)
    ax.set_ylabel("In-house PPG SQI")
    ax.set_title(f"A. PPG SQI by labeled state\n(in-house thresholds, n={n} windows)")
    ax.axhline(0.7, color="crimson", linestyle="--", linewidth=1, alpha=0.5,
               label="default threshold (0.7)")
    ax.legend(loc="lower left", fontsize=8)

    # Panel B: in-house vs Orphanidou scatter
    ax = axes[0, 1]
    ax.scatter(in_house, orph_continuous, s=8, alpha=0.3,
               c=orph_pass, cmap="RdYlGn")
    ax.set_xlabel("In-house continuous PPG SQI")
    ax.set_ylabel("Orphanidou template correlation")
    spearman = pd.Series(in_house).corr(pd.Series(orph_continuous), method="spearman")
    ax.set_title(f"B. Method agreement on real PPG\n(Spearman ρ = {spearman:.3f}, n={n})")
    ax.axvline(0.7, color="gray", linestyle="--", alpha=0.5, linewidth=1)
    recal_threshold = float(summary[summary.threshold_name == "recalibrated_youden"][
        "threshold_value"].iloc[0])
    ax.axvline(recal_threshold, color="navy", linestyle="--", alpha=0.7, linewidth=1,
               label=f"recalibrated ({recal_threshold:.3f})")
    ax.legend(loc="lower right", fontsize=8)

    # Panel C: ROC
    ax = axes[1, 0]
    ax.plot(roc_df.fpr, roc_df.tpr, linewidth=2, color="navy")
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", alpha=0.5, linewidth=1)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    auroc = float(summary.iloc[0]["auroc"])
    ax.set_title(f"C. In-house SQI ranks Orphanidou pass/fail\n(AUROC = {auroc:.3f})")
    y_idx = (roc_df.tpr - roc_df.fpr).idxmax()
    ax.scatter([roc_df.fpr[y_idx]], [roc_df.tpr[y_idx]], s=80, color="crimson",
               zorder=5, label=f"Youden's J: thresh={recal_threshold:.3f}")
    ax.legend(loc="lower right", fontsize=8)

    # Panel D: balanced accuracy
    ax = axes[1, 1]
    ba_default = float(summary[summary.threshold_name == "default"]["balanced_accuracy"].iloc[0])
    ba_recal = float(summary[summary.threshold_name == "recalibrated_youden"][
        "balanced_accuracy"].iloc[0])
    bars = ax.bar(["Default\nthreshold (0.7)",
                   f"Recalibrated\nthreshold ({recal_threshold:.3f})"],
                  [ba_default, ba_recal], color=["#888", "#1f4eaf"], width=0.55)
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5, linewidth=1, label="chance")
    ax.set_ylabel("Balanced accuracy vs Orphanidou")
    ax.set_title("D. Recalibration improves agreement\nwith published baseline")
    ax.set_ylim(0, 1)
    for bar, val in zip(bars, [ba_default, ba_recal]):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.02, f"{val:.3f}",
                ha="center", fontsize=9)
    ax.legend(loc="upper left", fontsize=8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, type=Path,
                        help="Path to the WESAD directory")
    parser.add_argument("--results-dir", default=Path("results/real_data/wesad"),
                        type=Path,
                        help="Directory containing the outputs of "
                             "run_real_data_pilot.py")
    args = parser.parse_args()

    out_dir = ensure_dir(args.results_dir)
    sqi_path = out_dir / "signal_quality.csv"
    if not sqi_path.exists():
        log.error("signal_quality.csv not found at %s. Run "
                  "scripts/run_real_data_pilot.py first.", sqi_path)
        sys.exit(1)

    sqi_df = pd.read_csv(sqi_path)
    log.info("Loaded %d windows across %d subjects.",
             len(sqi_df), sqi_df.subject_id.nunique())

    log.info("Per-subject Orphanidou agreement …")
    per_subj = per_subject_orphanidou(sqi_df, args.path)
    per_subj.to_csv(out_dir / "orphanidou_per_subject.csv", index=False)
    log.info("\n%s", per_subj.to_string(index=False))

    log.info("Within-subject state-contrast tests …")
    state_tests = within_subject_state_tests(sqi_df)
    state_tests.to_csv(out_dir / "state_tests_within_subject.csv", index=False)
    log.info("\n%s", state_tests.to_string(index=False))

    log.info("Recalibration analysis …")
    roc_df, summary = recalibration_analysis(sqi_df, args.path)
    roc_df.to_csv(out_dir / "recalibration_roc.csv", index=False)
    summary.to_csv(out_dir / "recalibration_summary.csv", index=False)
    log.info("\n%s", summary.to_string(index=False))

    log.info("Building 4-panel pilot figure …")
    fig_path = build_figure(sqi_df, args.path, summary, roc_df,
                            out_dir / "figure_pilot.png")
    log.info("Wrote %s", fig_path)


if __name__ == "__main__":
    main()
