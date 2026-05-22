"""Publication-quality figures for the deep WESAD analysis.

Six figures:
  1. Bland-Altman: HR-from-PPG vs HR-from-ECG, color-coded by state
  2. Scatter HR_PPG vs HR_ECG with identity line and per-subject color
  3. SQI pass rate by method (in-house vs Orphanidou vs Sukor)
  4. Per-state distribution panels (4-subplot: SQI, motion, HR error, template corr)
  5. Motion vs HR disagreement scatter
  6. Recalibration: original vs recalibrated kappa across thresholds
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..utils.paths import ensure_dir, resolve
from ..utils.plotting import apply_style, savefig


STATE_COLORS = {
    "baseline": "#2E86AB",   # blue
    "stress":   "#E63946",   # red
    "amusement": "#F4A261",  # orange
    "meditation": "#52B788", # green
}

SUBJECT_MARKERS = {"S2": "o", "S3": "^", "S4": "s", "S5": "D"}


def fig_bland_altman_hr(window_df: pd.DataFrame, out: str) -> Path:
    """Bland-Altman: mean of HR_PPG and HR_ECG vs their difference."""
    apply_style()
    sub = window_df.dropna(subset=["hr_ecg", "hr_ppg"])
    means = (sub["hr_ecg"] + sub["hr_ppg"]) / 2.0
    diffs = sub["hr_ppg"] - sub["hr_ecg"]
    bias = float(diffs.mean())
    sd = float(diffs.std(ddof=1))
    loa_low, loa_high = bias - 1.96 * sd, bias + 1.96 * sd

    fig, ax = plt.subplots(figsize=(7, 5))
    for state, sub_s in sub.groupby("label_name"):
        m_s = (sub_s["hr_ecg"] + sub_s["hr_ppg"]) / 2.0
        d_s = sub_s["hr_ppg"] - sub_s["hr_ecg"]
        ax.scatter(m_s, d_s, s=14, alpha=0.45,
                   color=STATE_COLORS.get(state, "#666"), label=state)
    ax.axhline(bias, color="black", linewidth=1.2, label=f"bias = {bias:+.1f} bpm")
    ax.axhline(loa_low, color="black", linestyle="--", linewidth=1,
               label=f"95% LoA = [{loa_low:+.1f}, {loa_high:+.1f}]")
    ax.axhline(loa_high, color="black", linestyle="--", linewidth=1)
    ax.axhline(0, color="grey", linewidth=0.5, alpha=0.5)
    ax.set_xlabel("Mean HR from chest ECG and wrist PPG (bpm)")
    ax.set_ylabel("HR$_{PPG}$ – HR$_{ECG}$ (bpm)")
    ax.set_title("Bland-Altman: wrist PPG vs chest ECG heart rate, real WESAD data")
    ax.legend(loc="upper right", fontsize=8, frameon=True)
    return savefig(fig, resolve(out))


def fig_hr_scatter(window_df: pd.DataFrame, out: str) -> Path:
    """HR_PPG vs HR_ECG scatter with identity line."""
    apply_style()
    sub = window_df.dropna(subset=["hr_ecg", "hr_ppg"])

    fig, ax = plt.subplots(figsize=(6, 6))
    for state, sub_s in sub.groupby("label_name"):
        ax.scatter(sub_s["hr_ecg"], sub_s["hr_ppg"], s=14, alpha=0.45,
                   color=STATE_COLORS.get(state, "#666"), label=state)
    lo = min(sub["hr_ecg"].min(), sub["hr_ppg"].min()) - 5
    hi = max(sub["hr_ecg"].max(), sub["hr_ppg"].max()) + 5
    ax.plot([lo, hi], [lo, hi], color="black", linewidth=0.8, linestyle="--",
            label="identity")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel("Heart rate from chest ECG (bpm)")
    ax.set_ylabel("Heart rate from wrist PPG (bpm)")
    ax.set_title("Cross-modality HR agreement, by labeled state")
    ax.legend(loc="lower right", fontsize=8, frameon=True)
    return savefig(fig, resolve(out))


def fig_sqi_pass_rates(three_way_result, out: str) -> Path:
    """Bar chart of pass rates across three SQI methods."""
    apply_style()
    methods = ["In-house\n(threshold 0.7)", "Orphanidou\n(2015)", "Sukor\n(2011)"]
    rates = [
        three_way_result.inhouse_pass_rate,
        three_way_result.orphanidou_pass_rate,
        three_way_result.sukor_pass_rate,
    ]
    colors = ["#5C7AEA", "#7F8CAA", "#A5B68D"]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(methods, rates, color=colors, edgecolor="black", linewidth=0.7)
    for b, r in zip(bars, rates):
        ax.text(b.get_x() + b.get_width()/2, r + 0.02, f"{r:.2f}",
                ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("Fraction of windows passing")
    ax.set_ylim(0, 1.1)
    ax.set_title(f"PPG SQI pass rate by method on real WESAD (n={three_way_result.n_windows})")
    ax.grid(axis="y", alpha=0.3)
    return savefig(fig, resolve(out))


def fig_per_state_panels(window_df: pd.DataFrame, out: str) -> Path:
    """4-panel boxplot: SQI, motion, HR error, template corr by state."""
    apply_style()
    states_order = ["baseline", "stress", "amusement"]
    sub = window_df[window_df["label_name"].isin(states_order)].copy()

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    metrics = [
        ("inhouse_ppg_sqi", "In-house PPG SQI", axes[0, 0]),
        ("inhouse_ppg_motion", "PPG motion artifact score", axes[0, 1]),
        ("hr_abs_diff", "|HR$_{PPG}$ – HR$_{ECG}$| (bpm)", axes[1, 0]),
        ("orphanidou_template_corr", "Orphanidou template correlation", axes[1, 1]),
    ]
    for col, ylabel, ax in metrics:
        data = [sub[sub["label_name"] == s][col].dropna().values for s in states_order]
        bp = ax.boxplot(data, labels=states_order, patch_artist=True,
                        medianprops={"color": "black", "linewidth": 1.5})
        for patch, state in zip(bp["boxes"], states_order):
            patch.set_facecolor(STATE_COLORS.get(state, "#666"))
            patch.set_alpha(0.7)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Per-state distributions on real WESAD (S2+S3 pooled, n=830)", y=1.02)
    fig.tight_layout()
    return savefig(fig, resolve(out))


def fig_motion_vs_hr_error(window_df: pd.DataFrame, out: str) -> Path:
    """Scatter: PPG motion score vs |HR_PPG - HR_ECG|."""
    apply_style()
    sub = window_df.dropna(subset=["inhouse_ppg_motion", "hr_abs_diff"])
    fig, ax = plt.subplots(figsize=(7, 5))
    for state, sub_s in sub.groupby("label_name"):
        ax.scatter(sub_s["inhouse_ppg_motion"], sub_s["hr_abs_diff"], s=14,
                   alpha=0.45, color=STATE_COLORS.get(state, "#666"), label=state)
    # Add the trend (simple linear)
    x = sub["inhouse_ppg_motion"].to_numpy()
    y = sub["hr_abs_diff"].to_numpy()
    if len(x) > 5 and np.std(x) > 1e-9:
        m, b = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 100)
        ax.plot(xs, m * xs + b, color="black", linewidth=1.2,
                label=f"linear fit, slope={m:.1f}")
    ax.set_xlabel("In-house PPG motion artifact score")
    ax.set_ylabel("|HR$_{PPG}$ – HR$_{ECG}$| (bpm)")
    ax.set_title("Motion predicts HR-modality disagreement, real WESAD")
    ax.legend(loc="upper right", fontsize=8, frameon=True)
    return savefig(fig, resolve(out))


def fig_recalibration_curve(window_df: pd.DataFrame, out: str) -> Path:
    """Cohen's kappa vs in-house SQI threshold, with original and recalibrated."""
    from ..evaluation.deep_real_analysis import cohens_kappa

    apply_style()
    sub = window_df.dropna(subset=["inhouse_ppg_sqi", "orphanidou_acceptable"])
    thresholds = np.linspace(0.1, 0.99, 90)
    kappas = []
    for t in thresholds:
        inhouse_b = (sub["inhouse_ppg_sqi"] >= t).astype(int).to_numpy()
        orph_b = sub["orphanidou_acceptable"].astype(int).to_numpy()
        kappas.append(cohens_kappa(inhouse_b, orph_b))
    kappas = np.array(kappas)
    best_idx = int(np.nanargmax(kappas))
    best_thr = float(thresholds[best_idx])
    best_kappa = float(kappas[best_idx])

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(thresholds, kappas, color="#264653", linewidth=1.8)
    ax.axvline(0.7, color="grey", linestyle="--", linewidth=1,
               label=f"original threshold 0.70 (κ={kappas[np.argmin(np.abs(thresholds-0.7))]:+.3f})")
    ax.axvline(best_thr, color="crimson", linestyle="--", linewidth=1,
               label=f"recalibrated to {best_thr:.3f} (κ={best_kappa:+.3f})")
    ax.axhline(0, color="black", linewidth=0.5, alpha=0.5)
    ax.set_xlabel("In-house PPG SQI threshold")
    ax.set_ylabel("Cohen's κ vs Orphanidou (2015) pass/fail")
    ax.set_title("Recalibration: agreement vs threshold, real WESAD")
    ax.legend(loc="upper left", fontsize=8, frameon=True)
    return savefig(fig, resolve(out))


def make_all_figures(window_df: pd.DataFrame, three_way_result,
                     out_dir: Path) -> dict[str, Path]:
    """Generate all six figures and return their paths."""
    out_dir = ensure_dir(out_dir)
    paths = {}
    paths["bland_altman"] = fig_bland_altman_hr(window_df, str(out_dir / "fig1_bland_altman_hr.png"))
    paths["hr_scatter"] = fig_hr_scatter(window_df, str(out_dir / "fig2_hr_scatter.png"))
    paths["sqi_pass_rates"] = fig_sqi_pass_rates(three_way_result, str(out_dir / "fig3_sqi_pass_rates.png"))
    paths["per_state"] = fig_per_state_panels(window_df, str(out_dir / "fig4_per_state_panels.png"))
    paths["motion_vs_error"] = fig_motion_vs_hr_error(window_df, str(out_dir / "fig5_motion_vs_hr_error.png"))
    paths["recalibration"] = fig_recalibration_curve(window_df, str(out_dir / "fig6_recalibration.png"))
    return paths
