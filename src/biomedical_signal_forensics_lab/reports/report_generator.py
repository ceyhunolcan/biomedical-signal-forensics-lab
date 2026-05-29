"""Top-level audit report generator.

Produces results/reports/signal_forensics_report.md plus a set of figures.
Designed to be readable as a standalone document.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..confounding import environmental_confounding, missingness_dynamics
from ..reliability.biomarker_trust_score import DigitalBiomarkerTrustScore
from ..reliability.device_bias import per_column_bias, bias_severity
from ..utils.config import load_yaml
from ..utils.logging import get_logger
from ..utils.paths import ensure_dir, resolve
from . import figure_builder, trust_report

log = get_logger("report")

DISCLAIMER = (
    "> **Research prototype only. Not medical advice, diagnosis, treatment, "
    "or a medical device. All outputs are signal-quality estimates and "
    "methodological recommendations, not clinical findings.**"
)


def _headline(df: pd.DataFrame, trust_df: pd.DataFrame) -> str:
    n_p = df["participant_id"].nunique()
    n_d = df["date"].nunique()
    mean_trust = float(trust_df["overall_trust_score"].mean())
    cat_low = int((trust_df["overall_trust_score"] < 40).sum())
    miss_rate = float(df["missing_wearable_flag"].mean())
    cat_label = (
        "high" if mean_trust >= 80 else
        "moderate" if mean_trust >= 60 else
        "low" if mean_trust >= 40 else "unreliable"
    )
    return (
        f"Cohort: **{n_p} participants** over **{n_d} days**.\n\n"
        f"- Mean Digital Biomarker Trust Score: **{mean_trust:.1f} ({cat_label})**\n"
        f"- Participants with trust score < 40: **{cat_low}** "
        f"({cat_low / n_p * 100:.1f}%)\n"
        f"- Overall missingness rate: **{miss_rate * 100:.1f}%**\n"
    )


def _confounding_section(df: pd.DataFrame) -> str:
    corr = environmental_confounding.correlation_table(df)
    if corr.empty:
        return "No environmental columns available to test."
    lines = ["| Environmental variable | Biomarker | Pearson r | n |",
             "|---|---|---|---|"]
    for _, row in corr.head(6).iterrows():
        lines.append(
            f"| {row['environmental_var']} | {row['biomarker']} | "
            f"{row['pearson_r']:+.3f} | {int(row['n'])} |"
        )
    top = environmental_confounding.top_confounder(corr)
    if top:
        lines.append(
            f"\nTop confounding pair: **{top['environmental_var']} ↔ "
            f"{top['biomarker']}**, r = {top['pearson_r']:+.3f}."
        )
    return "\n".join(lines)


def _device_bias_section(df: pd.DataFrame) -> str:
    bias = per_column_bias(df, columns=["resting_hr", "hrv_rmssd", "sleep_efficiency"])
    if bias.empty:
        return "No device column available."
    sev = bias_severity(bias)
    lines = ["| Device | Reference | Column | Mean diff | n |",
             "|---|---|---|---|---|"]
    for _, row in bias.iterrows():
        lines.append(
            f"| {row['device']} | {row['reference']} | {row['column']} | "
            f"{row['mean_diff']:+.2f} | {int(row['n_obs'])} |"
        )
    lines.append(f"\nAggregate device-bias severity: **{sev:.2f}** (0 = none, 1 = severe).")
    return "\n".join(lines)


def _missingness_section(df: pd.DataFrame) -> str:
    summary = missingness_dynamics.per_participant_summary(df)
    if summary.empty:
        return "No missingness data."
    state = missingness_dynamics.state_dependent_missingness(df)
    lines = [
        f"- Median per-participant missingness: "
        f"**{summary['miss_rate'].median():.2%}**",
        f"- Max consecutive missing days observed: "
        f"**{int(summary['max_consecutive_missing'].max())}**",
        "",
        "State-dependence of missingness:",
        "",
        "| State variable | r with missing-flag |",
        "|---|---|",
    ]
    for _, row in state.iterrows():
        r = row["miss_correlation_r"]
        lines.append(f"| {row['state']} | {r:+.3f} |" if not np.isnan(r)
                     else f"| {row['state']} | n/a |")
    return "\n".join(lines)


def _recommendations(df: pd.DataFrame, trust_df: pd.DataFrame) -> str:
    miss_rate = float(df["missing_wearable_flag"].mean())
    high_motion_frac = float((df["active_minutes"] > 120).mean())
    low_trust_frac = float((trust_df["overall_trust_score"] < 40).mean())
    bullets = []
    if miss_rate > 0.1:
        bullets.append(
            "Report missingness explicitly. Consider sensitivity analyses that "
            "compare results with and without participants above the 75th-percentile "
            "missingness rate."
        )
    if high_motion_frac > 0.2:
        bullets.append(
            "Exclude or down-weight participant-days with active_minutes > 120 "
            "when computing PPG-derived metrics, since artifact burden in this "
            "synthetic cohort scales with activity."
        )
    if low_trust_frac > 0.1:
        bullets.append(
            "Stratify analyses by Digital Biomarker Trust Score category and "
            "report whether effects survive restriction to the high/moderate strata."
        )
    bullets.append(
        "Pre-register the trust-score threshold used for inclusion. Defaults are "
        "documented in `configs/reliability.yaml`."
    )
    bullets.append(
        "Stratify by device_type when reporting any biomarker that the bias "
        "section above flags. Use device_A as the reference unless you have "
        "domain reasons to choose otherwise."
    )
    return "\n".join(f"- {b}" for b in bullets)


def _test_retest_section(df: pd.DataFrame) -> str:
    """Bootstrap test-retest table for the four most-watched daily metrics."""
    from ..reliability.test_retest import cohort_test_retest_table
    metrics = [m for m in ("resting_hr", "hrv_rmssd", "sleep_efficiency",
                            "sleep_duration") if m in df.columns]
    if not metrics:
        return "_No metrics available for test-retest._"
    table = cohort_test_retest_table(df, metrics, method="week_pair",
                                     n_bootstrap=300)
    if table.empty:
        return "_Could not compute test-retest (need ≥4 weeks of data per participant)._"
    lines = [
        "Week-pair Pearson correlation, pooled across all participants who "
        "contributed at least 4 weeks of data. 95% CIs come from a "
        "participant-level cluster bootstrap (n=300 resamples).",
        "",
        "| Metric | Test-retest r | 95% CI | Participants | Week pairs |",
        "|---|---|---|---|---|",
    ]
    for _, row in table.iterrows():
        ci = (f"[{row['ci_low']:+.3f}, {row['ci_high']:+.3f}]"
              if row['ci_low'] is not None else "n/a")
        pe = f"{row['point_estimate']:+.3f}" if row['point_estimate'] is not None else "n/a"
        lines.append(
            f"| {row['metric']} | {pe} | {ci} | "
            f"{int(row['n_participants'])} | {int(row['n_pairs'])} |"
        )
    return "\n".join(lines)


def _icc_comparison_section() -> str:
    """Pull the precomputed ICC vs test-retest comparison CSV.

    The framework uses ICC(2,1) with calendar days as 'raters', which is an
    unconventional design. This section runs the unconventional ICC alongside
    the proper bootstrap week-pair test-retest correlation and lets the
    reader see how they agree.
    """
    from ..utils.paths import resolve
    p = resolve("results/tables/icc_vs_test_retest.csv")
    if not p.exists():
        return ("_Method comparison not yet computed. Run "
                "`scripts/run_signal_audit.py` to populate this section._")
    try:
        cmp = pd.read_csv(p)
        if cmp.empty:
            raise ValueError("empty ICC comparison CSV")
        required = ["metric", "icc_days_as_raters", "week_pair_r",
                    "week_pair_ci_low", "week_pair_ci_high"]
        missing = [c for c in required if c not in cmp.columns]
        if missing:
            raise KeyError(f"missing columns: {missing}")
    except Exception as exc:  # noqa: BLE001
        return (f"_ICC comparison CSV present but unreadable "
                f"(`{exc}`). Re-run `scripts/run_signal_audit.py` to refresh._")
    lines = [
        "ICC(2,1) with calendar days as 'raters' is mathematically unusual: "
        "the classical Shrout and Fleiss (1979) ICC assumes a small fixed "
        "set of human raters per subject. Substituting daily measurements is "
        "defensible if the two methods rank metrics consistently and the ICC "
        "is monotonically related to a proper test-retest correlation. This "
        "table runs both side by side. The unconventional ICC is uniformly "
        "more conservative because it counts within-week noise as rater "
        "disagreement; clinical papers should report the bootstrap week-pair "
        "r as the headline reliability statistic.",
        "",
        "| Metric | ICC(2,1) days as raters | Week-pair r | 95% CI | n participants |",
        "|---|---|---|---|---|",
    ]
    for _, row in cmp.iterrows():
        icc = (f"{row['icc_days_as_raters']:+.3f}"
               if pd.notna(row['icc_days_as_raters']) else "n/a")
        wp = (f"{row['week_pair_r']:+.3f}"
              if pd.notna(row['week_pair_r']) else "n/a")
        if pd.notna(row['week_pair_ci_low']) and pd.notna(row['week_pair_ci_high']):
            ci = f"[{row['week_pair_ci_low']:+.3f}, {row['week_pair_ci_high']:+.3f}]"
        else:
            ci = "n/a"
        n_pid = int(row.get('n_participants_week_pair', 0) or 0)
        lines.append(f"| {row['metric']} | {icc} | {wp} | {ci} | {n_pid} |")
    return "\n".join(lines)


def _orphanidou_comparison_section() -> str:
    """Pull the precomputed baseline-comparison CSV if it exists."""
    from ..utils.paths import resolve
    p = resolve("results/tables/baseline_comparison_orphanidou.csv")
    if not p.exists():
        return ("_Baseline comparison not yet computed. Run "
                "`scripts/run_signal_audit.py` to populate this section._")
    try:
        bench = pd.read_csv(p)
        if bench.empty:
            raise ValueError("empty baseline-comparison CSV")
        bench = bench.iloc[0]
        required = ["n_windows", "in_house_mean_sqi", "orphanidou_acceptable_frac",
                    "spearman_with_template_corr", "point_biserial_with_binary",
                    "both_pass", "both_fail",
                    "inhouse_pass_orph_fail", "inhouse_fail_orph_pass"]
        missing = [c for c in required if c not in bench.index]
        if missing:
            raise KeyError(f"missing columns: {missing}")
    except Exception as exc:  # noqa: BLE001
        return (f"_Baseline comparison CSV present but unreadable "
                f"(`{exc}`). Re-run `scripts/run_signal_audit.py` to refresh._")
    lines = [
        "Head-to-head agreement between the in-house per-window PPG SQI and "
        "the published template-matching rules of Orphanidou et al. (2015). "
        "The two methods measure related but not identical things, so perfect "
        "agreement is not expected. A strong rank correlation (Spearman ≥ 0.7) "
        "supports the in-house SQI as a faithful continuous version of the "
        "published binary rule set.",
        "",
        f"- Windows compared: **{int(bench['n_windows'])}**",
        f"- In-house mean PPG SQI: **{bench['in_house_mean_sqi']:.3f}**",
        f"- Orphanidou acceptable fraction: **{bench['orphanidou_acceptable_frac']:.3f}**",
        f"- Spearman ρ (in-house continuous vs Orphanidou template correlation): "
        f"**{bench['spearman_with_template_corr']:.3f}**",
        f"- Point-biserial r (in-house continuous vs Orphanidou pass/fail): "
        f"**{bench['point_biserial_with_binary']:.3f}**",
        "",
        f"Crosstab at in-house threshold 0.7: "
        f"both pass={int(bench['both_pass'])}, both fail={int(bench['both_fail'])}, "
        f"in-house pass / Orphanidou fail={int(bench['inhouse_pass_orph_fail'])}, "
        f"in-house fail / Orphanidou pass={int(bench['inhouse_fail_orph_pass'])}.",
    ]
    return "\n".join(lines)


def _causal_section(df: pd.DataFrame) -> str:
    """Screening correlations vs causal-adjusted AIPW estimates."""
    from ..confounding.causal_inference import screening_vs_adjusted_table
    pairs = [("heat_index", "hrv_rmssd"),
             ("heat_index", "sleep_efficiency"),
             ("aqi", "sleep_efficiency"),
             ("active_minutes", "hrv_rmssd")]
    table = screening_vs_adjusted_table(df, pairs=pairs)
    if table.empty:
        return "_No pairs available for causal estimation._"
    lines = [
        "Screening correlations can overstate confounding when other covariates "
        "are doing the work. The AIPW (doubly-robust) column adjusts for the "
        "covariate set chosen by the project DAG (or a sensible default when "
        "the back-door set is empty). 95% CIs come from a participant-level "
        "bootstrap.",
        "",
        "| Treatment | Outcome | Screening r | AIPW estimate | 95% CI |",
        "|---|---|---|---|---|",
    ]
    for _, row in table.iterrows():
        ci = (f"[{row['ci_low']:+.3f}, {row['ci_high']:+.3f}]"
              if row['ci_low'] is not None and row['ci_high'] is not None else "n/a")
        est = f"{row['aipw_estimate']:+.3f}" if row['aipw_estimate'] is not None else "n/a"
        lines.append(
            f"| {row['treatment']} | {row['outcome']} | "
            f"{row['screening_r']:+.3f} | {est} | {ci} |"
        )
    return "\n".join(lines)


def _change_point_section(df: pd.DataFrame) -> str:
    """Per-participant change-point scan on resting heart rate."""
    from ..reliability.change_point import scan_cohort
    cps = scan_cohort(df, metric="resting_hr", method="binary_segmentation")
    # filter to meaningful changes
    if cps.empty:
        return "_No change-points detected in resting_hr at default sensitivity._"
    real = cps[cps["delta"].abs() >= 2.0]
    if real.empty:
        return "_No substantial change-points (|delta| ≥ 2 bpm) detected._"
    n_participants_affected = real["participant_id"].nunique()
    lines = [
        f"Substantial change-points (|delta| ≥ 2 bpm) detected for "
        f"**{n_participants_affected}** participants. A change-point cluster "
        "around the same calendar week across many participants is a strong "
        "signal of a firmware update or backend pipeline change; isolated "
        "changes are more likely individual physiology.",
        "",
        "| Participant | Date index | Before mean | After mean | Delta | Score |",
        "|---|---|---|---|---|---|",
    ]
    for _, row in real.head(10).iterrows():
        lines.append(
            f"| {row['participant_id']} | {int(row['index'])} | "
            f"{row['before_mean']:.2f} | {row['after_mean']:.2f} | "
            f"{row['delta']:+.2f} | {row['score']:.2f} |"
        )
    if len(real) > 10:
        lines.append(f"\n_…{len(real) - 10} more rows in_ "
                     f"`results/tables/change_points_resting_hr.csv`")
    return "\n".join(lines)


def _fairness_section(df: pd.DataFrame) -> str:
    """Per-stratum DBTS for device_type and skin_tone_proxy."""
    from ..reliability.fairness_audit import fairness_audit, disparity_summary
    out = []
    for col in ("device_type", "skin_tone_proxy"):
        if col not in df.columns:
            continue
        table = fairness_audit(df, stratify_by=col, n_bootstrap=30)
        if table.empty:
            continue
        out.append(f"### Stratified by `{col}`")
        out.append("")
        out.append("| Stratum | n_days | Overall (95% CI) | Signal quality | Artifact burden |")
        out.append("|---|---|---|---|---|")
        for _, row in table.iterrows():
            ci = (f"[{row['ci_low']:.1f}, {row['ci_high']:.1f}]"
                  if row['ci_low'] is not None else "n/a")
            out.append(
                f"| {row['stratum_value']} | {int(row['n_days'])} | "
                f"{row['overall_trust_score']:.1f} {ci} | "
                f"{row['signal_quality_score']:.1f} | "
                f"{row['artifact_burden_score']:.1f} |"
            )
        disp = disparity_summary(table)
        if not disp.empty:
            top = disp.iloc[0]
            out.append(
                f"\nLargest disparity: **{top['component']}**: "
                f"{top['min']:.1f} ({top['min_stratum']}) to "
                f"{top['max']:.1f} ({top['max_stratum']}), gap of "
                f"**{top['disparity']:.1f}** points."
            )
        out.append("")
    return "\n".join(out) if out else "_No stratifier columns available._"


def _weight_learning_section(df: pd.DataFrame) -> str:
    """Run the weight optimizer and report learned vs default."""
    from ..reliability.weight_optimization import (
        learn_weights, DEFAULT_WEIGHTS, sensitivity_table,
    )
    learned = learn_weights(df, target_metric="hrv_rmssd",
                            n_random=200, n_refine=4)
    sens = sensitivity_table(df, learned)
    lines = [
        "We searched the 6-component weight simplex for the weighting that "
        "maximizes Spearman correlation between the overall trust score and "
        "week-over-week reproducibility of HRV RMSSD. Holdout is a 30% "
        "participant-level split that the search never sees.",
        "",
        f"- ρ on training participants: **{learned.spearman_train:+.3f}**",
        f"- ρ on holdout participants: **{learned.spearman_holdout:+.3f}**",
        f"- Search budget: {learned.n_evaluated} weight combinations evaluated.",
        "",
        "| Component | Default weight | Learned weight |",
        "|---|---|---|",
    ]
    for k in DEFAULT_WEIGHTS:
        lines.append(
            f"| {k} | {DEFAULT_WEIGHTS[k]:.3f} | {learned.weights[k]:.3f} |"
        )
    lines += [
        "",
        "Rank stability under weight perturbation (median Spearman of the "
        "participant ranking against the learned-weight baseline):",
        "",
        "| Perturbation magnitude | Median rank ρ | Worst-case rank ρ |",
        "|---|---|---|",
    ]
    for _, row in sens.iterrows():
        lines.append(
            f"| {row['perturbation_magnitude']:.2f} | "
            f"{row['median_rank_correlation']:.3f} | "
            f"{row['min_rank_correlation']:.3f} |"
        )
    lines.append("")
    lines.append(
        "_The learned weights apply to this synthetic cohort and this "
        "downstream task. They are not a general recommendation. Re-run on "
        "your own cohort and your own outcome before relying on the result._"
    )
    return "\n".join(lines)


def generate_report(synthetic_csv: str | None = None,
                    out_md: str | None = None) -> Path:
    cfg = load_yaml("configs/default.yaml")
    in_path = resolve(synthetic_csv or cfg.paths.synthetic_csv)
    out_path = resolve(out_md or cfg.paths.report_md)
    figures_dir = ensure_dir(cfg.paths.figures_dir)
    ensure_dir(out_path.parent)

    df = pd.read_csv(in_path)
    scorer = DigitalBiomarkerTrustScore()
    trust_df = scorer.cohort_scores(df)

    # use the median participant for the example radar
    median_row = trust_df.iloc[(trust_df["overall_trust_score"] - trust_df[
        "overall_trust_score"].median()).abs().argmin()]
    example_components = {
        k: float(median_row[k]) for k in (
            "signal_quality_score", "artifact_burden_score",
            "temporal_stability_score", "missingness_risk_score",
            "device_bias_score", "confounding_risk_score",
        )
    }

    # try to grab one example signal pair
    ecg = ppg = None
    windows_path = resolve(cfg.paths.synthetic_windows)
    if windows_path.exists():
        try:
            arrays = np.load(windows_path)
            ecg = arrays["ecg"][0]
            ppg = arrays["ppg"][0]
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not load windows: %s", exc)

    figure_paths = figure_builder.write_all(
        df, trust_df, example_components, ecg=ecg, ppg=ppg,
        ecg_fs=int(cfg.cohort.ecg_sample_rate_hz),
        ppg_fs=int(cfg.cohort.ppg_sample_rate_hz),
    )

    md = [
        "# Signal Forensics Report",
        "",
        DISCLAIMER,
        "",
        "## Headline",
        _headline(df, trust_df),
        "## Signal quality summary",
        f"- Mean signal_quality_ground_truth: "
        f"**{df['signal_quality_ground_truth'].mean():.3f}**",
        f"- Fraction of windows with signal_quality_ground_truth < 0.5: "
        f"**{(df['signal_quality_ground_truth'] < 0.5).mean() * 100:.1f}%**",
        "",
        "## Artifact burden summary",
        f"- Mean artifact_burden_ground_truth: "
        f"**{df['artifact_burden_ground_truth'].mean():.3f}**",
        f"- Fraction of participant-days flagged: "
        f"**{(df['artifact_burden_ground_truth'] > 0.4).mean() * 100:.1f}%**",
        "",
        "## Reliability statistics",
        f"- Mean reliability_ground_truth: "
        f"**{df['reliability_ground_truth'].mean():.3f}**",
        "",
        "## Test-retest reliability (week-pair design, bootstrap CIs)",
        _test_retest_section(df),
        "",
        "## ICC(2,1) days-as-raters vs proper week-pair test-retest",
        _icc_comparison_section(),
        "",
        "## Baseline comparison (in-house SQI vs Orphanidou 2015)",
        _orphanidou_comparison_section(),
        "",
        "## Missingness analysis",
        _missingness_section(df),
        "",
        "## Device-bias analysis",
        _device_bias_section(df),
        "",
        "## Confounding risk (screening)",
        _confounding_section(df),
        "",
        "## Confounding risk (causal-adjusted)",
        _causal_section(df),
        "",
        "## Change-point surveillance (firmware drift proxy)",
        _change_point_section(df),
        "",
        "## Stratified fairness audit",
        _fairness_section(df),
        "",
        "## Learned trust-score weights",
        _weight_learning_section(df),
        "",
        "## Cohort trust score distribution",
        f"- Mean: **{trust_df['overall_trust_score'].mean():.2f}**",
        f"- Median: **{trust_df['overall_trust_score'].median():.2f}**",
        f"- 10th-90th percentile: "
        f"**{trust_df['overall_trust_score'].quantile(0.1):.1f} - "
        f"{trust_df['overall_trust_score'].quantile(0.9):.1f}**",
        "",
        "## Example trust report (median-trust participant)",
        "",
        trust_report.render(
            scorer.score(df[df["participant_id"] == median_row["participant_id"]]),
            participant_id=str(median_row["participant_id"]),
        ),
        "",
        "## Methodological recommendations",
        _recommendations(df, trust_df),
        "",
        "## Figures",
        "",
    ]
    for p in figure_paths:
        rel = p.relative_to(resolve("."))
        md.append(f"- `{rel}`")
    md += ["", DISCLAIMER, ""]

    out_path.write_text("\n".join(md), encoding="utf-8")
    log.info("Wrote report → %s", out_path)
    return out_path
