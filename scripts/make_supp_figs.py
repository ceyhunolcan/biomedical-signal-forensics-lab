"""Generate supplementary figures S2 and S3 from already-computed CSVs.

S2: Threshold sensitivity (results/real_data/threshold_sensitivity.csv).
    Two panels (WESAD, PPG-DaLiA). Lines: joint-condition % and
    published-only consensus rejection %. Flat across thresholds 0.50-0.95.

S3: LOSO per-subject held-out Cohen's kappa
    (results/real_data/loso_recalibration.csv). Bar plot of 15 subjects,
    sorted by kappa, color-coded degenerate vs non-degenerate, mean line.

Run:  python3 scripts/make_supp_figs.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica', 'Arial', 'DejaVu Sans'],
    'svg.fonttype': 'none',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'axes.linewidth': 0.5,
})

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "paper" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ORPH    = '#0072B2'
SUKOR   = '#E69F00'
ELGENDI = '#009E73'
NEG     = '#c44536'
DEGEN   = '#888888'
TEXT_DARK  = '#1a1a1a'
TEXT_MUTED = '#555555'


def fig_s2_threshold_sensitivity():
    ts = pd.read_csv(ROOT / "results" / "real_data" / "threshold_sensitivity.csv")
    datasets_in_csv = ts['dataset'].unique().tolist()
    print(f"  S2: dataset names in CSV = {datasets_in_csv}")

    # Map by lowercase match so we tolerate naming variation
    def get_df(name_substr):
        for d in datasets_in_csv:
            if name_substr.lower().replace('-', '').replace('_', '') in d.lower().replace('-', '').replace('_', ''):
                return ts[ts['dataset'] == d].sort_values('threshold').reset_index(drop=True)
        raise ValueError(f"No dataset matching {name_substr} in {datasets_in_csv}")

    wesad = get_df('wesad')
    dalia = get_df('dalia')

    fig, axes = plt.subplots(1, 2, figsize=(7.08, 3.5), facecolor='white')
    panels = [
        {'panel': 'a', 'name': 'WESAD',     'df': wesad},
        {'panel': 'b', 'name': 'PPG-DaLiA', 'df': dalia},
    ]

    for ax, ds in zip(axes, panels):
        df = ds['df']
        ax.plot(df['threshold'], df['inhouse_pass_AND_all3_pub_fail_pct'],
                'o-', color=ORPH, linewidth=1.5, markersize=4.5,
                label='In-house pass AND all 3 published fail', zorder=3)
        ax.plot(df['threshold'], df['pub_only_consensus_rejection_pct'],
                's--', color=SUKOR, linewidth=1.5, markersize=4.5,
                label='Published-only consensus rejection', zorder=2)

        ax.axvline(0.70, color='#bbbbbb', linewidth=0.6, linestyle=':', zorder=1)
        ax.text(0.70, 41.0, 'default\n(0.70)', fontsize=7,
                color='#888888', ha='center', va='bottom')

        ax.text(-0.12, 1.02, ds['panel'],
                transform=ax.transAxes, ha='left', va='bottom',
                fontsize=12, fontweight='bold', color=TEXT_DARK)
        ax.set_title(ds['name'], fontsize=10, fontweight='bold', pad=8)
        ax.set_xlabel('In-house SQI threshold', fontsize=8.5)
        ax.set_ylabel('Fraction of windows (%)', fontsize=8.5)

        joint_min = df['inhouse_pass_AND_all3_pub_fail_pct'].min()
        joint_max = df['inhouse_pass_AND_all3_pub_fail_pct'].max()
        ax.text(0.97, 0.05,
                f'Range across thresholds:\n{joint_max - joint_min:.3f} pp',
                transform=ax.transAxes, ha='right', va='bottom',
                fontsize=7.5, style='italic', color=TEXT_MUTED)

        ax.set_ylim(40, 50)
        ax.set_xlim(0.48, 0.97)
        ax.tick_params(labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        if ax is axes[0]:
            ax.legend(loc='upper left', fontsize=7, frameon=False)

    plt.tight_layout(pad=0.5)
    out_png = OUT_DIR / 'figS2_threshold_sensitivity.png'
    out_pdf = OUT_DIR / 'figS2_threshold_sensitivity.pdf'
    plt.savefig(out_png, dpi=600, bbox_inches='tight', facecolor='white')
    plt.savefig(out_pdf, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  S2: saved {out_png.name} and {out_pdf.name}")


def fig_s3_loso_kappa():
    loso = pd.read_csv(ROOT / "results" / "real_data" / "loso_recalibration.csv")
    loso['degenerate'] = loso['note'].notna()
    loso = loso.sort_values('test_kappa').reset_index(drop=True)

    mean_kappa = loso['test_kappa'].mean()
    n = len(loso)
    n_degen = int(loso['degenerate'].sum())
    n_nondegen = n - n_degen
    nondegen = loso[~loso['degenerate']]
    n_nondegen_nonpositive = int((nondegen['test_kappa'] <= 0).sum())
    print(f"  S3: mean held-out kappa = {mean_kappa:+.3f}, "
          f"n_degenerate = {n_degen}/{n}, "
          f"n_nondegen non-positive = {n_nondegen_nonpositive}/{n_nondegen}")

    fig, ax = plt.subplots(figsize=(7.08, 3.6), facecolor='white')
    colors = [NEG if not d else DEGEN for d in loso['degenerate']]
    x = list(range(n))
    ax.bar(x, loso['test_kappa'], color=colors, edgecolor='black',
           linewidth=0.6, width=0.72)

    ax.axhline(mean_kappa, color='#000000', linewidth=1.0,
               linestyle='--', zorder=3)
    ax.text(n - 0.4, mean_kappa, f"  mean = {mean_kappa:+.3f}",
            fontsize=8, color='#000000', va='center', ha='left')

    ax.axhline(0, color='#666666', linewidth=0.5, zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels(loso['held_out'], fontsize=8)
    ax.set_xlabel('Held-out subject (LOSO fold)', fontsize=9)
    ax.set_ylabel("Held-out Cohen's $\\kappa$\n(in-house vs Orphanidou)",
                  fontsize=9)

    ax.text(0.5, 1.04,
            f"LOSO recalibration: {n_degen} of {n} folds degenerate; "
            f"{n_nondegen_nonpositive} of {n_nondegen} non-degenerate are non-positive",
            transform=ax.transAxes, ha='center', va='bottom',
            fontsize=9, fontweight='bold', color=TEXT_DARK)

    legend_handles = [
        Patch(facecolor=NEG, edgecolor='black',
              label='Non-degenerate (in-house varies on held-out subject)'),
        Patch(facecolor=DEGEN, edgecolor='black',
              label='Degenerate (in-house constant on held-out subject)'),
    ]
    ax.legend(handles=legend_handles, loc='lower right',
              fontsize=7.5, frameon=False)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=8)

    plt.tight_layout(pad=0.5)
    out_png = OUT_DIR / 'figS3_loso_recalibration.png'
    out_pdf = OUT_DIR / 'figS3_loso_recalibration.pdf'
    plt.savefig(out_png, dpi=600, bbox_inches='tight', facecolor='white')
    plt.savefig(out_pdf, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  S3: saved {out_png.name} and {out_pdf.name}")


if __name__ == "__main__":
    print("Generating supplementary figures...")
    fig_s2_threshold_sensitivity()
    fig_s3_loso_kappa()
    print("Done.")
