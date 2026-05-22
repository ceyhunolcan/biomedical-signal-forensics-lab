"""Generate a STARD-style data flow diagram for the WESAD validation pipeline.

The diagram shows how raw WESAD data flowed through the study into the four
analysis arms (HR agreement, SQI agreement, recalibration, downstream audit).

CONSORT-style flow diagrams were originally designed for randomized trials.
This paper is not a trial; it is a methodology audit. The closest analog among
EQUATOR reporting standards is STARD 2015 for diagnostic accuracy studies,
because chest ECG serves as the reference standard against which wrist PPG
serves as the index modality. The diagram below follows STARD conventions
adapted to the multi-arm structure of this paper.

Produces: paper/figures/fig_flow_diagram.png and fig_flow_diagram.svg
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


# Visual style: clean black-and-white with subtle slate accents.
FONT = "DejaVu Sans"
BOX_FACE = "#fafbfc"
BOX_EDGE = "#1f2933"
ARROW_COLOR = "#1f2933"
TEXT_COLOR = "#0b1118"
ACCENT_FACE = "#eef3f8"

plt.rcParams.update({
    "font.family": FONT,
    "font.size": 9,
    "axes.linewidth": 0.6,
})


def add_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    face: str = BOX_FACE,
    edge: str = BOX_EDGE,
    fontsize: int = 9,
    weight: str = "normal",
) -> tuple[float, float]:
    """Draw a rounded box centred at (x, y) and write text inside it.

    Returns (x, y) of the box bottom-centre for arrow attachment.
    """
    patch = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.10",
        linewidth=0.9,
        facecolor=face,
        edgecolor=edge,
    )
    ax.add_patch(patch)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=TEXT_COLOR,
        weight=weight,
        linespacing=1.25,
    )
    return (x, y - h / 2)


def add_arrow(ax, x0: float, y0: float, x1: float, y1: float) -> None:
    """Draw a small arrow from (x0, y0) to (x1, y1)."""
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="->",
            color=ARROW_COLOR,
            linewidth=0.9,
            shrinkA=2,
            shrinkB=2,
        ),
    )


def render(out_dir: Path) -> tuple[Path, Path]:
    fig, ax = plt.subplots(figsize=(10.5, 13.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.set_aspect("equal")
    ax.axis("off")

    # Title
    ax.text(
        5.0,
        13.55,
        "Figure 1. Data flow through the WESAD validation pipeline",
        ha="center",
        va="center",
        fontsize=11,
        weight="bold",
        color=TEXT_COLOR,
    )
    ax.text(
        5.0,
        13.20,
        "(STARD-style; this paper is a methodology audit, not a randomised trial)",
        ha="center",
        va="center",
        fontsize=8.5,
        style="italic",
        color="#4a5568",
    )

    # ----- Source data tier -----
    add_box(
        ax,
        x=5.0,
        y=12.30,
        w=7.6,
        h=0.95,
        text=(
            "WESAD dataset (Schmidt et al. 2018)\n"
            "Source: physiological signals from 17 enrolled participants;\n"
            "2 excluded by data curators before public release"
        ),
        face=ACCENT_FACE,
    )
    add_arrow(ax, 5.0, 11.83, 5.0, 11.50)

    add_box(
        ax,
        x=5.0,
        y=11.10,
        w=7.6,
        h=0.80,
        text=(
            "n = 15 subjects analysed in this study (S2-S11, S13-S17)\n"
            "Synchronised acquisition: Empatica E4 wrist PPG (64 Hz) +\n"
            "RespiBAN chest ECG (700 Hz)"
        ),
    )
    add_arrow(ax, 5.0, 10.70, 5.0, 10.40)

    # ----- Pre-processing -----
    add_box(
        ax,
        x=5.0,
        y=10.00,
        w=7.6,
        h=0.85,
        text=(
            "Pre-processing:\n"
            "Resample to common time base; segment into non-overlapping 30-second windows;\n"
            "across all 15 subjects this produced 6,585 candidate windows"
        ),
    )
    add_arrow(ax, 5.0, 9.58, 5.0, 9.28)

    # ----- Per-window processing -----
    add_box(
        ax,
        x=5.0,
        y=8.85,
        w=7.6,
        h=1.00,
        text=(
            "Per-window processing (each of 6,585 windows):\n"
            "(a) ECG R-peak detection -> HR_ECG (bpm)\n"
            "(b) PPG pulse-peak detection -> HR_PPG (bpm)\n"
            "(c) Four SQI scores: in-house, Orphanidou 2015, Sukor 2011, Elgendi 2016"
        ),
    )
    add_arrow(ax, 5.0, 8.35, 5.0, 8.05)

    # ----- Exclusion box -----
    add_box(
        ax,
        x=5.0,
        y=7.65,
        w=7.6,
        h=0.80,
        text=(
            "Exclusions during per-window processing: 0\n"
            "All 6,585 windows successfully produced an ECG HR, PPG HR, and four SQI scores;\n"
            "no auto-rejection on processing failure"
        ),
        face="#fff7e6",
    )
    add_arrow(ax, 5.0, 7.25, 5.0, 6.95)

    # ----- Final analysed sample -----
    add_box(
        ax,
        x=5.0,
        y=6.55,
        w=7.6,
        h=0.65,
        text=(
            "Analysed: 6,585 windows from 15 subjects\n"
            "(mean 439 windows per subject; range 320-520)"
        ),
        face=ACCENT_FACE,
        weight="bold",
    )

    # ----- Four-arm branching -----
    # Arrows down from analysed sample to four arms
    y_arm_top = 5.55
    y_arm_mid = 4.75
    arm_xs = [1.45, 4.05, 6.65, 9.25]  # roughly evenly spaced across width

    # Draw four splitting arrows
    for x in arm_xs:
        add_arrow(ax, 5.0, 6.22, x, y_arm_top + 0.40)

    # Arrow endpoint geometry between arm title box and arm detail box.
    # Title box: centred at y_arm_top, h=0.80 -> bottom edge at y_arm_top - 0.40.
    # Detail box: centred at y_arm_mid - 0.20, h=1.30 -> top edge at y_arm_mid + 0.45.
    # Land the arrowhead above the rounded-corner extent of the detail box.
    arrow_y_start = y_arm_top - 0.43
    arrow_y_end = y_arm_mid + 0.58

    # Arm 1: HR agreement
    add_box(
        ax,
        x=arm_xs[0],
        y=y_arm_top,
        w=2.30,
        h=0.80,
        text="Arm 1: HR agreement\n(Section 4.1)",
        weight="bold",
        fontsize=8.5,
    )
    add_box(
        ax,
        x=arm_xs[0],
        y=y_arm_mid - 0.20,
        w=2.30,
        h=1.30,
        text=(
            "n = 6,585 paired\nHR_PPG vs HR_ECG values\n"
            "- Bland-Altman (bias +3.57 bpm,\n  LoA -23.14 to +30.28)\n"
            "- Pearson r = +0.70\n"
            "- Per-state pairs"
        ),
        fontsize=8,
    )
    add_arrow(ax, arm_xs[0], arrow_y_start, arm_xs[0], arrow_y_end)

    # Arm 2: SQI agreement
    add_box(
        ax,
        x=arm_xs[1],
        y=y_arm_top,
        w=2.30,
        h=0.80,
        text="Arm 2: SQI agreement\n(Section 4.2)",
        weight="bold",
        fontsize=8.5,
    )
    add_box(
        ax,
        x=arm_xs[1],
        y=y_arm_mid - 0.20,
        w=2.30,
        h=1.30,
        text=(
            "Four SQI binarisations\nper window\n"
            "- Pairwise Cohen's kappa\n  matrix (six pairs)\n"
            "- All-3-published-fail:\n  44.6% of windows (2,936)"
        ),
        fontsize=8,
    )
    add_arrow(ax, arm_xs[1], arrow_y_start, arm_xs[1], arrow_y_end)

    # Arm 3: Recalibration
    add_box(
        ax,
        x=arm_xs[2],
        y=y_arm_top,
        w=2.30,
        h=0.80,
        text="Arm 3: Threshold\nrecalibration (Section 4.3)",
        weight="bold",
        fontsize=8.5,
    )
    add_box(
        ax,
        x=arm_xs[2],
        y=y_arm_mid - 0.20,
        w=2.30,
        h=1.30,
        text=(
            "Random subject-stratified\nsplit of 6,585 windows\n"
            "- Train: 3,292 windows\n- Holdout: 3,293 windows\n"
            "- Delta kappa = 0.000\n  (recalibration failed)"
        ),
        fontsize=8,
    )
    add_arrow(ax, arm_xs[2], arrow_y_start, arm_xs[2], arrow_y_end)

    # Arm 4: Downstream audit
    add_box(
        ax,
        x=arm_xs[3],
        y=y_arm_top,
        w=2.30,
        h=0.80,
        text="Arm 4: Downstream audit\n(Section 4.6)",
        weight="bold",
        fontsize=8.5,
    )
    add_box(
        ax,
        x=arm_xs[3],
        y=y_arm_mid - 0.20,
        w=2.30,
        h=1.30,
        text=(
            "Per-subject biomarker:\nLF/HF ratio (baseline vs\nstress); LOSO 15-fold\n"
            "- Wilcoxon p = 1.5e-4\n  (paired, n=15)\n"
            "- AUROC 0.804 -> 0.823"
        ),
        fontsize=8,
    )
    add_arrow(ax, arm_xs[3], arrow_y_start, arm_xs[3], arrow_y_end)

    # ----- Reporting and reproducibility tier -----
    y_repro = 2.85
    add_box(
        ax,
        x=5.0,
        y=y_repro,
        w=8.6,
        h=0.85,
        text=(
            "Reporting and reproducibility (Appendix B)\n"
            "Compliance summary against TRIPOD+AI (Collins et al. 2024) and STARD 2015 (Bossuyt et al. 2015);\n"
            "applicability assessments for CONSORT-AI (Liu et al. 2020) and DECIDE-AI (Vasey et al. 2022)"
        ),
        face=ACCENT_FACE,
    )

    # Caption / legend at bottom
    caption_text = (
        "Notes on flow-diagram conventions used here:\n"
        "(i) All counts (n=15 subjects, 6,585 windows) refer to data actually analysed; no post-hoc\n"
        "    exclusion occurred at any stage of this study.\n"
        "(ii) Arms 1-4 use overlapping observations from the same 6,585 windows; per-arm statistics\n"
        "     are reported in their respective Results subsections.\n"
        "(iii) STARD-style conventions (Bossuyt et al. 2015) apply most directly to Arms 1-3, where\n"
        "      chest ECG serves as the reference standard. Arm 4 follows TRIPOD+AI conventions\n"
        "      (Collins et al. 2024) because it evaluates a prediction model rather than diagnostic\n"
        "      accuracy. CONSORT-AI (Liu et al. 2020) and DECIDE-AI (Vasey et al. 2022) are\n"
        "      referenced for completeness but do not apply: this paper is not a clinical trial\n"
        "      and contains no early-stage clinical deployment."
    )
    ax.text(
        5.0,
        1.05,
        caption_text,
        ha="center",
        va="center",
        fontsize=7.5,
        color="#2d3748",
        linespacing=1.50,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "fig_flow_diagram.png"
    svg_path = out_dir / "fig_flow_diagram.svg"
    fig.savefig(png_path, dpi=200, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png_path, svg_path


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    target = here / "paper" / "figures"
    png, svg = render(target)
    print(f"Wrote: {png}")
    print(f"Wrote: {svg}")
