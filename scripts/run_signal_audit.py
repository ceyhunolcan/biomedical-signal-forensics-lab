"""Run the artifact / reliability / confounding audit on the synthetic dataset.

Includes the publication-level upgrades:
  - causal-adjusted confounding (AIPW) alongside the screening correlations
  - change-point scan per participant (firmware-drift surveillance)
  - stratified fairness audit by device_type and skin_tone_proxy
  - learned trust-score weights tied to weekly HRV reproducibility

Usage: python scripts/run_signal_audit.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.artifacts.artifact_classifier import evaluate_batch
from src.confounding import environmental_confounding, missingness_dynamics
from src.confounding.causal_inference import screening_vs_adjusted_table
from src.reliability.biomarker_trust_score import DigitalBiomarkerTrustScore
from src.reliability.change_point import scan_cohort
from src.reliability.device_bias import per_column_bias
from src.reliability.fairness_audit import fairness_audit, disparity_summary
from src.reliability.test_retest import cohort_test_retest_table
from src.reliability.weight_optimization import learn_weights, sensitivity_table
from src.reports.figure_builder import fairness_forest_plot
from src.signals.orphanidou_sqi import head_to_head as orph_head_to_head
from src.signals.signal_quality import per_window_sqi
from src.utils.config import load_yaml
from src.utils.logging import get_logger
from src.utils.paths import ensure_dir, resolve

log = get_logger("audit")


def main() -> None:
    cfg = load_yaml("configs/default.yaml")
    df = pd.read_csv(resolve(cfg.paths.synthetic_csv))
    out_dir = ensure_dir("results/tables")
    fig_dir = ensure_dir("results/figures")

    log.info("Artifact evaluation on signal windows…")
    windows_path = resolve(cfg.paths.synthetic_windows)
    if windows_path.exists():
        arrays = np.load(windows_path)
        artifact_df = evaluate_batch(arrays["ppg"], int(cfg.cohort.ppg_sample_rate_hz))
        artifact_df.to_csv(out_dir / "artifact_findings.csv", index=False)
        log.info("Saved artifact_findings.csv (rows=%d)", len(artifact_df))

    log.info("Confounding (screening correlations)…")
    corr = environmental_confounding.correlation_table(df)
    corr.to_csv(out_dir / "confounding_correlations.csv", index=False)

    log.info("Confounding (causal-adjusted AIPW): this can take a minute…")
    pairs = [("heat_index", "hrv_rmssd"),
             ("heat_index", "sleep_efficiency"),
             ("aqi", "sleep_efficiency"),
             ("active_minutes", "hrv_rmssd")]
    adjusted = screening_vs_adjusted_table(df, pairs=pairs, learner="linear")
    adjusted.to_csv(out_dir / "confounding_adjusted.csv", index=False)
    log.info("AIPW table:\n%s", adjusted.to_string(index=False))

    log.info("Missingness summary…")
    missingness_dynamics.per_participant_summary(df).to_csv(
        out_dir / "missingness_summary.csv", index=False
    )
    missingness_dynamics.state_dependent_missingness(df).to_csv(
        out_dir / "state_dependent_missingness.csv", index=False
    )

    log.info("Device bias…")
    per_column_bias(df, ["resting_hr", "hrv_rmssd", "sleep_efficiency"]).to_csv(
        out_dir / "device_bias.csv", index=False
    )

    log.info("Cohort trust scores…")
    scorer = DigitalBiomarkerTrustScore()
    trust_df = scorer.cohort_scores(df)
    trust_df.to_csv(out_dir / "trust_scores.csv", index=False)
    log.info("Mean overall trust score: %.2f", trust_df["overall_trust_score"].mean())

    log.info("Bootstrap test-retest reliability (week-pair design)…")
    tr_table = cohort_test_retest_table(
        df, ["resting_hr", "hrv_rmssd", "sleep_efficiency", "sleep_duration"],
        method="week_pair", n_bootstrap=300,
    )
    tr_table.to_csv(out_dir / "test_retest_bootstrap.csv", index=False)
    log.info("Test-retest:\n%s", tr_table.to_string(index=False))

    log.info("Method comparison: ICC(2,1) days-as-raters vs week-pair r…")
    from src.reliability.intraclass_correlation import compare_to_test_retest
    icc_cmp = compare_to_test_retest(
        df, ["resting_hr", "hrv_rmssd", "sleep_efficiency", "sleep_duration"],
        n_bootstrap=200,
    )
    icc_cmp.to_csv(out_dir / "icc_vs_test_retest.csv", index=False)
    log.info("ICC vs week-pair:\n%s", icc_cmp.to_string(index=False))

    log.info("Baseline comparison: in-house SQI vs Orphanidou 2015…")
    if windows_path.exists():
        ppg_arr = arrays["ppg"]
        # Recompute per-window in-house PPG SQI on the same windows
        sqi_df = per_window_sqi(arrays["ecg"], ppg_arr,
                                int(cfg.cohort.ecg_sample_rate_hz),
                                int(cfg.cohort.ppg_sample_rate_hz))
        in_house_ppg = sqi_df["ppg_sqi"].to_numpy()
        summary = orph_head_to_head(
            ppg_arr, in_house_ppg,
            fs=int(cfg.cohort.ppg_sample_rate_hz), modality="ppg",
        )
        bench = pd.DataFrame([{
            "n_windows": summary.n_windows,
            "in_house_mean_sqi": round(summary.in_house_mean, 4),
            "orphanidou_acceptable_frac": round(summary.orphanidou_acceptable_frac, 4),
            "spearman_with_template_corr": round(summary.spearman_with_continuous, 4),
            "point_biserial_with_binary": round(summary.point_biserial_with_binary, 4),
            **summary.crosstab,
        }])
        bench.to_csv(out_dir / "baseline_comparison_orphanidou.csv", index=False)
        log.info("Orphanidou agreement: Spearman=%.3f, point-biserial=%.3f",
                 summary.spearman_with_continuous, summary.point_biserial_with_binary)

    log.info("Change-point scan (resting_hr per participant)…")
    cps_hr = scan_cohort(df, metric="resting_hr", method="binary_segmentation")
    cps_hr.to_csv(out_dir / "change_points_resting_hr.csv", index=False)
    log.info("Found %d change-points in resting_hr across the cohort", len(cps_hr))

    log.info("Stratified fairness audit by device_type…")
    fair_dev = fairness_audit(df, stratify_by="device_type", n_bootstrap=50)
    fair_dev.to_csv(out_dir / "fairness_by_device.csv", index=False)
    fairness_forest_plot(fair_dev, out=str(fig_dir / "fairness_forest_device.png"))
    disp_dev = disparity_summary(fair_dev)
    disp_dev.to_csv(out_dir / "fairness_disparity_device.csv", index=False)

    log.info("Stratified fairness audit by skin_tone_proxy…")
    fair_skin = fairness_audit(df, stratify_by="skin_tone_proxy", n_bootstrap=50)
    fair_skin.to_csv(out_dir / "fairness_by_skin_tone.csv", index=False)
    fairness_forest_plot(fair_skin, out=str(fig_dir / "fairness_forest_skin_tone.png"))
    disp_skin = disparity_summary(fair_skin)
    disp_skin.to_csv(out_dir / "fairness_disparity_skin_tone.csv", index=False)

    log.info("Learning DBTS weights tied to weekly HRV reproducibility…")
    learned = learn_weights(df, target_metric="hrv_rmssd",
                            n_random=300, n_refine=5, holdout_fraction=0.3)
    with open(out_dir / "learned_weights.json", "w") as f:
        json.dump({
            "weights": learned.weights,
            "spearman_train": learned.spearman_train,
            "spearman_holdout": learned.spearman_holdout,
            "n_train": learned.n_train,
            "n_holdout": learned.n_holdout,
            "n_evaluated": learned.n_evaluated,
            "notes": learned.notes,
        }, f, indent=2)
    sens = sensitivity_table(df, learned)
    sens.to_csv(out_dir / "weight_sensitivity.csv", index=False)
    log.info("Audit complete. Outputs under results/tables/ and results/figures/.")


if __name__ == "__main__":
    main()
