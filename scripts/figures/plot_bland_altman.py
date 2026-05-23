"""Generate a Bland-Altman plot of wrist-PPG HR vs chest-ECG HR.

Reads the WESAD analysis output JSON, produces a publication-grade
Bland-Altman PNG. Run after `scripts/run_deep_real_analysis.py` has written
its results JSON.

Usage:
    python scripts/figures/plot_bland_altman.py \\
        --input results/wesad_deep_analysis.json \\
        --output paper/figures/fig1_bland_altman.png

The script accepts either of two JSON schemas:

  schema A: top-level keys `hr_ppg` and `hr_ecg` mapping to equal-length lists
            of beats per minute.

  schema B: a list of records each with keys `hr_ppg` and `hr_ecg`.

If neither schema is found, a clear error is printed listing the top-level
keys so the user can adapt the script. No data are fabricated.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

NAVY = "#0b3d91"
RED = "#e63946"
MUTED = "#666"
TEXT = "#1a1a2e"


def load_paired_hr(input_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load paired heart rates from JSON or CSV.

    Supports:
      - CSV with columns hr_ppg and hr_ecg (per-window table from
        run_deep_real_analysis.py)
      - JSON dict with top-level keys hr_ppg and hr_ecg mapping to arrays
      - JSON list of records each with hr_ppg and hr_ecg fields
    """
    suffix = input_path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(input_path)
        if "hr_ppg" not in df.columns or "hr_ecg" not in df.columns:
            print(f"ERROR: CSV columns are {list(df.columns)}; expected hr_ppg "
                  "and hr_ecg.", file=sys.stderr)
            sys.exit(1)
        return df["hr_ppg"].to_numpy(dtype=float), df["hr_ecg"].to_numpy(dtype=float)

    raw = json.loads(input_path.read_text())

    if isinstance(raw, dict) and "hr_ppg" in raw and "hr_ecg" in raw:
        return (np.asarray(raw["hr_ppg"], dtype=float),
                np.asarray(raw["hr_ecg"], dtype=float))

    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        return (np.asarray([r["hr_ppg"] for r in raw], dtype=float),
                np.asarray([r["hr_ecg"] for r in raw], dtype=float))

    if isinstance(raw, dict):
        keys = sorted(raw.keys())
        print(f"ERROR: top-level dict has keys {keys} but neither schema A "
              "(hr_ppg + hr_ecg) nor schema B (list of records) matches.",
              file=sys.stderr)
    else:
        print(f"ERROR: top-level JSON type is {type(raw).__name__}, expected "
              "dict or list.", file=sys.stderr)
    sys.exit(1)


def bland_altman(ppg: np.ndarray, ecg: np.ndarray, output: Path) -> None:
    # Filter NaNs and obvious sentinels
    mask = np.isfinite(ppg) & np.isfinite(ecg)
    ppg, ecg = ppg[mask], ecg[mask]
    n = len(ppg)

    means = (ppg + ecg) / 2
    diffs = ppg - ecg

    bias = float(np.mean(diffs))
    sd = float(np.std(diffs, ddof=1))
    loa_lower = bias - 1.96 * sd
    loa_upper = bias + 1.96 * sd
    mae = float(np.mean(np.abs(diffs)))
    pearson_r = float(np.corrcoef(ppg, ecg)[0, 1])

    fig, ax = plt.subplots(figsize=(9, 6), dpi=140)
    fig.patch.set_facecolor("white")

    ax.scatter(means, diffs, s=8, alpha=0.25, color=NAVY, edgecolor="none")
    ax.axhline(bias, color=RED, lw=1.8, label=f"Bias = {bias:+.2f} bpm")
    ax.axhline(loa_upper, color=RED, ls="--", lw=1.2,
               label=f"95% LoA = [{loa_lower:+.2f}, {loa_upper:+.2f}]")
    ax.axhline(loa_lower, color=RED, ls="--", lw=1.2)
    ax.axhline(0, color="#999", ls=":", lw=0.8)

    ax.set_xlabel("Mean of wrist PPG and chest ECG heart rate (bpm)", fontsize=11)
    ax.set_ylabel("PPG HR minus ECG HR (bpm)", fontsize=11)
    ax.set_title(f"Bland-Altman: wrist PPG vs chest ECG heart rate (WESAD)\n"
                 f"n = {n:,} windows, MAE = {mae:.2f} bpm, Pearson r = {pearson_r:+.3f}",
                 fontsize=12, fontweight="bold", pad=12)
    ax.legend(loc="upper right", fontsize=10, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_facecolor("#f8f9fa")

    ax.text(0.5, -0.18,
            "Each point is one thirty-second window. Positive values indicate that wrist PPG overestimates HR relative to chest ECG.",
            transform=ax.transAxes, ha="center", fontsize=9,
            color=MUTED, style="italic")

    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=140, facecolor="white", bbox_inches="tight")
    plt.close()
    print(f"Wrote {output}")
    print(f"  n     = {n}")
    print(f"  bias  = {bias:+.4f} bpm")
    print(f"  LoA   = [{loa_lower:+.4f}, {loa_upper:+.4f}] bpm")
    print(f"  MAE   = {mae:.4f} bpm")
    print(f"  r     = {pearson_r:+.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path,
                        help="Path to WESAD results JSON")
    parser.add_argument("--output", default=Path("paper/figures/fig1_bland_altman.png"),
                        type=Path, help="Output PNG path")
    args = parser.parse_args()
    ppg, ecg = load_paired_hr(args.input)
    bland_altman(ppg, ecg, args.output)


if __name__ == "__main__":
    main()
