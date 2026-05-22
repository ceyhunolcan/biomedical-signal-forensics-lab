"""Deep real-data validation on WESAD.

Runs five analyses on top of the basic real-data pilot:

  1. Cross-modality HR agreement (chest ECG vs wrist PPG) per subject and pooled
  2. Per-state within-subject paired comparisons (baseline vs stress)
  3. Three-way SQI agreement: in-house vs Orphanidou 2015 vs Sukor 2011
  4. Motion-vs-SQI confounding analysis
  5. SQI threshold recalibration experiment

Usage:
    python scripts/run_deep_real_analysis.py --dataset wesad --path /path/to/wesad
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.data.wesad_adapter import adapt_directory
from src.evaluation.deep_real_analysis import (
    compute_window_table, cross_modality_hr_agreement,
    per_state_comparison, three_way_sqi_agreement,
    motion_effect_analysis, recalibrate_inhouse_sqi,
)
from src.utils.logging import get_logger
from src.utils.paths import ensure_dir, resolve

log = get_logger("deep_real")


def _nan_safe(value):
    """Convert NaN/Inf to None so JSON serializes cleanly."""
    if value is None:
        return None
    if isinstance(value, float) and (value != value or value == float("inf") or value == float("-inf")):
        return None
    return value


def _result_to_dict(result):
    """Convert a dataclass result into a JSON-safe dict."""
    d = asdict(result)
    return {k: _nan_safe(v) for k, v in d.items()}


def main(dataset_path: Path, out_dir: Path) -> None:
    out_dir = ensure_dir(out_dir)

    log.info("Loading WESAD from %s …", dataset_path)
    daily_df, ecg_arr, ppg_arr, meta = adapt_directory(dataset_path)
    log.info("Subjects: %d, windows: %d", len(daily_df), len(meta))

    # Per-window table
    log.info("Computing per-window HR + SQI table…")
    window_df = compute_window_table(ecg_arr, ppg_arr, meta)
    window_df.to_csv(out_dir / "window_table.csv", index=False)
    log.info("Wrote per-window table (%d rows, %d columns) → window_table.csv",
             len(window_df), len(window_df.columns))

    summary = {"dataset": "wesad",
               "n_subjects": int(len(daily_df)),
               "n_windows": int(len(window_df))}

    # ------------------------------------------------------------------
    # 1. Cross-modality HR agreement
    # ------------------------------------------------------------------
    log.info("\n%s\nAnalysis 1: Cross-modality HR agreement (chest ECG vs wrist PPG)\n%s",
             "=" * 70, "=" * 70)
    overall_agreement = cross_modality_hr_agreement(window_df)
    log.info("  Overall (n=%d): MAE=%.2f bpm, bias=%.2f bpm, "
             "LoA=[%.2f, %.2f], Pearson r=%.3f (p=%.3g)",
             overall_agreement.n_windows,
             overall_agreement.mean_absolute_error_bpm,
             overall_agreement.bias_ppg_minus_ecg_bpm,
             overall_agreement.loa_lower_bpm, overall_agreement.loa_upper_bpm,
             overall_agreement.pearson_r, overall_agreement.pearson_p)
    log.info("  Fraction within 5 bpm: %.3f, within 10 bpm: %.3f",
             overall_agreement.fraction_within_5_bpm,
             overall_agreement.fraction_within_10_bpm)
    summary["hr_agreement_overall"] = _result_to_dict(overall_agreement)

    # Per-subject + per-state agreement
    per_subject_rows = []
    for subject_id, g in window_df.groupby("subject_id"):
        r = cross_modality_hr_agreement(g)
        d = _result_to_dict(r)
        d["subject_id"] = subject_id
        d["stratum"] = "all"
        per_subject_rows.append(d)
        for state, gs in g.groupby("label_name"):
            r = cross_modality_hr_agreement(gs)
            d = _result_to_dict(r)
            d["subject_id"] = subject_id
            d["stratum"] = state
            per_subject_rows.append(d)
    per_subject = pd.DataFrame(per_subject_rows)
    per_subject.to_csv(out_dir / "hr_agreement_per_subject_state.csv", index=False)
    log.info("Per-subject × per-state agreement:\n%s",
             per_subject[["subject_id", "stratum", "n_windows",
                          "mean_absolute_error_bpm", "fraction_within_5_bpm",
                          "pearson_r"]].to_string(index=False))

    # ------------------------------------------------------------------
    # 2. Per-state paired comparisons (within-subject)
    # ------------------------------------------------------------------
    log.info("\n%s\nAnalysis 2: Per-state comparisons (baseline vs stress)\n%s",
             "=" * 70, "=" * 70)
    state_cmp = per_state_comparison(window_df, "baseline", "stress")
    state_cmp.to_csv(out_dir / "per_state_baseline_vs_stress.csv", index=False)
    log.info("Within-subject ranksum stress vs baseline:\n%s",
             state_cmp[["subject_id", "metric", "baseline_n", "stress_n",
                        "baseline_mean", "stress_mean",
                        "delta_b_minus_a", "wilcoxon_p"]].to_string(index=False))

    # Also amusement comparison
    state_cmp_am = per_state_comparison(window_df, "baseline", "amusement")
    state_cmp_am.to_csv(out_dir / "per_state_baseline_vs_amusement.csv", index=False)

    # ------------------------------------------------------------------
    # 3. Three-way SQI agreement
    # ------------------------------------------------------------------
    log.info("\n%s\nAnalysis 3: Three-way SQI agreement (in-house vs Orphanidou vs Sukor)\n%s",
             "=" * 70, "=" * 70)
    three_way = three_way_sqi_agreement(window_df)
    log.info("  n_windows=%d", three_way.n_windows)
    log.info("  Pass rates: in-house=%.3f, Orphanidou=%.3f, Sukor=%.3f",
             three_way.inhouse_pass_rate, three_way.orphanidou_pass_rate,
             three_way.sukor_pass_rate)
    log.info("  Spearman ρ: in-house↔Orphanidou=%.3f, in-house↔Sukor=%.3f, "
             "Orphanidou↔Sukor=%.3f",
             three_way.spearman_inhouse_vs_orph,
             three_way.spearman_inhouse_vs_sukor,
             three_way.spearman_orph_vs_sukor)
    log.info("  Cohen's kappa: in-house↔Orphanidou=%.3f, in-house↔Sukor=%.3f, "
             "Orphanidou↔Sukor=%.3f",
             three_way.kappa_inhouse_vs_orph,
             three_way.kappa_inhouse_vs_sukor,
             three_way.kappa_orph_vs_sukor)
    log.info("  All three pass: %.3f; all three fail: %.3f",
             three_way.fraction_all_three_pass,
             three_way.fraction_all_three_fail)
    summary["three_way_sqi"] = _result_to_dict(three_way)

    # ------------------------------------------------------------------
    # 3b. Four-way SQI agreement (adds Elgendi 2016 as a third baseline)
    # ------------------------------------------------------------------
    log.info("\n%s\nAnalysis 3b: Four-way SQI agreement (adds Elgendi 2016)\n%s",
             "=" * 70, "=" * 70)
    from src.evaluation.deep_real_analysis import four_way_sqi_agreement
    four_way = four_way_sqi_agreement(window_df)
    log.info("  n_windows=%d", four_way.n_windows)
    log.info("  Pass rates: in-house=%.3f, Orphanidou=%.3f, Sukor=%.3f, Elgendi=%.3f",
             four_way.inhouse_pass_rate, four_way.orphanidou_pass_rate,
             four_way.sukor_pass_rate, four_way.elgendi_pass_rate)
    log.info("  Cohen's kappa, in-house vs published: Orph=%.3f, Sukor=%.3f, Elgendi=%.3f "
             "(median %.3f)",
             four_way.kappa_inhouse_vs_orph,
             four_way.kappa_inhouse_vs_sukor,
             four_way.kappa_inhouse_vs_elgendi,
             four_way.median_kappa_inhouse_vs_published)
    log.info("  Cohen's kappa, published vs published: Orph-Sukor=%.3f, Orph-Elgendi=%.3f, "
             "Sukor-Elgendi=%.3f (median %.3f)",
             four_way.kappa_orph_vs_sukor,
             four_way.kappa_orph_vs_elgendi,
             four_way.kappa_sukor_vs_elgendi,
             four_way.median_kappa_published_only)
    log.info("  All three published pass: %.3f; all three published fail: %.3f",
             four_way.fraction_all_published_pass,
             four_way.fraction_all_published_fail)
    log.info("  In-house passes when ALL three published baselines fail: %.3f",
             four_way.inhouse_passes_when_all_published_fail)
    summary["four_way_sqi"] = _result_to_dict(four_way)

    # ------------------------------------------------------------------
    # 4. Motion-vs-SQI
    # ------------------------------------------------------------------
    log.info("\n%s\nAnalysis 4: Motion-vs-SQI and motion-vs-HR-disagreement\n%s",
             "=" * 70, "=" * 70)
    motion = motion_effect_analysis(window_df)
    log.info("  Spearman motion vs in-house SQI: %.3f (expect <0: motion lowers SQI)",
             motion.spearman_motion_vs_inhouse_sqi)
    log.info("  Spearman motion vs |HR_PPG - HR_ECG|: %.3f (expect >0)",
             motion.spearman_motion_vs_hr_disagreement)
    log.info("  Spearman motion vs Orphanidou template corr: %.3f (expect <0)",
             motion.spearman_motion_vs_orphanidou_template_corr)
    log.info("  Mean |HR diff| low motion: %.2f bpm  /  high motion: %.2f bpm",
             motion.mean_hr_disagreement_low_motion,
             motion.mean_hr_disagreement_high_motion)
    summary["motion_effect"] = _result_to_dict(motion)

    # ------------------------------------------------------------------
    # 5. Recalibration experiment
    # ------------------------------------------------------------------
    log.info("\n%s\nAnalysis 5: In-house SQI threshold recalibration vs Orphanidou\n%s",
             "=" * 70, "=" * 70)
    recal = recalibrate_inhouse_sqi(window_df)
    log.info("  Original threshold: %.2f → kappa on holdout: %.3f (raw agreement: %.3f)",
             recal.original_threshold,
             recal.original_holdout_kappa_vs_orph,
             recal.original_holdout_agreement)
    log.info("  Recalibrated threshold: %.3f → kappa on holdout: %.3f (raw agreement: %.3f)",
             recal.recalibrated_threshold,
             recal.recalibrated_holdout_kappa_vs_orph,
             recal.recalibrated_holdout_agreement)
    delta_kappa = (recal.recalibrated_holdout_kappa_vs_orph -
                   recal.original_holdout_kappa_vs_orph)
    log.info("  Δ kappa: %+.3f (positive = recalibration helped)", delta_kappa)
    summary["recalibration"] = _result_to_dict(recal)

    # ------------------------------------------------------------------
    # Write summary JSON
    # ------------------------------------------------------------------
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    log.info("\nWrote summary → %s", out_dir / "summary.json")

    # ------------------------------------------------------------------
    # Generate publication figures
    # ------------------------------------------------------------------
    log.info("\nGenerating publication figures…")
    from src.reports.real_data_figures import make_all_figures
    fig_paths = make_all_figures(window_df, three_way, out_dir / "figures")
    for name, path in fig_paths.items():
        log.info("  %s → %s", name, path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["wesad"], default="wesad")
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path("results/real_data/wesad_deep"))
    args = parser.parse_args()
    main(args.path, args.out)
