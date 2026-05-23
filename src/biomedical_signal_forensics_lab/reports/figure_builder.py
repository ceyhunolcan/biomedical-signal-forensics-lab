"""Publication-style figures. Matplotlib only.

Each function takes an already-loaded dataframe and writes a PNG to
results/figures/. Numbers are deliberately kept legible at small sizes
so they reproduce well in a PDF.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..utils.paths import ensure_dir, resolve
from ..utils.plotting import apply_style, savefig


def trust_radar(components: dict[str, float], out: str = "results/figures/trust_radar.png") -> Path:
    apply_style()
    labels = list(components.keys())
    values = list(components.values())
    if not labels:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No components to display", ha="center", va="center")
        ax.set_axis_off()
        return savefig(fig, resolve(out))
    # close the polygon
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_loop = values + [values[0]]
    angles_loop = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(projection="polar"))
    ax.plot(angles_loop, values_loop, linewidth=2)
    ax.fill(angles_loop, values_loop, alpha=0.2)
    ax.set_xticks(angles)
    ax.set_xticklabels([l.replace("_", "\n") for l in labels], fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_title("Digital Biomarker Trust Score components", pad=18)
    return savefig(fig, resolve(out))


def reliability_heatmap(df: pd.DataFrame,
                        out: str = "results/figures/reliability_heatmap.png") -> Path:
    apply_style()
    pivot = df.pivot_table(
        index="participant_id", columns="date",
        values="reliability_ground_truth", aggfunc="mean",
    ).iloc[:60, :]  # cap rows for legibility
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(pivot.to_numpy(), aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_xlabel("Day index")
    ax.set_ylabel("Participant (first 60)")
    ax.set_title("Per-participant reliability over time")
    fig.colorbar(im, ax=ax, label="reliability (ground truth)")
    return savefig(fig, resolve(out))


def confounding_scatter(df: pd.DataFrame, x: str = "heat_index", y: str = "hrv_rmssd",
                        out: str = "results/figures/confounding_scatter.png") -> Path:
    apply_style()
    if x not in df.columns or y not in df.columns:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, f"Missing columns ({x!r}, {y!r})",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return savefig(fig, resolve(out))
    sub = df[[x, y]].dropna()
    if sub.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, f"No finite ({x}, {y}) pairs",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return savefig(fig, resolve(out))
    sub = sub.sample(min(3000, len(sub)), random_state=0)
    fig, ax = plt.subplots()
    ax.scatter(sub[x], sub[y], s=4, alpha=0.3)
    if len(sub) > 5:
        m, b = np.polyfit(sub[x], sub[y], 1)
        xs = np.linspace(sub[x].min(), sub[x].max(), 100)
        ax.plot(xs, m * xs + b, color="crimson", linewidth=1.5,
                label=f"slope={m:.2f}")
        ax.legend()
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(f"Environmental confounding: {x} vs {y}")
    return savefig(fig, resolve(out))


def trust_distribution(scores: np.ndarray,
                       out: str = "results/figures/trust_distribution.png") -> Path:
    apply_style()
    fig, ax = plt.subplots()
    ax.hist(scores, bins=30, edgecolor="white")
    ax.axvline(80, color="green", linestyle="--", label="high")
    ax.axvline(60, color="orange", linestyle="--", label="moderate")
    ax.axvline(40, color="red", linestyle="--", label="low")
    ax.set_xlabel("Digital Biomarker Trust Score")
    ax.set_ylabel("Participants")
    ax.set_title("Cohort distribution of trust scores")
    ax.legend()
    return savefig(fig, resolve(out))


def signal_example(ecg: np.ndarray, ppg: np.ndarray, ecg_fs: int, ppg_fs: int,
                   out: str = "results/figures/signal_example.png") -> Path:
    apply_style()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 5), sharex=False)
    t_ecg = np.arange(len(ecg)) / ecg_fs
    t_ppg = np.arange(len(ppg)) / ppg_fs
    ax1.plot(t_ecg, ecg, linewidth=0.8)
    ax1.set_title("Synthetic ECG window")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Amplitude (a.u.)")
    ax2.plot(t_ppg, ppg, linewidth=0.8, color="darkorange")
    ax2.set_title("Synthetic PPG window")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Amplitude (a.u.)")
    fig.tight_layout()
    return savefig(fig, resolve(out))


def fairness_forest_plot(stratum_table: pd.DataFrame,
                         out: str = "results/figures/fairness_forest.png") -> Path:
    """Forest plot of per-stratum overall trust score with bootstrap CIs.

    Expects the output of `fairness_audit`: columns stratum_value,
    overall_trust_score, ci_low, ci_high.
    """
    apply_style()
    if stratum_table.empty:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, "No strata to display", ha="center", va="center")
        ax.set_axis_off()
        return savefig(fig, resolve(out))

    df = stratum_table.sort_values("overall_trust_score").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.45 * len(df) + 1.2)))
    ys = np.arange(len(df))
    ax.scatter(df["overall_trust_score"], ys, marker="o", s=42, zorder=3)
    for y, (lo, hi) in zip(ys, zip(df["ci_low"], df["ci_high"])):
        if pd.notna(lo) and pd.notna(hi):
            ax.plot([lo, hi], [y, y], color="gray", linewidth=1.4, zorder=2)
    # threshold bands
    for x, label, color in [(80, "high", "#1b9e77"), (60, "moderate", "#7570b3"),
                            (40, "low", "#d95f02")]:
        ax.axvline(x, linestyle="--", color=color, alpha=0.4, linewidth=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r}  (n={n})" for r, n in zip(df["stratum_value"], df["n_days"])])
    ax.set_xlabel("Overall trust score")
    title = f"Per-stratum DBTS: {df['stratum_column'].iloc[0]}"
    ax.set_title(title)
    ax.set_xlim(0, 100)
    fig.tight_layout()
    return savefig(fig, resolve(out))


def write_all(df: pd.DataFrame, cohort_trust: pd.DataFrame, components_example: dict,
              ecg: np.ndarray | None = None, ppg: np.ndarray | None = None,
              ecg_fs: int = 250, ppg_fs: int = 64) -> list[Path]:
    ensure_dir("results/figures")
    paths = []
    paths.append(trust_radar(components_example))
    paths.append(reliability_heatmap(df))
    paths.append(confounding_scatter(df))
    paths.append(trust_distribution(cohort_trust["overall_trust_score"].to_numpy()))
    if ecg is not None and ppg is not None:
        paths.append(signal_example(ecg, ppg, ecg_fs, ppg_fs))
    return paths
