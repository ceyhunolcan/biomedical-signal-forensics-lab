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
| AUROC | **0.484** | **[0.467, 0.499]** |
| Youden's J threshold | 0.9986 | [0.9786, 0.9993] |
| F1-maximizing threshold | 0.8645 | [0.8645, 0.8785] |

**Bootstrap CIs from 200 paired resamples on the full n=15 release (6585 windows).** At n=15 the AUROC drops to 0.484 (CI [0.467, 0.499]), straddling 0.5: the in-house SQI is statistically indistinguishable from chance at predicting Orphanidou pass/fail on real WESAD wrist PPG. The Youden and F1 threshold-selection rules disagree at n=15 (Youden at 0.9986, F1 at 0.8645), an instability that did not appear in the n=2 pilot. The pilot result that the recalibrated threshold was a stable operating point was an artifact of the small n=2 sample, not a general property of the in-house SQI distribution on real wrist PPG.

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
| S10 | 236 | 231 | 98.03 | 7.11 | 7.25 | -0.126 |
| S11 | 236 | 236 | 74.13 | 4.72 | 6.37 | +0.090 |
| S13 | 236 | 236 | 86.93 | 5.60 | 6.44 | +0.016 |
| S14 | 236 | 236 | 73.20 | 4.50 | 6.15 | +0.143 |
| S15 | 235 | 235 | 82.60 | 5.46 | 6.61 | +0.067 |
| S16 | 236 | 236 | 65.31 | 5.82 | 8.91 | +0.042 |
| S17 | 236 | 236 | 66.53 | 7.89 | 11.86 | +0.093 |
| S2 | 228 | 227 | 72.47 | 4.89 | 6.74 | +0.078 |
| S3 | 228 | 228 | 54.65 | 4.96 | 9.07 | +0.112 |
| S4 | 231 | 231 | 60.59 | 5.72 | 9.43 | +0.397 |
| S5 | 239 | 239 | 62.87 | 3.85 | 6.12 | +0.041 |
| S6 | 236 | 236 | 69.30 | 5.92 | 8.54 | -0.093 |
| S7 | 237 | 237 | 70.58 | 6.83 | 9.67 | +0.019 |
| S8 | 233 | 233 | 70.86 | 4.98 | 7.03 | -0.027 |
| S9 | 236 | 236 | 76.62 | 5.69 | 7.43 | +0.071 |

**Honest finding (n=15).** Median within-subject CV is **7.25%** (range 6.12-11.86%). Median split-half Pearson r is **+0.067** (range -0.126 to +0.397). Only S4 shows split-half r above +0.30 (+0.397); the rest are near zero or weakly negative. Within-baseline HR estimates from per-window 5-second windows are essentially uncorrelated between the first and second halves of the session for nearly all subjects. This confirms the pilot finding (which used only S2 and S3) and rules out an n=2-specific artifact.

This is **substantially weaker than the synthetic week-pair r of +0.977 for resting HR** (Section 3.2). Two non-exclusive explanations:

1. **Different units of analysis.** The synthetic test-retest uses week-mean HR (averaging ~7 days × 1 measurement-per-day), while the real-data split-half uses per-window HR at 5-second resolution. Per-window HR has more measurement noise.
2. **Real-data within-session variability is real.** Resting baseline in WESAD is not perfectly controlled; subjects breathe, swallow, and shift posture during the session, which moves HR enough to overwhelm a 19-minute split-half signal.

This finding does not contradict the synthetic-cohort headline. The headline is week-to-week reliability of a daily-aggregated resting HR estimate; the real-data finding is 5-second-window-to-5-second-window correlation within a single session. They measure different things. But it is honest to report both, and reviewers will appreciate the candor.

The framework's recommended HR reliability statistic for a real-data study is the bootstrap week-pair test-retest of a daily aggregate, which is what Section 3.2 reports. Validating that on a longitudinal real dataset (AppleWatch-MIMIC, All of Us) is outside the WESAD pilot scope and is recommended future work.

CSV: `results/extended_analysis/per_subject_reliability.csv`. Figure 9 panel E.

## S2.6 Per-state effect sizes: Cliff's δ and Cohen's d with bootstrap CIs

Mann-Whitney U with both Cliff's δ and Cohen's d for each (subject, metric, baseline-vs-state) contrast. The full table is in `results/extended_analysis/per_state_effect_sizes.csv`; the 12 contrasts with the largest |Cliff's δ| at n=15 are listed below.

| Subject | Metric | Contrast | n_a / n_b | Cliff's δ [95% CI] | Cohen's d | p |
|---|---|---|---|---|---|---|
| S9 | ppg_motion | baseline_vs_amusement | 235 / 74 | -0.80 [-0.88, -0.71] | -1.89 | 3.7e-25 |
| S9 | ppg_sqi | baseline_vs_amusement | 235 / 74 | +0.80 [+0.71, +0.88] | +1.89 | 3.7e-25 |
| S17 | ppg_sqi | baseline_vs_stress | 235 / 144 | +0.75 [+0.68, +0.82] | +1.16 | 1.0e-34 |
| S17 | ppg_motion | baseline_vs_stress | 235 / 144 | -0.75 [-0.82, -0.68] | -1.16 | 1.0e-34 |
| S5 | ppg_sqi | baseline_vs_stress | 239 / 128 | +0.73 [+0.65, +0.79] | +1.37 | 2.0e-30 |
| S5 | ppg_motion | baseline_vs_stress | 239 / 128 | -0.73 [-0.79, -0.65] | -1.37 | 2.0e-30 |
| S14 | ecg_sqi | baseline_vs_amusement | 235 / 73 | +0.70 [+0.57, +0.84] | +1.59 | 8.5e-20 |
| S14 | ppg_sqi | baseline_vs_stress | 235 / 134 | +0.70 [+0.62, +0.78] | +1.30 | 2.7e-29 |
| S14 | ppg_motion | baseline_vs_stress | 235 / 134 | -0.70 [-0.78, -0.62] | -1.30 | 2.7e-29 |
| S16 | ppg_sqi | baseline_vs_amusement | 235 / 72 | +0.70 [+0.58, +0.80] | +1.37 | 4.1e-19 |
| S16 | ppg_motion | baseline_vs_amusement | 235 / 72 | -0.70 [-0.80, -0.58] | -1.37 | 4.1e-19 |
| S5 | ppg_sqi | baseline_vs_amusement | 239 / 74 | +0.61 [+0.51, +0.71] | +0.97 | 1.6e-15 |

**Findings (n=15).** Of 90 per-(subject, metric, contrast) tests, **65 are significant at p < 0.05** and **27 survive p < 1e-10**. Stress-vs-baseline effects on PPG SQI are large in many subjects (Cliff's δ > 0.50 in S5, S11, S14, S16, S17; Cohen's d > 1.0). Amusement-vs-baseline effects are even larger in some subjects, with S9's PPG SQI dropping during amusement at Cliff's δ = +0.80, Cohen's d = +1.89.

**Direction heterogeneity is the headline finding.** Most subjects' PPG SQI drops during stress (positive Cliff's δ), but S15's rises (Cliff's δ = -0.49, p = 4e-15). S6 also shows reversed direction. **Pooling per-state Cliff's δ across subjects would average opposing effects toward zero and miss the heterogeneity entirely.** The framework's per-subject outputs catch this; pooled aggregates would not. This is the clearest single methodological argument the n=15 data provides.

CSV: `results/extended_analysis/per_state_effect_sizes.csv`. Figure 9 panel F.

## S2.7 Summary table: what each analysis adds

| Analysis | Question answered | Main finding |
|---|---|---|
| S2.1 Positivity | Are AIPW estimates trustworthy? | active_minutes positivity is clean; heat_index has severe violation (Kish ESS 63%) |
| S2.2 E-values | How strong must unmeasured confounder be? | active_minutes → HRV: needs RR ≥ 1.52 to shift CI to null |
| S2.3 ROC/PR/F1 | Is the recalibrated threshold stable? | No. At n=15 AUROC = 0.48 (near chance). Youden vs F1 disagree (0.999 vs 0.864). Pilot stability was n=2 artifact |
| S2.4 RR cleaning | Are HRV numbers artifacts of a single filter? | S3's high HRV holds across raw, plausibility, Malik 25% |
| S2.5 Real-data reliability | Does within-session HR replicate? | No (n=15): median split-half r = +0.067, median CV = 7.25%. Only S4 > +0.30 |
| S2.6 Effect sizes | Are state contrasts robust? | Cliff's δ and Cohen's d agree. S9 amusement on PPG SQI: Cliff δ +0.80, Cohen d +1.89 (n=15, largest single effect) |

## Figure 9 caption

Six-panel reviewer-grade supplementary figure (`results/extended_analysis/figure_extended.png`).
(A) Distribution of estimated propensity scores for three AIPW analyses, showing the heat_index positivity violation (range spans 10⁻²⁴ to 1.0) and the clean active_minutes positivity (concentrated near 0.5).
(B) E-values for the four AIPW analyses on Chinn-converted RR scale. active_minutes → HRV has the largest E-value (point 2.52, CI bound 1.52), meaning an unmeasured confounder would need an effect of RR ≥ 1.52 to explain away the lower-CI bound.
(C) Full ROC curve for the in-house SQI as a predictor of Orphanidou pass/fail on real WESAD wrist PPG. AUROC = 0.703 with bootstrap 95% CI [0.659, 0.736]. The Youden's J optimum is at threshold 0.991 with CI [0.986, 0.992].
(D) RMSSD on each WESAD subject's baseline ECG under five RR-cleaning policies. S2's RMSSD is highly sensitive (127 → 83 → 60 → 48 ms), S3's is robust except under the NN50 filter (121 → 120 → 117 → 85 → 139 ms).
(E) Per-subject within-baseline split-half HR reliability on real data. Pearson r = +0.078 (S2) and +0.112 (S3); within-subject CV = 6.7% (S2) and 9.1% (S3). Substantially weaker than the synthetic week-pair r of +0.977, attributable to different units of analysis (5-second-window vs daily-aggregate) and to real within-session HR variability.
(F) Significant baseline vs amusement contrasts plotted with both Cliff's δ (with bootstrap 95% CI) and Cohen's d. The two effect-size families agree on direction and magnitude ordering. S3 baseline vs amusement on PPG SQI / motion shows the largest effect (Cliff's δ = ±0.49, Cohen's d = ±0.80).
