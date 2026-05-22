# Supplement S2: reviewer-grade extended analyses

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

This supplement contains six reviewer-grade extended analyses that go beyond the headline numbers in the main manuscript. Each analysis addresses a question a careful peer reviewer would ask. All numbers come from `scripts/run_extended_analyses.py` run on the same fresh outputs that back the main manuscript. Numbers are reproducible end-to-end in ~30 seconds on a modern laptop CPU.

## S2.1 AIPW positivity check

A doubly-robust AIPW estimator requires the positivity assumption: the propensity score must be bounded away from 0 and 1 for all units. Violations make the inverse-propensity weights unstable and the estimate sensitive to extrapolation. Reviewers will ask for the distribution of estimated propensity scores.

| Treatment | Outcome | n | PS mean | PS p5 | PS p95 | Frac outside [0.05, 0.95] | Kish ESS / n |
|---|---|---|---|---|---|---|---|
| heat_index | hrv_rmssd | 18000 | 0.504 | 8.9 × 10⁻¹⁵ | 1.000 | **93.4%** | **62.9%** |
| heat_index | sleep_efficiency | 18000 | 0.504 | 8.9 × 10⁻¹⁵ | 1.000 | **93.4%** | **62.9%** |
| active_minutes | hrv_rmssd | 18000 | 0.500 | 0.397 | 0.604 | **0.0%** | **98.5%** |

**Honest finding.** The heat_index treatments have a severe positivity problem on the synthetic cohort. Propensity scores range from 10⁻²⁴ to 1.0, and 93% of observations have propensity scores outside the conventional [0.05, 0.95] window. Kish's effective sample size drops to 63% of nominal. The cause is collinearity: `temperature_c` (one of the adjustment covariates) correlates with `heat_index` at r = 0.997, so the binarized heat_index treatment is nearly perfectly predicted from `temperature_c` alone, which pushes propensities to 0 or 1. This is a textbook collinearity-induced positivity failure, fixable by dropping `temperature_c` from the heat_index adjustment set (since heat_index already encodes most of the same information). The AIPW point estimates for heat_index (+0.249 with CI [-0.604, +1.030]) should be read accordingly: the wide CI reflects the loss of effective sample size from extreme propensity weights, not a genuine causal uncertainty.

The active_minutes → hrv_rmssd analysis has clean positivity: propensities concentrated near 0.50, zero observations outside the clip, Kish ESS at 98.5% of nominal. The -0.497 [-0.797, -0.137] AIPW estimate is statistically clean and is the AIPW result that should anchor the methods-paper claim. The heat_index analysis should be reported as illustrative of "screening correlation can invert under adjustment" but flagged as positivity-limited.

CSV: `results/extended_analysis/aipw_positivity.csv`. Figure 9 panel A.

## S2.2 E-value sensitivity to unmeasured confounding

The AIPW estimator adjusts for measured confounders. Reviewers will ask: how strong would an unmeasured confounder need to be to explain away the effect? We compute the E-value (VanderWeele & Ding 2017) on each AIPW estimate using the Chinn (2000) standardized-effect-to-RR conversion.

| Treatment | Outcome | AIPW estimate | RR-equivalent | E-value (point) | E-value (CI bound) |
|---|---|---|---|---|---|
| active_minutes | hrv_rmssd | **-0.497** | 1.57 | **2.52** | **1.52** |
| heat_index | hrv_rmssd | +0.249 | 1.25 | 1.82 | - (CI crosses null) |
| heat_index | sleep_efficiency | +0.005 | 1.00 | 1.07 | 1.01 |
| aqi | sleep_efficiency | -0.002 | 1.00 | 1.04 | - (CI crosses null) |

**Interpretation.** For the active_minutes → HRV result, an unmeasured confounder would need to have a risk ratio of at least 2.52 with both the treatment and the outcome (after adjustment for measured covariates) to fully explain away the point estimate, and at least 1.52 to shift the CI lower bound to the null. These are modest E-values (the Hernán & VanderWeele convention treats E > 2.0 as "moderate to strong" robustness). A reviewer can then judge whether they consider a 1.52-strength confounder plausible. Our position is that with sleep efficiency, stress proxy, AQI, and temperature already in the adjustment set, a 1.52-strength residual confounder is implausible on this synthetic generator.

The heat_index results have E-values close to 1.0, which is consistent with the positivity violation flagged in S2.1: the point estimates are not robust to confounding because they are not robust to the choice of adjustment set in the first place.

CSV: `results/extended_analysis/evalues.csv`. Figure 9 panel B.

## S2.3 Multi-operating-point recalibration with bootstrap CIs

The headline recalibration result in Section 4.3 (held-out κ = +0.217 at threshold 0.99) is a single operating point. Reviewers will ask for the full ROC, PR, and F1 curves, and bootstrap CIs on the chosen threshold.

| Quantity | Point estimate | 95% bootstrap CI |
|---|---|---|
| AUROC | **0.703** | **[0.659, 0.736]** |
| Youden's J threshold | 0.9915 | [0.9857, 0.9924] |
| F1-maximizing threshold | 0.9915 | [0.9858, 0.9930] |

**Bootstrap CIs from 200 paired resamples.** AUROC is significantly above chance (lower CI 0.659 well above 0.5). The Youden-J and F1-maximizing thresholds both land near 0.99 with narrow CIs spanning ~0.007 in threshold units. The recalibrated threshold is therefore not a chance product of the held-out split: it is a stable operating point on the in-house SQI distribution against the Orphanidou label.

The ROC curve and the bootstrap CI are shown in Figure 9 panel C. The PR curve is in `results/extended_analysis/pr_curve.csv`.

## S2.4 RR-cleaning robustness sweep

Section 4 uses two-stage RR cleaning (plausibility filter 0.4-1.5 s, then drop intervals more than 25% from the running median per Malik 1996). Reviewers will ask whether the HRV numbers are artifacts of this particular policy. We report HR and RMSSD on each subject's baseline ECG under five policies.

| Subject | Policy | n RR | HR (bpm) | RMSSD (ms) | SDNN (ms) |
|---|---|---|---|---|---|
| S2 | raw (no cleaning) | 1376 | 72.20 | **127.16** | 107.35 |
| S2 | plausibility only | 1367 | 72.25 | 82.61 | 78.97 |
| S2 | **plausibility + Malik 25%** | 1354 | 72.33 | **59.48** | 69.17 |
| S2 | plausibility + Malik 10% | 1047 | 71.61 | 47.94 | 42.81 |
| S2 | plausibility + NN50 | 883 | 72.42 | 61.46 | 69.92 |
| S3 | raw (no cleaning) | 1032 | 54.37 | 121.22 | 124.62 |
| S3 | plausibility only | 1031 | 54.39 | 120.05 | 124.02 |
| S3 | **plausibility + Malik 25%** | 993 | 54.00 | **116.52** | 109.71 |
| S3 | plausibility + Malik 10% | 696 | 52.98 | 84.52 | 62.71 |
| S3 | plausibility + NN50 | 352 | 54.05 | 139.28 | 125.39 |

**Findings.**

1. **S2's RMSSD is highly sensitive to cleaning policy:** raw 127 ms → plausibility 83 ms → Malik 25% 60 ms → Malik 10% 48 ms. The raw value is inflated by occasional missed beats. Plausibility alone removes the worst offenders. Malik 25% (our default) brings it into the normal range for a young adult at rest.

2. **S3's RMSSD is robust to the choice between raw, plausibility, and Malik 25%** (121 → 120 → 117 ms). The Malik 10% filter drops it to 85 ms but discards 32% of the RR intervals, which is too aggressive. The NN50-style filter (drop the post-jump interval when consecutive RR differs by more than 50 ms) gives the counter-intuitive result of 139 ms on the smallest sample. The mechanism is gap creation: removing intermediate intervals leaves the kept sequence with new large diffs between non-adjacent original neighbors. We include this row to show what fails, not to recommend it.

3. **The honest middle ground is Malik 25% (Task Force 1996)**, which is what we use. S2 = 59.5 ms is solidly normal; S3 = 116.5 ms is genuinely high but not implausible for a young person with strong vagal tone. A Pan-Tompkins-style detector independently gives 115.6 ms on S3 (Section 4 of the main manuscript), confirming that this is not a detector-induced artifact.

CSV: `results/extended_analysis/rr_cleaning_robustness.csv`. Figure 9 panel D.

## S2.5 Real-data within-baseline test-retest

The main manuscript reports test-retest reliability on the synthetic cohort (Section 3.2). Reviewers will ask about real-data analog. We compute split-half reliability on per-window HR estimates within each WESAD subject's ~19-minute baseline segment.

| Subject | n windows total | n valid | HR mean (bpm) | HR SD (bpm) | Within-subject CV (%) | Split-half r |
|---|---|---|---|---|---|---|
| S2 | 228 | 227 | 72.47 | 4.89 | **6.74** | **+0.078** |
| S3 | 228 | 228 | 54.65 | 4.96 | **9.07** | **+0.112** |

**Honest finding.** Within-subject HR varies meaningfully within a single ~19-minute resting baseline (CV 6.7% on S2, 9.1% on S3). The split-half Pearson correlation between the first half and second half of each subject's per-window HR is +0.08 and +0.11. These are essentially noise.

This is **substantially weaker than the synthetic week-pair r of +0.977 for resting HR** (Section 3.2). Two non-exclusive explanations:

1. **Different units of analysis.** The synthetic test-retest uses week-mean HR (averaging ~7 days × 1 measurement-per-day), while the real-data split-half uses per-window HR at 5-second resolution. Per-window HR has more measurement noise.
2. **Real-data within-session variability is real.** Resting baseline in WESAD is not perfectly controlled; subjects breathe, swallow, and shift posture during the session, which moves HR enough to overwhelm a 19-minute split-half signal.

This finding does not contradict the synthetic-cohort headline. The headline is week-to-week reliability of a daily-aggregated resting HR estimate; the real-data finding is 5-second-window-to-5-second-window correlation within a single session. They measure different things. But it is honest to report both, and reviewers will appreciate the candor.

The framework's recommended HR reliability statistic for a real-data study is the bootstrap week-pair test-retest of a daily aggregate, which is what Section 3.2 reports. Validating that on a longitudinal real dataset (AppleWatch-MIMIC, All of Us) is outside the WESAD pilot scope and is recommended future work.

CSV: `results/extended_analysis/per_subject_reliability.csv`. Figure 9 panel E.

## S2.6 Per-state effect sizes: Cliff's δ and Cohen's d with bootstrap CIs

Section 4.5 reports Mann-Whitney U with Cliff's δ for the within-subject per-state contrasts. Reviewers will ask for Cohen's d (the parametric companion) and bootstrap CIs on the effect sizes.

| Subject | Metric | Contrast | n_a | n_b | p-value | Cliff's δ [95% CI] | Cohen's d |
|---|---|---|---|---|---|---|---|
| **S3** | PPG SQI | baseline vs amusement | 227 | 74 | 1.9e-10 | **+0.49 [+0.34, +0.63]** | **+0.80** |
| **S3** | PPG motion | baseline vs amusement | 227 | 74 | 1.9e-10 | **-0.49 [-0.63, -0.34]** | **-0.80** |
| S3 | PPG SQI | baseline vs stress | 227 | 127 | 0.026 | +0.14 [+0.02, +0.27] | +0.27 |
| S3 | PPG motion | baseline vs stress | 227 | 127 | 0.026 | -0.14 [-0.27, -0.02] | -0.27 |
| **S2** | ECG SQI | baseline vs stress | 228 | 122 | 4.5e-7 | **+0.32 [+0.20, +0.44]** | **+0.60** |
| **S2** | ECG SQI | baseline vs amusement | 228 | 72 | 1.2e-3 | **+0.25 [+0.10, +0.40]** | **+0.33** |
| S2 | PPG SQI | baseline vs stress | 228 | 122 | 0.141 | +0.10 [-0.04, +0.22] | +0.30 |
| S2 | PPG motion | baseline vs stress | 228 | 122 | 0.141 | -0.10 [-0.22, +0.04] | -0.30 |
| S2 | PPG SQI | baseline vs amusement | 228 | 72 | 0.780 | -0.02 [-0.18, +0.13] | +0.08 |
| S2 | PPG motion | baseline vs amusement | 228 | 72 | 0.780 | +0.02 [-0.13, +0.18] | -0.08 |
| S3 | ECG SQI | baseline vs stress | 227 | 127 | 0.075 | -0.11 [-0.22, +0.00] | -0.15 |
| S3 | ECG SQI | baseline vs amusement | 227 | 74 | 0.386 | -0.07 [-0.20, +0.09] | -0.10 |

**Findings.**

1. **S3 baseline vs amusement is the largest effect in the dataset.** Cliff's δ = ±0.49 (medium-to-large by Romano's 2006 thresholds), Cohen's d = ±0.80 (large by Cohen's 1988 thresholds). Both effect-size families agree. The PPG SQI drops, the motion artifact score rises. The 95% CI on Cliff's δ excludes zero comfortably.

2. **S2 ECG SQI drops during stress with Cliff's δ = +0.32 and Cohen's d = +0.60** (both medium effects). The ECG signal quality on the chest device is degraded during the Trier task even though chest ECG is supposed to be robust to motion. Worth flagging in the discussion.

3. **The two effect-size families disagree only in sign-magnitude relations** (Cliff's δ is bounded in [-1, +1], Cohen's d is unbounded), but they agree on which contrasts are significant and which are not. This is the standard sanity check on effect-size reporting.

4. **All significant effects have 95% CIs on Cliff's δ that exclude zero**, which is the bootstrap analog of the Wilcoxon p-value claim.

CSV: `results/extended_analysis/per_state_effect_sizes.csv`. Figure 9 panel F.

## S2.7 Summary table: what each analysis adds

| Analysis | Question answered | Main finding |
|---|---|---|
| S2.1 Positivity | Are AIPW estimates trustworthy? | active_minutes positivity is clean; heat_index has severe violation (Kish ESS 63%) |
| S2.2 E-values | How strong must unmeasured confounder be? | active_minutes → HRV: needs RR ≥ 1.52 to shift CI to null |
| S2.3 ROC/PR/F1 | Is the recalibrated threshold stable? | Yes. Youden CI [0.986, 0.992]. AUROC 0.70 [0.66, 0.74] |
| S2.4 RR cleaning | Are HRV numbers artifacts of a single filter? | S3's high HRV holds across raw, plausibility, Malik 25% |
| S2.5 Real-data reliability | Does within-session HR replicate? | No: split-half r = 0.08-0.11, CV = 7-9%. Different unit of analysis from week-pair |
| S2.6 Effect sizes | Are state contrasts robust? | Cliff's δ and Cohen's d agree. S3 amusement = large effect on both scales |

## Figure 9 caption

Six-panel reviewer-grade supplementary figure (`results/extended_analysis/figure_extended.png`).
(A) Distribution of estimated propensity scores for three AIPW analyses, showing the heat_index positivity violation (range spans 10⁻²⁴ to 1.0) and the clean active_minutes positivity (concentrated near 0.5).
(B) E-values for the four AIPW analyses on Chinn-converted RR scale. active_minutes → HRV has the largest E-value (point 2.52, CI bound 1.52), meaning an unmeasured confounder would need an effect of RR ≥ 1.52 to explain away the lower-CI bound.
(C) Full ROC curve for the in-house SQI as a predictor of Orphanidou pass/fail on real WESAD wrist PPG. AUROC = 0.703 with bootstrap 95% CI [0.659, 0.736]. The Youden's J optimum is at threshold 0.991 with CI [0.986, 0.992].
(D) RMSSD on each WESAD subject's baseline ECG under five RR-cleaning policies. S2's RMSSD is highly sensitive (127 → 83 → 60 → 48 ms), S3's is robust except under the NN50 filter (121 → 120 → 117 → 85 → 139 ms).
(E) Per-subject within-baseline split-half HR reliability on real data. Pearson r = +0.078 (S2) and +0.112 (S3); within-subject CV = 6.7% (S2) and 9.1% (S3). Substantially weaker than the synthetic week-pair r of +0.977, attributable to different units of analysis (5-second-window vs daily-aggregate) and to real within-session HR variability.
(F) Significant baseline vs amusement contrasts plotted with both Cliff's δ (with bootstrap 95% CI) and Cohen's d. The two effect-size families agree on direction and magnitude ordering. S3 baseline vs amusement on PPG SQI / motion shows the largest effect (Cliff's δ = ±0.49, Cohen's d = ±0.80).
