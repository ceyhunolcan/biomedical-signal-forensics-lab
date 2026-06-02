"""Generate publication-grade figures from cited summary statistics.

These figures visualise numbers that are already reported in the manuscript
and README; they do not introduce new analyses. Output goes to
paper/figures/.

Run: python generate_results_figures.py
"""

from __future__ import annotations
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Shared palette
NAVY = "#0b3d91"
RED = "#e63946"
BG = "#f8f9fa"
PALE = "#f1f5f9"
TEXT = "#1a1a2e"
MUTED = "#666"

plt.rcParams.update({
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#999",
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "text.color": TEXT,
})


def fig_pass_rate_bars(out: str) -> None:
    """Bar chart of per-baseline pass rates on WESAD."""
    labels = ["In-house\n(threshold-based)",
              "Orphanidou\n(2015)",
              "Sukor\n(2011)",
              "Elgendi\n(2016)"]
    values = [1.0000, 0.2565, 0.2545, 0.2150]
    colors = [NAVY, RED, RED, RED]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=140)
    bars = ax.bar(labels, values, color=colors, alpha=0.88, width=0.62)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.025,
                f"{val:.4f}", ha="center", va="bottom",
                fontsize=11, fontweight="bold", color=TEXT)

    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Window pass rate", fontsize=11)
    ax.set_title("Per-baseline pass rate on WESAD\n(n = 15 subjects, 6,585 5-second windows)",
                 fontsize=12, fontweight="bold", pad=14)
    ax.axhline(1.0, ls=":", color="#999", lw=0.8, zorder=0)
    ax.set_facecolor(BG)
    fig.patch.set_facecolor("white")

    ax.text(0.5, 0.98,
            "In-house thresholds pass every window; three published baselines reject roughly three-quarters.",
            transform=fig.transFigure, ha="center", fontsize=9,
            color=MUTED, style="italic")

    plt.tight_layout(rect=(0, 0, 1, 0.94))
    plt.savefig(out, dpi=140, facecolor="white", bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def fig_kappa_heatmap(out: str) -> None:
    """3x3 pairwise Cohen's kappa heatmap for the three published baselines.

    In-house is excluded because its pass rate is 1.00, leaving Cohen's kappa
    undefined against any other baseline (zero marginal variance).
    """
    methods = ["Orphanidou", "Sukor", "Elgendi"]
    # Pairwise published kappas
    M = np.array([
        [1.0000, 0.4096, -0.1978],
        [0.4096, 1.0000, -0.2247],
        [-0.1978, -0.2247, 1.0000],
    ])

    fig, ax = plt.subplots(figsize=(6.5, 5.5), dpi=140)
    fig.patch.set_facecolor("white")

    im = ax.imshow(M, cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="equal")
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(methods, fontsize=11)
    ax.set_yticklabels(methods, fontsize=11)

    for i in range(3):
        for j in range(3):
            v = M[i, j]
            text_color = "white" if abs(v) > 0.35 else TEXT
            weight = "bold" if i != j else "normal"
            ax.text(j, i, f"{v:+.4f}" if i != j else "1.0000",
                    ha="center", va="center",
                    fontsize=12, color=text_color, fontweight=weight)

    ax.set_title("Pairwise Cohen's kappa across published SQI baselines",
                 fontsize=12, fontweight="bold", pad=14)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Cohen's kappa", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    ax.text(0.5, 0.02,
            "Two of three pairs disagree (negative kappa); the third agreement is modest.\n"
            "Median pairwise kappa = -0.1978.",
            transform=fig.transFigure, ha="center", fontsize=9,
            color=MUTED, style="italic")

    plt.tight_layout(rect=(0, 0.06, 1, 0.96))
    plt.savefig(out, dpi=140, facecolor="white", bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def fig_rejection_cascade(out: str) -> None:
    """Verdict-gap chart: in-house pipeline keeps every window while the
    three-baseline consensus rejects 44.6%.

    Two grouped horizontal bars partition the 6,585 windows by who decides:
      - In-house pipeline: passes 6,585, rejects 0.
      - Three-baseline consensus (Orphanidou and Sukor and Elgendi): passes
        3,650 (passed by at least one baseline), consensus-rejects 2,935
        (rejected by all three simultaneously).
    """
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=140)
    fig.patch.set_facecolor("white")

    rows = ["In-house pipeline\n(threshold-based SQI)",
            "Three-baseline consensus\n(Orphanidou + Sukor + Elgendi)"]
    y = np.array([1, 0])

    # In-house: 6585 pass, 0 reject
    ax.barh(y[0], 6585, height=0.5, color=NAVY, alpha=0.88, label="Passed")

    # Consensus: 3650 passed by at least one, 2935 rejected by all
    ax.barh(y[1], 3650, height=0.5, color=NAVY, alpha=0.55)
    ax.barh(y[1], 2935, left=3650, height=0.5, color=RED, alpha=0.88,
            label="Consensus-rejected (rejected by all three baselines)")

    # Annotations
    ax.text(6585 / 2, y[0], "6,585 passed (100.0%)",
            ha="center", va="center", fontsize=11, color="white", fontweight="bold")
    ax.text(3650 / 2, y[1], "3,650 passed by at least one (55.4%)",
            ha="center", va="center", fontsize=10, color="white", fontweight="bold")
    ax.text(3650 + 2935 / 2, y[1], "2,935 consensus-rejected (44.6%)",
            ha="center", va="center", fontsize=10, color="white", fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(rows, fontsize=11)
    ax.set_xlim(0, 7000)
    ax.set_xlabel("Number of 5-second windows", fontsize=11)
    ax.set_title("Verdict gap between in-house thresholds and three published SQI baselines\n"
                 "(WESAD, n = 15 subjects, 6,585 windows)",
                 fontsize=12, fontweight="bold", pad=14)
    ax.set_facecolor(BG)

    ax.text(0.5, 0.015,
            "The in-house pipeline passes every window. Applying three independent published baselines,\n"
            "2,935 of the same 6,585 windows are rejected by all three simultaneously (consensus rejection).",
            transform=fig.transFigure, ha="center", fontsize=9,
            color=MUTED, style="italic")

    plt.tight_layout(rect=(0, 0.10, 1, 0.95))
    plt.savefig(out, dpi=140, facecolor="white", bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def fig_downstream_outcomes(out: str) -> None:
    """Downstream stress-detection outcomes before and after the audit pipeline."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), dpi=140)
    fig.patch.set_facecolor("white")

    # Panel A: LOSO AUROC
    ax = axes[0]
    conditions = ["Baseline\n(no audit)", "After full\naudit pipeline"]
    auroc = [0.804, 0.823]
    bars = ax.bar(conditions, auroc, color=[MUTED, NAVY], alpha=0.88, width=0.55)
    for bar, v in zip(bars, auroc):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.008,
                f"{v:.3f}", ha="center", va="bottom",
                fontsize=12, fontweight="bold", color=TEXT)
    ax.set_ylim(0.75, 0.86)
    ax.set_ylabel("LOSO AUROC", fontsize=11)
    ax.set_title("A. Leave-one-subject-out AUROC",
                 fontsize=11, fontweight="bold", pad=10)
    ax.set_facecolor(BG)
    ax.text(0.5, -0.18, "delta = +0.019",
            transform=ax.transAxes, ha="center", fontsize=10,
            color=NAVY, fontweight="bold")

    # Panel B: paired effect, kappa change, Wilcoxon
    ax = axes[1]
    metrics = ["delta kappa\n(recalibration)", "Spearman rho\n(paired effect)"]
    values = [0.000, 0.100]
    colors = ["#999", NAVY]
    bars = ax.bar(metrics, values, color=colors, alpha=0.88, width=0.55)
    for bar, v in zip(bars, values):
        offset = 0.005 if v >= 0 else -0.012
        ax.text(bar.get_x() + bar.get_width() / 2, v + offset,
                f"{v:+.3f}" if v != 0 else "0.000",
                ha="center", va="bottom" if v >= 0 else "top",
                fontsize=12, fontweight="bold", color=TEXT)
    ax.set_ylim(-0.05, 0.18)
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_ylabel("Effect size", fontsize=11)
    ax.set_title("B. Recalibration effect and paired correlation",
                 fontsize=11, fontweight="bold", pad=10)
    ax.set_facecolor(BG)
    ax.text(0.5, -0.18, "Wilcoxon p = 1.5e-4",
            transform=ax.transAxes, ha="center", fontsize=10,
            color=NAVY, fontweight="bold")

    fig.suptitle("Downstream stress-detection outcomes (WESAD, n = 15)",
                 fontsize=13, fontweight="bold", y=1.00)

    fig.text(0.5, 0.005,
             "Quality filtering does not improve recalibrated agreement, "
             "but produces a small, statistically significant paired effect.",
             ha="center", fontsize=9, color=MUTED, style="italic")

    plt.tight_layout(rect=(0, 0.05, 1, 0.95))
    plt.savefig(out, dpi=140, facecolor="white", bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def main() -> None:
    os.makedirs("paper/figures", exist_ok=True)
    fig_pass_rate_bars("paper/figures/fig2_pass_rate_bars.png")
    fig_kappa_heatmap("paper/figures/fig3_kappa_heatmap.png")
    fig_rejection_cascade("paper/figures/fig4_rejection_cascade.png")
    fig_downstream_outcomes("paper/figures/fig5_downstream_outcomes.png")


if __name__ == "__main__":
    main()
