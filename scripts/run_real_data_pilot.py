"""Run the audit framework on a downloaded WESAD dataset.

Usage:
    # First, download WESAD from
    # https://archive.ics.uci.edu/dataset/465/wesad
    # and unzip so you have a directory layout:
    #   /path/to/wesad/S2/S2.pkl
    #   /path/to/wesad/S3/S3.pkl
    #   ...
    python scripts/run_real_data_pilot.py --dataset wesad --path /path/to/wesad

What this script produces:
    results/real_data/wesad/
        daily_summary.csv       (one row per subject)
        windows_meta.csv        (one row per extracted ECG/PPG window)
        signal_quality.csv      (in-house SQI per window)
        orphanidou_baseline.csv (head-to-head with Orphanidou 2015)
        report.md               (human-readable summary)

The pilot does not compute trust scores, fairness audits, or
test-retest reliability on WESAD: those analyses require multi-day longitudinal
data per participant, which WESAD does not provide. What we get is per-window
signal quality, artifact burden, and an agreement comparison against the
published baseline on real ECG and real PPG.

Other real datasets can be added under `src/data/<dataset>_adapter.py` using
the same pattern.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.utils.logging import get_logger
from src.utils.paths import ensure_dir

log = get_logger("real_data_pilot")


def run_wesad_pilot(wesad_dir: Path, out_dir: Path) -> dict:
    """Load WESAD, run the per-window SQI + Orphanidou baseline, write outputs."""
    from src.data.wesad_adapter import adapt_directory
    from src.signals.signal_quality import per_window_sqi
    from src.signals.orphanidou_sqi import head_to_head

    log.info("Loading WESAD from %s …", wesad_dir)
    daily_df, ecg_arr, ppg_arr, meta = adapt_directory(wesad_dir)

    out_dir = ensure_dir(out_dir)
    daily_df.to_csv(out_dir / "daily_summary.csv", index=False)
    meta.to_csv(out_dir / "windows_meta.csv", index=False)
    log.info("Wrote %d daily-summary rows and %d windows.",
             len(daily_df), len(meta))

    summary: dict = {
        "dataset": "wesad",
        "n_subjects": int(len(daily_df)),
        "n_windows": int(len(meta)),
    }

    if len(meta) == 0:
        log.warning("No windows extracted; skipping SQI and baseline.")
        summary["sqi_computed"] = False
        return summary

    log.info("Computing in-house per-window SQI on %d windows …", len(meta))
    sqi_df = per_window_sqi(ecg_arr, ppg_arr,
                            ecg_fs=700,    # WESAD chest sampling rate
                            ppg_fs=64)     # WESAD wrist BVP sampling rate
    # per_window_sqi adds its own window_idx column; drop it before concat so
    # the meta's window_idx (which carries the pooled cross-subject id) wins.
    if "window_idx" in sqi_df.columns:
        sqi_df = sqi_df.drop(columns=["window_idx"])
    sqi_df = pd.concat([meta.reset_index(drop=True), sqi_df.reset_index(drop=True)],
                       axis=1)
    sqi_df.to_csv(out_dir / "signal_quality.csv", index=False)
    summary["sqi_computed"] = True
    summary["in_house_mean_ppg_sqi"] = float(sqi_df["ppg_sqi"].mean())
    summary["in_house_mean_ecg_sqi"] = float(sqi_df["ecg_sqi"].mean())

    log.info("Running Orphanidou 2015 head-to-head on PPG …")
    agreement = head_to_head(ppg_arr, sqi_df["ppg_sqi"].to_numpy(),
                             fs=64, modality="ppg")
    bench = pd.DataFrame([{
        "n_windows": agreement.n_windows,
        "in_house_mean_sqi": round(agreement.in_house_mean, 4),
        "orphanidou_acceptable_frac": round(agreement.orphanidou_acceptable_frac, 4),
        "spearman_with_template_corr": round(agreement.spearman_with_continuous, 4)
            if agreement.spearman_with_continuous == agreement.spearman_with_continuous
            else None,
        "point_biserial_with_binary": round(agreement.point_biserial_with_binary, 4)
            if agreement.point_biserial_with_binary == agreement.point_biserial_with_binary
            else None,
        **agreement.crosstab,
    }])
    bench.to_csv(out_dir / "orphanidou_baseline.csv", index=False)
    summary["orphanidou_spearman"] = (
        float(agreement.spearman_with_continuous)
        if agreement.spearman_with_continuous == agreement.spearman_with_continuous
        else None
    )

    # Per-state breakdown: do labeled stress windows have lower SQI?
    if "label_name" in sqi_df.columns:
        by_state = sqi_df.groupby("label_name").agg(
            n=("window_idx", "count"),
            ecg_sqi_mean=("ecg_sqi", "mean"),
            ppg_sqi_mean=("ppg_sqi", "mean"),
            ppg_motion_mean=("ppg_motion", "mean"),
        ).reset_index()
        by_state.to_csv(out_dir / "sqi_by_state.csv", index=False)
        log.info("Per-state SQI breakdown:\n%s",
                 by_state.to_string(index=False))
        summary["per_state_breakdown"] = by_state.to_dict("records")

    return summary


def write_report(summary: dict, out_dir: Path) -> Path:
    """Compose a short markdown summary of the pilot."""
    lines = [
        "# Real-data pilot: WESAD",
        "",
        "> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.",
        "",
        f"- Dataset: **{summary.get('dataset', '?')}**",
        f"- Subjects: **{summary.get('n_subjects', 0)}**",
        f"- Windows extracted: **{summary.get('n_windows', 0)}**",
        "",
    ]
    if summary.get("sqi_computed"):
        lines.extend([
            "## In-house SQI vs Orphanidou (2015)",
            "",
            f"- In-house mean PPG SQI: **{summary.get('in_house_mean_ppg_sqi'):.3f}**",
            f"- In-house mean ECG SQI: **{summary.get('in_house_mean_ecg_sqi'):.3f}**",
            f"- Spearman ρ vs Orphanidou template correlation: "
            f"**{summary.get('orphanidou_spearman')}**",
            "",
        ])
    if summary.get("per_state_breakdown"):
        lines.extend([
            "## SQI by labeled state",
            "",
            "| State | n | ECG SQI | PPG SQI | PPG motion |",
            "|---|---|---|---|---|",
        ])
        for row in summary["per_state_breakdown"]:
            lines.append(
                f"| {row['label_name']} | {int(row['n'])} | "
                f"{row['ecg_sqi_mean']:.3f} | {row['ppg_sqi_mean']:.3f} | "
                f"{row['ppg_motion_mean']:.3f} |"
            )
        lines.append("")
    lines.extend([
        "## What this pilot does and doesn't tell us",
        "",
        "WESAD has ~60 minutes per subject and no multi-day longitudinal "
        "data. We can therefore validate per-window signal quality and "
        "artifact-burden estimates, but not test-retest reliability, "
        "missingness dynamics, weekly reproducibility, or device-bias "
        "comparisons across calendar time. For those analyses, MIMIC-PERform "
        "or an AppleWatch-MIMIC subset is a better fit.",
        "",
        "Numbers above were produced by `scripts/run_real_data_pilot.py "
        "--dataset wesad`. CSVs are alongside this report.",
    ])
    p = out_dir / "report.md"
    p.write_text("\n".join(lines))
    log.info("Wrote pilot report → %s", p)
    return p


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["wesad"], default="wesad",
                        help="Which dataset adapter to use.")
    parser.add_argument("--path", required=True, type=Path,
                        help="Path to the unpacked dataset directory.")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output directory (defaults to results/real_data/<dataset>/).")
    args = parser.parse_args()

    if args.out is None:
        args.out = Path("results/real_data") / args.dataset

    if args.dataset == "wesad":
        summary = run_wesad_pilot(args.path, args.out)
    else:
        raise NotImplementedError(args.dataset)

    write_report(summary, args.out)


if __name__ == "__main__":
    main()
