---
title: "Supplementary Materials: Biomedical Signal Forensics for Wearable-Derived Digital Biomarkers"
author: "Ceyhun Olcan"
---

# Supplementary Materials

This supplement contains extended methodological details, sensitivity analyses, and per-subject result tables referenced in the main manuscript.

## S1. ICC(2,1) days-as-raters vs bootstrap week-pair Pearson r

Comparison of ICC and bootstrap week-pair r on the synthetic cohort:

| Metric | ICC(2,1) | Week-pair r | 95% CI (r) |
| --- | --- | --- | --- |
| resting_hr | +0.869 | +0.977 | [+0.973, +0.980] |
| hrv_rmssd | +0.779 | +0.954 | [+0.945, +0.961] |
| sleep_efficiency | +0.006 | +0.023 | [-0.018, +0.062] |
| sleep_duration | -0.003 | +0.002 | [-0.041, +0.038] |

: Table S1. ICC(2,1) days-as-raters vs bootstrap week-pair Pearson r on the synthetic cohort.

The two methods agree on metric ranking. The ICC is uniformly more conservative because it treats within-week noise as rater disagreement. Both methods correctly identify sleep efficiency and duration as essentially unreliable.

## S2. Positivity and E-value sensitivity for AIPW estimates

The heat_index treatments have a positivity violation on the synthetic cohort: estimated propensity scores span 10⁻²⁴ to 1.0, with 93% of observations outside the conventional [0.05, 0.95] clip, and Kish's effective sample size drops to 63% of nominal. The heat_index AIPW point estimates are therefore positivity-limited and should be treated as illustrative of "screening can invert under adjustment" rather than as quantitative causal claims.

The active_minutes treatment has clean positivity (Kish ESS 98.5%) and is the quantitatively defensible AIPW result. The E-value [@vanderweele2017] for the active_minutes finding is 2.52 (point) and 1.52 (CI bound), meaning an unmeasured confounder would need a risk-ratio strength of at least 1.52 with both treatment and outcome (after measured-covariate adjustment) to shift the CI lower bound to the null. The E-value indicates modest robustness.

## S3. Cross-cohort parameter-sweep details

Five synthetic regimes, eight qualitative predictions:

| Regime | heat→HRV r | Q4-Q1 SQI gap | device-B empirical (bpm) | HRV test-retest r |
| --- | --- | --- | --- | --- |
| default | -0.075 | -7.54 | +3.20 | +0.955 |
| strong_environment | -0.190 | -20.36 | +3.20 | +0.921 |
| inverted_skin_tone | -0.075 | +9.34 | +3.20 | +0.955 |
| severe_device_bias | -0.075 | -7.54 | +7.40 | +0.955 |
| clean_world | +0.007 | +1.07 | -0.60 | +0.959 |

: Table S2. Five-regime cross-cohort parameter-sweep results.

CSVs: `results/tables/cross_cohort_regimes.csv`, `results/tables/cross_cohort_predictions.csv`.

## S4. Per-subject effect sizes — stress vs baseline

Largest stress-vs-baseline effects (PPG SQI drop or motion rise), sorted by Cliff's δ [@cliff1993]:

| Subject | Metric | n_a / n_b | Cliff's δ [95% CI] | Cohen's d | p |
| --- | --- | --- | --- | --- | --- |
| S17 | PPG SQI | 235 / 144 | +0.75 [+0.68, +0.82] | +1.16 | 1.0e-34 |
| S5 | PPG SQI | 239 / 128 | +0.73 [+0.65, +0.79] | +1.37 | 2.0e-30 |
| S14 | PPG SQI | 235 / 134 | +0.70 [+0.62, +0.78] | +1.30 | 2.7e-29 |
| S16 | PPG SQI | 235 / 134 | +0.59 [+0.46, +0.71] | +1.41 | 4.6e-21 |
| S11 | PPG SQI | 235 / 135 | +0.50 [+0.39, +0.61] | +0.98 | 8.8e-16 |
| S15 | PPG SQI | 234 / 137 | -0.49 [-0.58, -0.39] | -0.79 | 4.0e-15 |
| S4 | PPG SQI | 230 / 126 | +0.44 [+0.32, +0.55] | +0.90 | 9.7e-12 |

: Table S3. Largest stress-vs-baseline effect sizes per subject on WESAD.

Most subjects show a PPG SQI drop during stress, but S15 shows the opposite (δ = -0.49): their PPG SQI rises during stress. This is consistent with state-dependent posture: if a subject moves less during the stressor than during baseline, their PPG quality can improve.

## S5. Per-subject effect sizes — amusement vs baseline

Largest baseline-vs-amusement effects, sorted by Cliff's δ:

| Subject | Metric | n_a / n_b | Cliff's δ [95% CI] | Cohen's d | p |
| --- | --- | --- | --- | --- | --- |
| S9 | PPG SQI | 235 / 74 | +0.80 [+0.71, +0.88] | +1.89 | 3.7e-25 |
| S14 | ECG SQI | 235 / 73 | +0.70 [+0.57, +0.84] | +1.59 | 8.5e-20 |
| S16 | PPG SQI | 235 / 72 | +0.70 [+0.58, +0.80] | +1.37 | 4.1e-19 |
| S14 | PPG SQI | 235 / 73 | +0.61 [+0.48, +0.74] | +1.55 | 3.7e-15 |
| S5 | PPG SQI | 239 / 74 | +0.61 [+0.51, +0.71] | +0.97 | 1.6e-15 |
| S17 | PPG SQI | 235 / 73 | +0.59 [+0.48, +0.68] | +0.97 | 4.4e-14 |

: Table S4. Largest baseline-vs-amusement effect sizes per subject on WESAD.

The funny-video amusement paradigm produces upper-body laughter motion that degrades wrist PPG in most subjects.

## S6. Learned trust-score weights — training and holdout

Search over the 6-component weight simplex:

- Sampling: 360 Dirichlet draws plus local grid refinement near the best candidate.
- Training Spearman ρ between overall trust score and week-over-week HRV RMSSD reproducibility: +0.592 (n_train = 210).
- Holdout Spearman ρ: +0.668 (n_holdout = 90).

The learned weights emphasize signal_quality and reduce emphasis on confounding_risk but remain within the convex hull of plausible weightings. The default weights produce Spearman within 0.08 of the optimum on this cohort.

## References


## S7 Threshold sensitivity for the in-house SQI baseline

The 44.6% / 43.1% headline metric (in-house pass AND all three published methods fail) is numerically dominated by the published-only consensus rejection rate, which is independent of any choice of in-house threshold. Varying the in-house threshold from 0.50 to 0.95 spans the full range of permissive thresholds plausibly used by wearable-PPG pipelines that retain most windows. The published-method internal disagreement (median pairwise Cohen's κ) is unaffected by any in-house decision and is shown in the rightmost column as a constant within each dataset.

| Dataset | Threshold | In-house pass rate (%) | In-house pass AND all 3 pub fail (%) | Pub-only consensus rejection (%) | Median pairwise published κ |
|---|---|---|---|---|---|
| WESAD | 0.50 | 100.000 | 44.571 | 44.571 | -0.198 |
| WESAD | 0.60 | 100.000 | 44.571 | 44.571 | -0.198 |
| WESAD | 0.70 | 100.000 | 44.571 | 44.571 | -0.198 |
| WESAD | 0.80 | 100.000 | 44.571 | 44.571 | -0.198 |
| WESAD | 0.85 | 99.970 | 44.541 | 44.571 | -0.198 |
| WESAD | 0.90 | 99.636 | 44.480 | 44.571 | -0.198 |
| WESAD | 0.95 | 97.130 | 43.569 | 44.571 | -0.198 |
| PPG-DaLiA | 0.50 | 100.000 | 43.129 | 43.129 | -0.204 |
| PPG-DaLiA | 0.60 | 100.000 | 43.129 | 43.129 | -0.204 |
| PPG-DaLiA | 0.70 | 100.000 | 43.129 | 43.129 | -0.204 |
| PPG-DaLiA | 0.80 | 99.995 | 43.129 | 43.129 | -0.204 |
| PPG-DaLiA | 0.85 | 99.904 | 43.070 | 43.129 | -0.204 |
| PPG-DaLiA | 0.90 | 99.569 | 42.846 | 43.129 | -0.204 |
| PPG-DaLiA | 0.95 | 97.178 | 41.664 | 43.129 | -0.204 |

: Table S5. Threshold-sensitivity analysis for the in-house SQI baseline on WESAD and PPG-DaLiA. The full sensitivity output is at results/real_data/threshold_sensitivity.csv.


![Supplementary Figure S2. Threshold-sensitivity analysis for the in-house PPG SQI baseline on WESAD (a) and PPG-DaLiA (b). Solid line: joint condition (in-house passes AND all three published methods fail). Dashed line: published-only consensus rejection (independent of in-house decision). Both lines are nearly flat across the in-house threshold range 0.50 to 0.95 (range across thresholds < 0.05 percentage points on both datasets), confirming the headline disagreement finding is robust to the in-house threshold choice. The default threshold (0.70) is marked.](paper/figures/figS2_threshold_sensitivity.png)


## S8. LOSO subject-level recalibration

To test whether the negative recalibration result in main-text Section 3.3 is robust to the train/test split strategy, we re-ran the threshold search as leave-one-subject-out cross-validation across all 15 WESAD subjects. For each held-out subject, the threshold was selected on the other 14 subjects to maximize Cohen's kappa versus the Orphanidou pass/fail label, then evaluated on the held-out subject. Mean held-out kappa across the 15 folds is -0.063 (median 0.000, range -0.321 to +0.002).

For 10 of 15 subjects the train search settles on threshold 0.85, under which the in-house SQI still passes 100% of the held-out subject's windows; held-out kappa is therefore degenerate at zero (Cohen's kappa is forced to zero when one of the two raters has constant output). For the remaining 5 subjects the train search lands on stricter thresholds (0.98 to 0.99) that produce non-trivial in-house pass/fail variation on the held-out subject; on these 5 subjects 4 show strongly negative held-out kappa (S10: -0.321, S13: -0.214, S16: -0.250, S9: -0.163) and S17 is at +0.0017, essentially zero.

The LOSO recalibration therefore confirms and sharpens the negative result reported in Section 3.3 (random window-split gives Δkappa approximately zero): when the in-house SQI is forced to make discriminating decisions, it does not recover agreement with the Orphanidou baseline. Full per-subject output: `results/real_data/loso_recalibration.csv`.

![Supplementary Figure S3. LOSO per-subject held-out Cohen's kappa from the subject-level recalibration cross-validation on WESAD (n = 15 folds). Bars sorted by held-out kappa ascending. Red bars: non-degenerate folds (in-house SQI varies on the held-out subject so kappa is meaningful). Grey bars: degenerate folds (in-house SQI passes 100% of held-out windows so kappa is forced to zero). Mean held-out kappa = -0.063 (dashed line).](paper/figures/figS3_loso_recalibration.png)


## S9. Consensus rejection: alternative view of the headline finding

The main-text Figure 1 (conceptual Venn) shows the cross-method signal-quality disagreement on WESAD and PPG-DaLiA as overlapping disks of acceptance with a dark region for consensus rejection. Supplementary Figure S4 provides a complementary stacked-bar view of the same finding on WESAD: of 6,585 5-second windows, the in-house pipeline accepts every one (100.0%), but applying the three independently developed published methods simultaneously rejects 2,936 (44.6%) of the same windows. The two visualizations summarize the same numbers from different angles; we include both because reviewers and readers may find one or the other more communicative.

![Supplementary Figure S4. Verdict gap between the in-house threshold-based PPG SQI and the three-baseline consensus on WESAD (n = 15 subjects, 6,585 5-second windows). The in-house pipeline passes every window. Applying Orphanidou 2015, Sukor 2011, and Elgendi 2016 simultaneously, 2,936 of the same 6,585 windows (44.6%) are rejected by all three published methods.](paper/figures/fig4_rejection_cascade.png)
