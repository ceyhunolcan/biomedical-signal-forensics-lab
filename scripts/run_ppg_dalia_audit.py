"""External validation: run the multi-baseline SQI audit on PPG-DaLiA.

Reuses the exact analysis functions from evaluation.deep_real_analysis (the
same ones run on WESAD), but with the PPG-DaLiA adapter. Two WESAD-specific
analyses are skipped:

  - per_state_comparison: WESAD's labeled states (baseline / stress /
    amusement) and PPG-DaLiA's activities (sitting / cycling / walking ...)
    are not comparable, so paired state contrasts are not meaningful.
  - recalibrate_inhouse_sqi: the WESAD recalibration result is the negative
    finding we already report (Delta kappa ~ 0 at n=15); redoing the same
    recalibration on a second n=15 cohort would not add information.

Output structure mirrors results/real_data/wesad_deep/ for direct comparison.

Usage:
    python scripts/run_ppg_dalia_audit.py --data-dir /path/to/PPG_FieldStudy
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.data.ppg_dalia_adapter import adapt_directory
from biomedical_signal_forensics_lab.evaluation.deep_real_analysis import (
    compute_window_table,
    cross_modality_hr_agreement,
    three_way_sqi_agreement,
    motion_effect_analysis,
)
from biomedical_signal_forensics_lab.utils.logging import get_logger
from biomedical_signal_forensics_lab.utils.paths import ensure_dir, resolve

log = get_logger("ppg_dalia_audit")


def _nan_safe(value):
    """Convert NaN / +-Inf to None for JSON."""
    if value is None:
        return None
    if isinstance(value, float) and (
        value != value or value == float("inf") or value == float("-inf")
    ):
        return None
    return value


def _result_to_dict(result):
    """Convert a dataclass result (or plain dict) into a JSON-safe dict."""
    if is_dataclass(result):
        d = asdict(result)
    elif isinstance(result, dict):
        d = result
    else:
        return _nan_safe(result)
    return {k: (_result_to_dict(v) if (is_dataclass(v) or isinstance(v, dict))
                else _nan_safe(v))
            for k, v in d.items()}


def _format_summary(results: dict) -> str:
    """Pretty-print the headline numbers for stdout."""
    lines = [
        "",
        "=== PPG-DaLiA cross-method audit ===",
        f"  Subjects:  {results.get('n_subjects', 'n/a')}",
        f"  Windows:   {results.get('n_windows', 'n/a')}",
    ]
    hr = results.get("hr_agreement") or {}
    if hr:
        lines.append("  HR agreement (PPG vs ECG):")
        for k, label in [
            ("bias_bpm", "  bias"),
            ("loa_lower_bpm", "  LoA lower"),
            ("loa_upper_bpm", "  LoA upper"),
            ("mae_bpm", "  MAE"),
            ("pearson_r", "  Pearson r"),
        ]:
            v = hr.get(k)
            if isinstance(v, (int, float)):
                lines.append(f"      {label:18s} {v:+.3f}")
    sqi = results.get("sqi_agreement") or {}
    if sqi:
        lines.append("  Cross-method SQI agreement:")
        for k, v in sqi.items():
            if isinstance(v, (int, float)):
                lines.append(f"      {k:40s} {v:+.4f}")
    return "\n".join(lines)


def _print_wesad_comparison(ppg_dalia: dict, wesad_path: Path) -> None:
    if not wesad_path.exists():
        log.info("(No WESAD summary at %s; skipping side-by-side.)", wesad_path)
        return
    with wesad_path.open() as f:
        wesad = json.load(f)
    print("\n=== WESAD vs PPG-DaLiA ===")
    for key in ("hr_agreement", "sqi_agreement", "motion_effect"):
        print(f"\n  {key}:")
        w = wesad.get(key) if isinstance(wesad.get(key), dict) else {}
        p = ppg_dalia.get(key) if isinstance(ppg_dalia.get(key), dict) else {}
        keys = sorted(set(w.keys()) | set(p.keys()))
        for k in keys:
            wv = w.get(k)
            pv = p.get(k)
            wv_s = f"{wv:+.3f}" if isinstance(wv, (int, float)) else str(wv)
            pv_s = f"{pv:+.3f}" if isinstance(pv, (int, float)) else str(pv)
            print(f"    {k:40s} WESAD: {wv_s:>10}   PPG-DaLiA: {pv_s:>10}")


def main(dataset_path: Path, out_dir: Path, wesad_summary: Path) -> None:
    out_dir = ensure_dir(out_dir)

    log.info("Loading PPG-DaLiA from %s ...", dataset_path)
    daily_df, ecg_arr, ppg_arr, meta = adapt_directory(dataset_path)
    log.info("Subjects: %d, windows: %d", len(daily_df), len(meta))
    if len(meta) == 0:
        log.error("No windows extracted; aborting.")
        sys.exit(1)

    daily_df.to_csv(out_dir / "daily_summary.csv", index=False)
    meta.to_csv(out_dir / "window_meta.csv", index=False)

    log.info("Computing per-window SQI/HR table ...")
    window_table = compute_window_table(ecg_arr, ppg_arr, meta)
    window_table.to_csv(out_dir / "window_table.csv", index=False)
    log.info("Window table: %d rows -> window_table.csv", len(window_table))

    results: dict = {
        "dataset": "PPG-DaLiA",
        "n_subjects": int(meta["subject_id"].nunique()),
        "n_windows": int(len(meta)),
    }

    log.info("Cross-modality HR agreement ...")
    results["hr_agreement"] = _result_to_dict(
        cross_modality_hr_agreement(window_table)
    )

    log.info("Three-way SQI agreement (in-house vs Orphanidou vs Sukor) ...")
    results["sqi_agreement"] = _result_to_dict(
        three_way_sqi_agreement(window_table)
    )

    log.info("Motion-vs-SQI effect ...")
    results["motion_effect"] = _result_to_dict(
        motion_effect_analysis(window_table)
    )

    with (out_dir / "summary.json").open("w") as f:
        json.dump(results, f, indent=2)
    log.info("Wrote summary -> %s", out_dir / "summary.json")

    print(_format_summary(results))
    _print_wesad_comparison(results, wesad_summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to PPG-DaLiA's PPG_FieldStudy/ directory (containing S1/, S2/, ...)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("results/real_data/ppg_dalia"),
        help="Output directory (default: results/real_data/ppg_dalia)",
    )
    parser.add_argument(
        "--wesad-summary",
        type=Path,
        default=Path("results/real_data/wesad_deep/summary.json"),
        help="Path to WESAD summary.json for side-by-side comparison.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.data_dir, args.out_dir, args.wesad_summary)
