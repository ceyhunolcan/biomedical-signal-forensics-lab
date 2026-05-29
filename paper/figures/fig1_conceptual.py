"""
Figure 1: conceptual Venn of three published PPG SQI methods
            on two public benchmarks (WESAD, PPG-DaLiA).

Design follows Nature / npj Digital Medicine conventions:
  - white background, hairline strokes
  - colorblind-safe Wong palette
  - text labels in plain text (no pill backgrounds)
  - panel labels (a, b) in top-left
  - headline number is a small annotation, not a graphic
  - story belongs in the caption, not on the figure
"""
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica', 'Arial', 'DejaVu Sans'],
    'svg.fonttype': 'none',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'axes.linewidth': 0.5,
})

# Wong colorblind-safe palette (Wong 2011, Nature Methods)
ORPH    = '#0072B2'  # blue
SUKOR   = '#E69F00'  # orange
ELGENDI = '#009E73'  # green
TEXT_DARK  = '#1a1a1a'
TEXT_MUTED = '#555555'
HAIRLINE   = '#cccccc'

DATASETS = [
    dict(panel='a', name='WESAD', n_subjects=15, n_windows=6585,
         paradigm='lab stress + amusement',
         orphanidou=25.6, sukor=25.5, elgendi=21.5,
         consensus_reject=44.6, median_kappa=-0.20),
    dict(panel='b', name='PPG-DaLiA', n_subjects=15, n_windows=18781,
         paradigm='ambulatory activities',
         orphanidou=28.2, sukor=27.1, elgendi=22.0,
         consensus_reject=43.1, median_kappa=-0.20),
]

# Figure: 180 mm wide (npj two-column), about 90 mm tall
fig, axes = plt.subplots(1, 2, figsize=(7.08, 3.9), facecolor='white')

R = 1.55   # circle radius (panel coords 0..10)
SEP = 2.0  # center-to-center; overlap ~ 1.1, ~35% of diameter

for ax, ds in zip(axes, DATASETS):
    # Equilateral triangle of circle centers
    cx, cy = 5.0, 5.05
    h = SEP * math.sqrt(3) / 2.0
    c_orph    = (cx - SEP / 2.0, cy + h / 3.0)
    c_sukor   = (cx + SEP / 2.0, cy + h / 3.0)
    c_elgendi = (cx,             cy - 2.0 * h / 3.0)

    for center, color in [(c_orph, ORPH), (c_sukor, SUKOR), (c_elgendi, ELGENDI)]:
        ax.add_patch(Circle(
            center, R,
            fill=True, facecolor=color, alpha=0.30,
            edgecolor=color, linewidth=0.9, zorder=2,
        ))

    # ---- Method labels: plain text, OUTSIDE each circle, no pill bbox ----
    # Orphanidou: upper-left
    ax.text(c_orph[0] - R * 1.05, c_orph[1] + R * 1.05,
            'Orphanidou 2015',
            ha='right', va='bottom',
            fontsize=8.5, color=ORPH, fontweight='bold')
    ax.text(c_orph[0] - R * 1.05, c_orph[1] + R * 1.05 - 0.42,
            f'{ds["orphanidou"]:.1f}% accepted',
            ha='right', va='bottom',
            fontsize=7.5, color=TEXT_MUTED)

    # Sukor: upper-right
    ax.text(c_sukor[0] + R * 1.05, c_sukor[1] + R * 1.05,
            'Sukor 2011',
            ha='left', va='bottom',
            fontsize=8.5, color=SUKOR, fontweight='bold')
    ax.text(c_sukor[0] + R * 1.05, c_sukor[1] + R * 1.05 - 0.42,
            f'{ds["sukor"]:.1f}% accepted',
            ha='left', va='bottom',
            fontsize=7.5, color=TEXT_MUTED)

    # Elgendi: below
    ax.text(c_elgendi[0], c_elgendi[1] - R * 1.10,
            'Elgendi 2016',
            ha='center', va='top',
            fontsize=8.5, color=ELGENDI, fontweight='bold')
    ax.text(c_elgendi[0], c_elgendi[1] - R * 1.10 - 0.40,
            f'{ds["elgendi"]:.1f}% accepted',
            ha='center', va='top',
            fontsize=7.5, color=TEXT_MUTED)

    # ---- Panel label (a / b): top-left, set apart from dataset header ----
    ax.text(0.0, 9.95, ds['panel'],
            ha='left', va='top',
            fontsize=12, fontweight='bold', color=TEXT_DARK)

    # ---- Dataset header ----
    ax.text(5.0, 9.3, ds['name'],
            ha='center', va='center',
            fontsize=10, fontweight='bold', color=TEXT_DARK)
    ax.text(5.0, 8.8,
            f"n = {ds['n_subjects']} · {ds['n_windows']:,} windows · {ds['paradigm']}",
            ha='center', va='center',
            fontsize=7.8, color=TEXT_MUTED, style='italic')

    # ---- Consensus statistic ----
    ax.text(5.0, 0.55,
            f"{ds['consensus_reject']:.1f}% rejected by all three methods",
            ha='center', va='center',
            fontsize=9.0, fontweight='bold', color=TEXT_DARK)
    ax.text(5.0, 0.10,
            f"median pairwise Cohen's κ = {ds['median_kappa']:+.2f}",
            ha='center', va='center',
            fontsize=7.5, color=TEXT_MUTED, style='italic')

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')

plt.tight_layout(pad=0.4)

out_dir = Path(__file__).parent
plt.savefig(out_dir / 'fig1_conceptual.png',
            dpi=600, bbox_inches='tight', facecolor='white')
plt.savefig(out_dir / 'fig1_conceptual.pdf',
            bbox_inches='tight', facecolor='white')
plt.close()

# ---- Layout sanity checks ----
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

cx, cy = 5.0, 5.05
h = SEP * math.sqrt(3) / 2.0
c_orph    = (cx - SEP / 2.0, cy + h / 3.0)
c_sukor   = (cx + SEP / 2.0, cy + h / 3.0)
c_elgendi = (cx,             cy - 2.0 * h / 3.0)

print(f"Circle radius R       = {R}")
print(f"Center separation SEP = {SEP}")
print(f"Pairwise overlap      = {2*R - SEP:.2f} ({(2*R - SEP)/(2*R)*100:.0f}% of diameter)")
print(f"c_orph    = ({c_orph[0]:.2f}, {c_orph[1]:.2f})")
print(f"c_sukor   = ({c_sukor[0]:.2f}, {c_sukor[1]:.2f})")
print(f"c_elgendi = ({c_elgendi[0]:.2f}, {c_elgendi[1]:.2f})")
print(f"orph - sukor    = {dist(c_orph, c_sukor):.3f}")
print(f"orph - elgendi  = {dist(c_orph, c_elgendi):.3f}")
print(f"sukor - elgendi = {dist(c_sukor, c_elgendi):.3f}")
print(f"Header text at y=9.55, top of upper circles at y={c_orph[1] + R:.2f}  -> gap = {9.55 - (c_orph[1] + R):.2f}")
print(f"Footer text at y=0.55, bottom of lower circle at y={c_elgendi[1] - R:.2f} -> gap = {(c_elgendi[1] - R) - 0.95:.2f}")
print("Saved fig1_conceptual.png (600 dpi) and fig1_conceptual.pdf")
