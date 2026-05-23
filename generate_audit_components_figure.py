"""Generate an audit-components overview figure for presentations and the docs site.

Produces paper/figures/fig6_audit_components.png: a four-panel diagram
summarising each audit component with its central methodological choice and
its WESAD headline finding.

Run: python generate_audit_components_figure.py
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

NAVY = "#0b3d91"
RED = "#e63946"
BG = "#f8f9fa"
PALE = "#f1f5f9"
TEXT = "#1a1a2e"
MUTED = "#666"


def panel(ax, title, methodology, finding, color):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_facecolor("white")

    # Coloured top bar
    ax.add_patch(patches.Rectangle((0, 9.0), 10, 1.0, color=color, alpha=0.92))

    # Title
    ax.text(0.4, 9.5, title, fontsize=13, fontweight="bold",
            color="white", verticalalignment="center")

    # Methodology block
    ax.text(0.4, 8.0, "METHOD", fontsize=8, fontweight="bold",
            color=MUTED)
    ax.text(0.4, 6.5, methodology, fontsize=10.5, color=TEXT,
            verticalalignment="top", wrap=True, linespacing=1.45)

    # Divider
    ax.plot([0.4, 9.6], [4.6, 4.6], color="#ddd", lw=0.8)

    # Finding block
    ax.text(0.4, 4.2, "WESAD FINDING", fontsize=8, fontweight="bold",
            color=MUTED)
    ax.text(0.4, 3.4, finding, fontsize=10.5, color=TEXT,
            verticalalignment="top", wrap=True, linespacing=1.45)

    # Outer frame
    for spine_pos in [(0, 0, 10, 9.0)]:
        ax.add_patch(patches.Rectangle(spine_pos[:2], spine_pos[2], spine_pos[3],
                                       fill=False, edgecolor="#e0e0e0", lw=1.0))


def main():
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), dpi=140)
    fig.patch.set_facecolor("white")

    panel(axes[0, 0],
          "1. Signal-Quality Audit",
          "Four independent SQI indicators applied per window:\n"
          "in-house, Orphanidou 2015, Sukor 2011, Elgendi 2016.\n"
          "Pairwise Cohen's kappa across indicators reports\n"
          "the degree of disagreement.",
          "44.6% three-baseline consensus rejection rate.\n"
          "Median pairwise kappa = -0.20.\n"
          "In-house pipeline passes all 6,585 windows.",
          NAVY)

    panel(axes[0, 1],
          "2. Algorithmic-Fairness Audit",
          "Pass-rate and downstream-AUROC stratified by\n"
          "device family, skin tone, per-subject drift, and\n"
          "motion intensity. Effect sizes with bootstrap\n"
          "CIs and permutation-test p-values.",
          "Disparities reported as quantitative effect sizes;\n"
          "no categorical fair/unfair claim is made.\n"
          "Strata are user-extensible.",
          "#7d3c98")

    panel(axes[1, 0],
          "3. Causal-Sensitivity Audit",
          "Back-door adjustment via AIPW (doubly-robust),\n"
          "E-values quantifying minimum unmeasured-confounder\n"
          "strength, and negative-control exposures testing\n"
          "for spurious residual association.",
          "Estimates with E-value below 1.5 are flagged as\n"
          "causally fragile in the recommendations layer.\n"
          "Sign-flip under adjustment is highlighted.",
          "#1d8348")

    panel(axes[1, 1],
          "4. Downstream-Impact Audit",
          "LOSO AUROC of a stress classifier before and\n"
          "after the audit pipeline. Recalibration kappa\n"
          "from 50/50 random per-subject split.\n"
          "Paired window-level Spearman rho and Wilcoxon.",
          "AUROC 0.804 to 0.823 (delta = +0.019).\n"
          "Delta kappa = 0.000 after recalibration.\n"
          "Spearman rho = +0.10, Wilcoxon p = 1.5e-4.",
          RED)

    fig.suptitle("Four audit components, each producing quantitative evidence",
                 fontsize=15, fontweight="bold", y=0.99, color=TEXT)
    fig.text(0.5, 0.01,
             "WESAD validation cohort: n = 15 subjects, 6,585 thirty-second windows. "
             "Headline findings from results/wesad_deep_analysis.json.",
             ha="center", fontsize=9.5, color=MUTED, style="italic")

    plt.tight_layout(rect=(0, 0.03, 1, 0.96))

    os.makedirs("paper/figures", exist_ok=True)
    out = "paper/figures/fig6_audit_components.png"
    plt.savefig(out, dpi=140, facecolor="white", bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
