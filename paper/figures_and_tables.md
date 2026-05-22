# Figures and tables index

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

This file is the canonical index of every figure and table referenced in `paper/manuscript.md`. Each entry gives the file location, the script that produces it, the input data, and the caption text as it would appear in a journal submission.

## Main figures

### Figure 1. Audit pipeline architecture

- **Source.** Schematic; not yet generated. Target path on creation: `results/figures/architecture_diagram.png`. Until generated, the manuscript can use a hand-drawn diagram or omit Figure 1 and renumber.
- **Caption.** Architecture of the `biomedical-signal-forensics-lab` audit pipeline. The pipeline takes daily summaries and short ECG/PPG windows as input and produces five categories of output: per-window artifact findings (five detectors), participant-level reliability primitives (test-retest, ICC, drift slope, device bias), a six-component Digital Biomarker Trust Score with cluster-bootstrap CIs, an AIPW-adjusted confounding analysis under a user-supplied DAG, and a stratified fairness audit. Three published PPG signal-quality baselines (in-house, Orphanidou 2015, Sukor 2011) run side by side on every audit.

### Figure 2. Synthetic-cohort headline results

- **Source.** Four-panel summary; produced as `results/figures/synthetic_headline.png` by `scripts/generate_report.py`.
- **Caption.** Headline results on the bundled 300-participant 60-day synthetic cohort. (A) Distribution of Digital Biomarker Trust Scores across participants (mean 74.11; 31 high, 266 moderate, 3 low). (B) Bootstrap week-pair test-retest reliability for four biomarkers with cluster-bootstrap 95% CIs (resting HR r = +0.977, HRV RMSSD r = +0.954, sleep efficiency r = +0.023, sleep duration r = +0.002). (C) Recovered fairness disparities by device family (device A reference, device C SQI gap −13 points) and skin-tone quartile (Q4-Q1 gap −9.5 points). (D) AIPW-adjusted vs screening Pearson correlations for three (treatment, outcome) pairs; the heat→HRV screening correlation of −0.054 inverts to +0.25 under back-door adjustment.

### Figure 3. Cross-cohort generalization sweep

- **Source.** `results/figures/cross_cohort_predictions.png`, produced by `scripts/run_cross_cohort_check.py`.
- **Caption.** Cross-cohort generalization across five generative regimes (default, strong environment, inverted skin tone, severe device bias, clean world). Eight qualitative predictions about how the audit should respond; 7 of 8 pass. Sign-flip on the skin-tone gap when the penalty is inverted from +0.12 to −0.12; near-zero gap recovered when all injected effects are removed. The framework's outputs respond to cohort parameters in the predicted direction.

### Figure 4. WESAD pilot: Bland-Altman wrist PPG vs chest ECG

- **Source.** `results/real_data/wesad_deep/figures/fig1_bland_altman_hr.png`, produced by `scripts/run_deep_real_analysis.py`.
- **Caption.** Bland-Altman plot of per-window heart rate from wrist Empatica E4 PPG vs chest RespiBAN ECG on real WESAD data (n=848 windows, 2 subjects), colored by labeled affective state. Bias +12.77 bpm; 95% limits of agreement [-16.18, +41.72] bpm. Only 30% of windows agree within 5 bpm. The amusement state (orange) cluster sits visibly higher in the disagreement axis than baseline (blue), consistent with motion-induced PPG bias.

### Figure 5. Three-way SQI pass-rate comparison

- **Source.** `results/real_data/wesad_deep/figures/fig3_sqi_pass_rates.png`.
- **Caption.** Pass rates of three PPG signal-quality methods on 850 real WESAD wrist PPG windows. In-house SQI at default threshold 0.70 passes 100%, Orphanidou (2015) passes 22%, Sukor (2011) passes 12%. The two published baselines agree with each other (Cohen's κ = +0.31, Spearman ρ = +0.57) but neither agrees with the synthetic-tuned in-house SQI on real data (κ = 0.000 vs both). The in-house SQI is the outlier, not the published baselines.

### Figure 6. Threshold recalibration against Orphanidou

- **Source.** `results/real_data/wesad_deep/figures/fig6_recalibration.png`.
- **Caption.** Cohen's κ between in-house pass/fail and Orphanidou pass/fail as a function of in-house threshold, on a 425-window holdout split. At the synthetic-tuned default (0.70) the κ is 0.000 (no agreement beyond chance). The κ rises sharply above 0.95 and peaks at 0.99, with held-out κ = +0.217 (fair agreement). The framework's `recalibrate_detector` helper exposes this analysis path.

### Figure 7. Motion artifact predicts cross-modality HR disagreement

- **Source.** `results/real_data/wesad_deep/figures/fig5_motion_vs_hr_error.png`.
- **Caption.** Scatter of |HR_PPG − HR_ECG| against the framework's per-window PPG motion-artifact score on real WESAD data (n=848 windows, 2 subjects). Spearman ρ = +0.30 between motion score and HR-modality disagreement. Mean error 12.9 bpm at low motion vs 19.6 bpm at high motion (52% increase). The motion detector is doing what it claims.

### Figure 8. Per-state SQI distributions

- **Source.** `results/real_data/wesad_deep/figures/fig4_per_state_panels.png`.
- **Caption.** Distributions of four per-window quantities by labeled WESAD affective state (baseline, stress, amusement). In-house PPG SQI is heavily concentrated near 1.0 across all states. PPG motion artifact rises monotonically from baseline (median 0.018) to amusement (0.025). HR-modality disagreement rises from baseline (median 8 bpm) to amusement (median 24 bpm). Orphanidou template correlation drops from baseline (median 0.78) to amusement (median 0.66). All four panels point in the same direction: the amusement state is the most challenging for wrist PPG.

## Supplementary figures

- **S1.** Reliability diagram for the in-house SQI as a probability-style estimator (`results/figures/reliability_diagram.png`). Expected calibration error after the v0.3.2 bug-fix that handles `p == 1.0` correctly.
- **S2.** Per-component trust-score distributions (`results/figures/trust_components.png`). Six panels, one per DBTS component, distribution across the 300 synthetic participants.
- **S3.** AIPW bootstrap distributions for three (treatment, outcome) pairs (`results/figures/aipw_bootstrap.png`). Cluster bootstrap at the participant level, 500 resamples.
- **S4.** Change-point detection on a synthetic firmware-drift signal (`results/figures/change_points_demo.png`). Both BOCPD and binary segmentation correctly identify the inserted step change.
- **S5.** Forest plot of skin-tone-quartile disparities (`results/figures/fairness_forest_skin_tone.png`). Per-component disparity with cluster-bootstrap 95% CIs.
- **S6.** Forest plot of device-family disparities (`results/figures/fairness_forest_device.png`). Same structure as S5 with device as the stratifier.

## Main tables

### Table 1. Synthetic cohort: bootstrap test-retest reliability

In `paper/manuscript.md` Section 3.2 and `paper/results.md` Section 6. Source CSV: `results/tables/test_retest_bootstrap.csv`.

### Table 2. ICC(2,1) days-as-raters vs proper week-pair r

In `paper/manuscript.md` Section 3.3 and `paper/results.md` Section 7. Source CSV: `results/tables/icc_vs_test_retest.csv`.

### Table 3. Fairness disparities recovered

In `paper/manuscript.md` Section 3.4. Source CSVs: `results/tables/fairness_by_device.csv`, `results/tables/fairness_by_skin_tone.csv`.

### Table 4. AIPW-adjusted vs screening confounding

In `paper/manuscript.md` Section 3.5. Source CSV: `results/tables/confounding_adjusted.csv`.

### Table 5. WESAD Bland-Altman HR agreement

In `paper/manuscript.md` Section 4.1 and `paper/real_data_pilot.md`. Source CSV: `results/real_data/wesad_deep/hr_agreement_per_subject_state.csv`.

### Table 6. Three-way SQI agreement on real WESAD PPG

In `paper/manuscript.md` Section 4.2 and `paper/real_data_pilot.md`. Source: `results/real_data/wesad_deep/summary.json`.

### Table 7. Recalibration of in-house SQI threshold

In `paper/manuscript.md` Section 4.3 and `paper/real_data_pilot.md`. Source: `results/real_data/wesad_deep/summary.json`.

### Table 8. WESAD within-subject state-contrast tests

In `paper/manuscript.md` Section 4.5 and `paper/real_data_pilot.md`. Source CSVs: `results/real_data/wesad_deep/per_state_baseline_vs_stress.csv`, `results/real_data/wesad_deep/per_state_baseline_vs_amusement.csv`.

## Supplementary tables

- **ST1.** Cross-cohort regime parameters and observed audit outputs. Source: `results/tables/cross_cohort_regimes.csv`.
- **ST2.** Cross-cohort predictions and pass/fail. Source: `results/tables/cross_cohort_predictions.csv`.
- **ST3.** Per-subject Orphanidou agreement on WESAD. Source: `results/real_data/wesad/orphanidou_per_subject.csv`.
- **ST4.** Per-window WESAD table with all SQI methods and HR estimates. Source: `results/real_data/wesad_deep/window_table.csv`.
- **ST5.** Learned trust-score weights and per-component sensitivity. Source: `results/tables/learned_weights.json`.
- **ST6.** Five-round bug-audit log. Source: `docs/bug_audit_round{1..5}.md`.

## Reproducibility note

Every figure listed above is generated by a script in `scripts/` and writes to a fixed path. The generation graph is:

```
scripts/run_pipeline.py
    → data/synthetic/*.csv

scripts/run_signal_audit.py
    → results/tables/{trust_scores, fairness_by_*, confounding_*, change_points_*, baseline_comparison_orphanidou, test_retest_bootstrap, icc_vs_test_retest}.csv

scripts/train_quality_model.py
    → results/model_leaderboard.csv

scripts/generate_report.py
    → results/figures/{trust_radar, trust_distribution, confounding_scatter, ...}.png
    → results/reports/signal_forensics_report.md

scripts/run_cross_cohort_check.py
    → results/tables/cross_cohort_{regimes, predictions}.csv

scripts/run_real_data_pilot.py --dataset wesad --path WESAD
    → results/real_data/wesad/*

scripts/run_deep_real_analysis.py --path WESAD
    → results/real_data/wesad_deep/*
    → results/real_data/wesad_deep/figures/fig{1..6}_*.png
```

Wall clock for the full chain on a modern laptop CPU: ~3 minutes for the synthetic side, ~30 seconds for the 2-subject WESAD pilot.
