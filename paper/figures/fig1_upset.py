"""Generate Figure 1: two-panel UpSet plot of cross-method acceptance structure.

Reproduces paper/figures/fig1_upset.png from the committed window tables. Each
column is a combination of the three published wrist-PPG quality methods
(Orphanidou, Sukor, Elgendi) that accept a window; bar height is the number of
windows in that combination and the dot matrix marks the membership. The
all-reject column (consensus reject) is highlighted in crimson.

Run from anywhere:
    python3 paper/figures/fig1_upset.py
"""
from itertools import product
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TABLES = {
    "WESAD": ROOT / "results" / "real_data" / "wesad_deep" / "window_table.csv",
    "PPG-DaLiA": ROOT / "results" / "real_data" / "ppg_dalia" / "window_table.csv",
}
OUT = ROOT / "paper" / "figures" / "fig1_upset.png"
METHODS = ["Orphanidou", "Sukor", "Elgendi"]
ACCEPT_COLS = ["orphanidou_acceptable", "sukor_acceptable", "elgendi_acceptable"]


def compute(path):
    df = pd.read_csv(path)
    o, s, e = (df[c].astype(bool).values for c in ACCEPT_COLS)
    n = len(df)
    counts = {combo: int(((o == combo[0]) & (s == combo[1]) & (e == combo[2])).sum())
              for combo in product([True, False], repeat=3)}
    return n, counts


def _color(combo):
    if combo == (False, False, False):
        return "#b2182b"
    if combo == (True, True, True):
        return "#2166ac"
    return "#92c5de"


def draw(ax_bar, ax_mat, n, counts, title):
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    combos = [k for k, _ in items]
    heights = [c for _, c in items]
    x = np.arange(len(items))
    ax_bar.bar(x, heights, color=[_color(c) for c in combos],
               edgecolor="black", linewidth=0.5, width=0.7)
    for xi, h in zip(x, heights):
        ax_bar.text(xi, h + max(heights) * 0.012, f"{h:,}\n{100 * h / n:.1f}%",
                    ha="center", va="bottom", fontsize=7.5)
    ax_bar.set_ylim(0, max(heights) * 1.22)
    ax_bar.set_ylabel("Windows")
    ax_bar.set_title(title, loc="left", fontsize=11, fontweight="bold", pad=8)
    ax_bar.set_xticks([])
    ax_bar.grid(axis="y", alpha=0.25, linewidth=0.5)
    ax_bar.set_axisbelow(True)
    for sp in ["top", "right"]:
        ax_bar.spines[sp].set_visible(False)
    ax_mat.set_ylim(-0.5, len(METHODS) - 0.5)
    ax_mat.invert_yaxis()
    for yi in range(len(METHODS)):
        for xi, c in zip(x, combos):
            ax_mat.plot(xi, yi, "o", ms=9,
                        color=("#333333" if c[yi] else "#dcdcdc"), mec="none", zorder=3)
    for xi, c in zip(x, combos):
        ys = [yi for yi in range(len(METHODS)) if c[yi]]
        if len(ys) >= 2:
            ax_mat.plot([xi, xi], [min(ys), max(ys)], "-", color="#333333", lw=1.5, zorder=2)
    ax_mat.set_yticks(range(len(METHODS)))
    ax_mat.set_yticklabels(METHODS, fontsize=9)
    ax_mat.set_xticks([])
    ax_mat.tick_params(length=0)
    for sp in ["top", "right", "bottom", "left"]:
        ax_mat.spines[sp].set_visible(False)


def main():
    n1, c1 = compute(TABLES["WESAD"])
    n2, c2 = compute(TABLES["PPG-DaLiA"])
    fig = plt.figure(figsize=(9, 10.5))
    gs = GridSpec(5, 1, height_ratios=[3, 1.0, 0.55, 3, 1.0], hspace=0.08)
    axb1 = fig.add_subplot(gs[0]); axm1 = fig.add_subplot(gs[1], sharex=axb1)
    axb2 = fig.add_subplot(gs[3]); axm2 = fig.add_subplot(gs[4], sharex=axb2)
    draw(axb1, axm1, n1, c1, f"(a) WESAD (n = {n1:,} windows)")
    draw(axb2, axm2, n2, c2, f"(b) PPG-DaLiA (n = {n2:,} windows)")
    axb1.legend(handles=[
        Patch(facecolor="#b2182b", edgecolor="black", label="rejected by all three (consensus reject)"),
        Patch(facecolor="#2166ac", edgecolor="black", label="accepted by all three"),
        Patch(facecolor="#92c5de", edgecolor="black", label="accepted by a subset")],
        fontsize=7.5, loc="upper right", framealpha=0.95)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
