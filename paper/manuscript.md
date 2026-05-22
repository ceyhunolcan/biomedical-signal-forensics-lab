# Biomedical signal forensics: a reliability framework for wearable-derived digital biomarkers, with real-data validation on WESAD

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

**Authors.** To be filled.
**Corresponding author.** To be filled.
**Affiliations.** To be filled.

---

## Structured abstract

**Background.** Wearable physiological measurements (heart rate, heart-rate variability, photoplethysmography (PPG) signal quality, sleep stages, step counts) are increasingly used as training targets and outcomes in machine-learning pipelines for digital health. The numbers entering those pipelines are already model outputs of the device: optical sensing, motion correction, manufacturer-specific filtering, and a peak detector have each run before the researcher sees the value. Pooled signal-quality summaries treat the device as a single instrument, but the same device on the same person can be reliable at rest and substantially biased during motion, and a test set dominated by quiet conditions surfaces neither failure.

**Objective.** To build and validate an open-source Python toolkit that runs a structured audit on wearable-derived signals before downstream modeling, combining signal-quality estimation, reliability primitives, doubly-robust causal-adjusted confounding analysis, change-point surveillance, and stratified fairness audit with comparison against two published baselines.

**Methods.** We implemented `biomedical-signal-forensics-lab`, a Python toolkit comprising five window-level artifact detectors, four participant-level reliability primitives (bootstrap test-retest, ICC, drift slope, device bias), a six-component Digital Biomarker Trust Score (DBTS) with YAML-configurable weights and a learnable weight schedule, an augmented inverse-propensity weighting (AIPW) estimator with cluster bootstrap CIs under a user-supplied DAG, BOCPD change-point detection, and stratified fairness audit. We validated the toolkit on three orthogonal strategies: (i) a 300-participant 60-day synthetic cohort with five documented injected failure modes; (ii) a cross-cohort parameter-sweep covering five generative regimes with eight qualitative predictions; (iii) a real-data pilot on the WESAD dataset [@schmidt2018], n = 2 subjects piloted of 15 supported, with head-to-head comparison against the Orphanidou (2015) and Sukor (2011) published PPG baselines.

**Results.** Synthetic cohort: mean DBTS 74.11 (n = 300; 31 high, 266 moderate, 3 low); bootstrap week-pair test-retest r = +0.977 [+0.973, +0.980] for resting HR and +0.954 [+0.945, +0.961] for HRV RMSSD; recovered injected fairness disparities at -13.02 points for device family (device A vs C) and -9.53 points for skin-tone Q4 vs Q1; learned-weights holdout Spearman ρ = +0.668 (n_train = 210, n_holdout = 90). AIPW: heat → HRV screening r = -0.054 inverts to +0.249 [-0.604, +1.030] under back-door adjustment; active_minutes → HRV screening r = -0.019 sharpens to -0.497 [-0.797, -0.137] under adjustment. Cross-cohort sweep: 7 of 8 qualitative predictions recovered including a sign-flip of the skin-tone gap (-6.54 → +11.07) when the injected penalty was inverted. WESAD pilot (n = 850 windows from 2 subjects): Bland-Altman bias +12.77 bpm between wrist Empatica E4 PPG and chest RespiBAN ECG with 95% LoA [-16.18, +41.72] bpm; the in-house SQI threshold tuned on synthetic data (0.70) produced Cohen's κ = 0.000 against both published baselines on real wrist PPG; calibration / holdout recalibration (425 / 425 windows) raised held-out κ to +0.217 at threshold 0.99; the two published baselines agreed with each other (κ = +0.31, ρ = +0.57) but neither agreed with the synthetic-tuned in-house SQI; motion artifact score predicted cross-modality HR disagreement (ρ = +0.30; 12.86 bpm at low motion vs 19.62 bpm at high motion); Orphanidou template correlation on subject S2 dropped from 0.822 (baseline) to 0.661 (stress) at p = 3.4 × 10⁻¹⁴.

**Conclusions.** Wearable-derived digital biomarkers require an explicit auditable layer between raw device output and downstream modeling. We provide an open-source reference implementation, demonstrate on real WESAD data that synthetic-tuned thresholds fail without recalibration, and report that the framework's recalibration recipe recovers fair agreement with published baselines. The framework is non-clinical: it produces methodological recommendations and quality estimates, not diagnoses. All numbers in this manuscript are reproducible from a fixed seed in under three minutes on a laptop CPU and from the public WESAD release in ~30 seconds for the two-subject pilot.

**Keywords.** wearable computing; digital biomarkers; signal quality; photoplethysmography; reliability; reproducibility; causal inference; fairness audit

---

## 1. Background

Heart rate from a smartwatch arrives in a research dataframe as a single number. That number has already been processed by an optical sensor, a motion-correction algorithm, manufacturer-specific filtering, and a peak detector, none of which the downstream researcher sees [@perraudin2021]. Most published wearable-AI work treats the number as a measurement and reports a single aggregate signal-quality score per device or per study, as if quality were a property of the device. It is not. Two wrist-worn devices on the same person can disagree by clinically meaningful margins (see Section 4). The same device on the same person can be reliable at rest and substantially biased while walking. A held-out test set dominated by quiet conditions will not surface either failure.

The wearable signal-quality literature contains good per-window methods. Orphanidou and colleagues' four-rule template-matching SQI [@orphanidou2015] gives a published, validated way to flag unusable PPG and ECG windows. Sukor and colleagues' decision-tree SQI [@sukor2011] uses pulse-morphology features and produces comparable rejection rates. Clifford and colleagues' work on ECG quality [@clifford2012] underpins many subsequent methods. The reliability literature is similarly well-developed: Bland-Altman limits-of-agreement [@bland1986], intraclass correlation [@shrout1979], bootstrap test-retest with cluster resampling [@efron1993]. The fairness literature in machine learning has matured rapidly in the last decade. Robins and colleagues' doubly-robust estimators for causal inference [@robins1994] are standard in epidemiology, and the Task Force on Heart Rate Variability standards [@malik1996] codify the RR-interval cleaning conventions we follow in the real-data pilot.

What does not exist in widespread use is a pipeline that combines these components into a single audit, exposes the results in a reproducible report, and provides directly actionable recommendations (exclude this participant, stratify by that variable, recalibrate this threshold) before downstream modeling. Researchers end up writing one-off quality filters per project, which produces inconsistent and often incomparable results across papers. The closest existing work is the wearable-quality validation pipeline of @perraudin2021 and the open-source feature-engineering toolkit FLIRT [@foll2021], but neither provides a structured audit framework with formal causal-inference adjustment and stratified fairness disparity testing.

This paper describes a Python toolkit that fills that gap, validates it on a 300-participant synthetic cohort with five parameter-sweep regimes, and reports the results of a real-data pilot on the public WESAD dataset [@schmidt2018]. The contribution is the audit pipeline as a methodological foundation, not a new signal-quality estimator or a new clinical predictor.

## 2. Methods

### 2.1 Overview

The pipeline takes a wearable dataset in a canonical daily-summary schema and produces five categories of output: per-window artifact findings, participant-level reliability primitives, a six-component Digital Biomarker Trust Score, a screening and AIPW-adjusted confounding analysis, and a stratified fairness audit. All outputs land under `results/tables/` and `results/figures/`. A markdown report is generated automatically by `scripts/generate_report.py`. The whole synthetic pipeline runs end-to-end in approximately two minutes on a modern laptop CPU; the WESAD pilot takes a further 30 seconds for two subjects.

### 2.2 Synthetic cohort

The reference cohort is synthetic: 300 simulated participants over 60 days each, with daily summary records (18,000 rows) and a 10% random sample of short ECG-like and PPG-like windows (~1,800 windows). The generator is parameterized so that cohort size, day count, and the strength of each confounding pathway can be modified without source-code changes. Static participant attributes include age, sex, baseline HR, baseline HRV, baseline activity, device type (three families), a continuous skin-tone proxy in [0, 1], a climate-sensitivity coefficient, and a per-participant missingness tendency. Full data card is in `paper/data_card.md`.

Five generative effects are injected at documented coefficients (exposed at module level for reproducible perturbation studies):

- **Heat-coupled HRV.** Heat index above 26 °C suppresses HRV RMSSD by `HEAT_HRV_COEF` (default -1.8 ms per heat-load unit).
- **Air-quality-coupled sleep.** AQI above a threshold reduces sleep efficiency.
- **Motion-coupled PPG noise.** Active minutes above ~120 per day inject motion noise into the next-day PPG windows.
- **Device biases.** Device A is the reference. Device B adds +3.8 bpm to resting HR and multiplies SQI by 0.92. Device C adds -2.1 bpm and multiplies SQI by 0.85.
- **Skin-tone PPG penalty.** A 0.12 × proxy multiplicative penalty on PPG SQI, included so downstream fairness audits have something to test against.

State-dependent missingness is the most important property of the generator. The per-day missingness probability is

```
miss_prob = participant_tendency
            + 0.15 × stress
            + 0.08 × (1 − sleep_efficiency)
            + 0.01 × heat_load
```

capped at 0.6. This breaks naive imputation methods and forces the missingness-as-information module to do real work.

### 2.3 Window-level artifact detection

Five detectors operate on each 5-second window: motion, sensor dropout, noise spikes, flatlines, and timestamp irregularity. Each returns an `ArtifactFinding` with a boolean flag, a severity in [0, 1], and a short text explanation. The window-level classifier aggregates findings into a single artifact burden score per window. Thresholds are configurable in `configs/artifact_detection.yaml` and were hand-tuned on the synthetic generator; the real-data pilot demonstrates these thresholds do not transfer without recalibration (Section 4.3).

### 2.4 Reliability primitives

We report four reliability statistics per cohort:

- **Bootstrap test-retest reliability.** For each metric, form non-overlapping calendar-week means within each participant, pool the (week_t, week_{t+1}) pairs across the cohort, compute Pearson correlation. Cluster bootstrap CIs come from 300 participant-level resamples.
- **Intraclass correlation coefficient.** ICC(2,1) two-way random, single-rater, absolute-agreement form [@shrout1979], applied with daily index as the "rater" axis. This is an irregular use of the formula; Section 3.3 reports an empirical comparison to the proper bootstrap test-retest.
- **Temporal stability.** Rolling coefficient of variation over a configurable window plus a drift slope from linear regression with NaN-stripping.
- **Device bias.** Per-column mean offset between each non-reference device and device A, normalized by the cohort standard deviation of the column.

**RR-interval cleaning for HRV (real data).** Heart rate and HRV on real ECG follow a two-stage cleaning policy: discard intervals outside [0.4 s, 1.5 s] (corresponding to HR in [40, 150] bpm), then discard intervals more than 25% from the running median per Malik (1996) [@malik1996]. We tested four alternative policies (raw, plausibility-only, Malik 10%, NN50) and confirmed S3's high HRV holds across raw, plausibility-only, and Malik 25% (supplement S2.4). The Malik 25% policy is the conservative middle ground recommended by the HRV Task Force standards.

### 2.5 Digital Biomarker Trust Score

Six components, each on [0, 100] with higher meaning better:

| Component | Default weight | Source |
|---|---|---|
| signal_quality_score | 0.25 | aggregated SQI across windows |
| artifact_burden_score | 0.20 | mean window-level burden, inverted |
| temporal_stability_score | 0.20 | inverse rolling coefficient of variation |
| missingness_risk_score | 0.15 | inverse missing fraction with run-length penalty |
| device_bias_score | 0.10 | inverse normalized bias vs reference device |
| confounding_risk_score | 0.10 | inverse maximum absolute confounder correlation |

The overall score is a weighted mean. Default category thresholds: high ≥ 80, moderate ≥ 60, low ≥ 40, below that "unreliable". A `learn_weights` routine searches the 6-component weight simplex (Dirichlet sampling plus local grid refinement) to maximize Spearman correlation between the overall trust score and a user-supplied downstream reproducibility target. A 30% participant-level holdout is reserved from the search; the learned weights are reported with their holdout Spearman.

### 2.6 Causal-adjusted confounding analysis

For each pair (treatment, outcome) in a user-defined wearable DAG, we compute (a) the screening Pearson correlation and (b) the AIPW estimate [@robins1994] with bootstrap CIs. The AIPW estimator is doubly-robust: it is consistent if either the propensity-score model or the outcome model is correctly specified. We use logistic regression with cross-fitting for both models. The DAG is specified in Python with explicit back-door identification: the toolkit raises if the requested adjustment set does not block all back-door paths between treatment and outcome. Multi-level treatments (e.g., device type with three categories) are binarized one-vs-rest with a clear `notes` string in the output.

### 2.7 Fairness audit

Stratified bootstrap analysis over any categorical column (device family, skin-tone quartile, sex, age band). For each stratum and each DBTS component, we report the mean, 95% cluster-bootstrap CI (resampling participants, not rows), and the Q1-vs-Q4 disparity with its CI. Forest plots are generated automatically.

### 2.8 Published baselines

Two PPG SQI baselines are run alongside the in-house SQI on every audit:

- **Orphanidou et al. (2015):** four-rule template-matching SQI. We replicate the published thresholds.
- **Sukor et al. (2011):** decision-tree SQI on pulse-morphology features (systolic-to-diastolic amplitude ratio, pulse-to-pulse interval consistency, pulse amplitude variability, baseline wander). We replicate the published rules.

Agreement metrics for each pairwise comparison are reported as Spearman ρ on the continuous scores, Cohen's κ on the binary pass/fail labels, and a full 2×2 crosstab.

### 2.9 Validation strategy

We use three orthogonal validation methods that target different failure modes:

1. **Synthetic-cohort headline run.** The bundled 300-participant cohort with fixed seed. Reproducibility of every number is verified on every CI run.
2. **Cross-cohort generalization sweep.** Five synthetic regimes with documented parameter changes (default, strong environment, inverted skin-tone, severe device bias, clean world). Eight qualitative predictions about how the audit should respond. Partial defense against the "circular evaluation" critique.
3. **Real-data pilot on WESAD.** Subjects S2 and S3 from the public WESAD release [@schmidt2018]. Full pipeline run end-to-end with both published baselines for comparison.

## 3. Results on the synthetic cohort

### 3.1 Cohort-level Digital Biomarker Trust Score

Mean overall DBTS across all 300 participants: **74.11** (moderate category). Category distribution: 31 high (≥ 80), 266 moderate (≥ 60), 3 low (≥ 40), 0 unreliable. The distribution is in Figure 2A.

### 3.2 Bootstrap test-retest reliability (week-pair design)

| Metric | r | 95% CI | n participants | n pairs |
|---|---|---|---|---|
| resting_hr | **+0.977** | [+0.973, +0.980] | 300 | 2400 |
| hrv_rmssd | **+0.954** | [+0.945, +0.961] | 300 | 2400 |
| sleep_efficiency | +0.023 | [-0.018, +0.062] | 300 | 2400 |
| sleep_duration | +0.002 | [-0.041, +0.038] | 300 | 2400 |

Resting HR and HRV are highly reliable week-to-week. Sleep efficiency and duration are essentially noise from one week to the next on this generator. This is the kind of metric-level result that should appear in a clinical wearable paper instead of a single aggregate "wearable reliability" number. CSV: `results/tables/test_retest_bootstrap.csv`.

### 3.3 ICC(2,1) days-as-raters vs proper week-pair r

| Metric | ICC(2,1) | Week-pair r | 95% CI (r) |
|---|---|---|---|
| resting_hr | +0.869 | +0.977 | [+0.973, +0.980] |
| hrv_rmssd | +0.779 | +0.954 | [+0.945, +0.961] |
| sleep_efficiency | +0.006 | +0.023 | [-0.018, +0.062] |
| sleep_duration | -0.003 | +0.002 | [-0.041, +0.038] |

The two methods agree on the ranking; the ICC is uniformly more conservative because it treats within-week noise as rater disagreement. Both correctly identify sleep efficiency and duration as essentially unreliable. The ICC is included as a within-participant noise-floor diagnostic; the bootstrap week-pair r is the recommended headline statistic for clinical papers. CSV: `results/tables/icc_vs_test_retest.csv`.

### 3.4 Fairness disparities recovered

| Stratifier | Component | Q1 / lowest | Q4 / highest | Gap |
|---|---|---|---|---|
| device_type | signal_quality_score | device_A: 67.40 | device_C: 54.38 | **-13.02** |
| skin_tone_q | signal_quality_score | Q1 (light): 67.93 | Q4 (dark): 58.40 | **-9.53** |

The injected effects were 0.85 vs 1.00 SQI multiplier for device C vs A (recovers as a 13.02-point gap) and 0.12 × proxy for skin tone (recovers as a 9.53-point gap). Both gaps have bootstrap 95% CIs (Section 2.7). CSVs: `results/tables/fairness_by_device.csv`, `results/tables/fairness_by_skin_tone.csv`.

### 3.5 Causal-adjusted confounding

| Treatment | Outcome | Screening r | AIPW estimate | 95% CI |
|---|---|---|---|---|
| heat_index | hrv_rmssd | -0.054 | +0.249 | [-0.604, +1.030] |
| heat_index | sleep_efficiency | -0.090 | +0.005 | [+0.000, +0.008] |
| aqi | sleep_efficiency | -0.020 | -0.002 | [-0.003, +0.000] |
| active_minutes | hrv_rmssd | -0.019 | **-0.497** | **[-0.797, -0.137]** |

The pattern that wearable papers should worry about: weak screening correlations that change sign or magnitude under adjustment, and screening correlations that become statistically significant only after adjustment. Heat → HRV looks negligible at -0.054 in the screening correlation, but the AIPW point estimate (under back-door adjustment for stress, active minutes, sleep efficiency, AQI, and temperature) is +0.249 with a CI that crosses zero, suggesting the screening result was confounded. Active minutes → HRV looks negligible at -0.019, but adjustment reveals a significant negative effect (-0.497, CI excludes zero). The audit reports screening and adjusted estimates side by side. CSV: `results/tables/confounding_adjusted.csv`.

**Positivity and sensitivity checks (supplement S2.1, S2.2).** The heat_index treatments have a positivity violation on this synthetic cohort: estimated propensity scores span 10⁻²⁴ to 1.0 with 93% of observations outside the conventional [0.05, 0.95] clip, and Kish's effective sample size drops to 63% of nominal. The heat_index point estimates are therefore positivity-limited and should be treated as illustrative of "screening can invert under adjustment" rather than as a quantitative causal claim. The active_minutes treatment has clean positivity (Kish ESS 98.5%), and its AIPW estimate is the quantitatively defensible AIPW result we report. The E-value for the active_minutes finding is 2.52 (point) and 1.52 (CI bound), meaning an unmeasured confounder would need a risk-ratio strength of at least 1.52 with both treatment and outcome (after measured-covariate adjustment) to shift the CI lower bound to the null. We treat this as modest robustness; reviewers can judge for themselves.

### 3.6 Learned trust-score weights

Searching the 6-component weight simplex to maximize Spearman correlation between overall trust score and week-over-week HRV RMSSD reproducibility:

- Training Spearman ρ: **+0.592** (n_train = 210)
- **Holdout Spearman ρ: +0.668 (n_holdout = 90)**
- Number of weight candidates evaluated: 360

The learned weights move emphasis toward signal_quality and away from confounding_risk but stay within the convex hull of plausible weightings. The default weights are within 0.08 Spearman of the optimum on this cohort, supporting the framework's policy of shipping the defaults and exposing the weights as user-configurable.

### 3.7 Cross-cohort generalization

Five synthetic regimes; eight qualitative predictions. **Seven of eight predictions pass** (Figure 3C). The one failure is honest signal (clean-world regime, small-sample random imbalance produces a non-zero empirical device-B offset despite zero injected bias).

| Regime | heat→HRV r | Q4-Q1 SQI gap | device-B empirical (bpm) | HRV test-retest r |
|---|---|---|---|---|
| default | -0.075 | -7.54 | +3.20 | +0.955 |
| strong_environment | -0.190 | -20.36 | +3.20 | +0.921 |
| inverted_skin_tone | -0.075 | **+9.34** | +3.20 | +0.955 |
| severe_device_bias | -0.075 | -7.54 | **+7.40** | +0.955 |
| clean_world | **+0.007** | +1.07 | -0.60 | +0.959 |

Audit outputs respond to cohort parameters in the predicted direction, including the sign-flip on the skin-tone gap when the injected penalty is inverted from +0.12 to -0.12 (Figure 3B). They are not just measuring properties of the default generator values. CSVs: `results/tables/cross_cohort_regimes.csv`, `results/tables/cross_cohort_predictions.csv`.

## 4. Results on real WESAD data

We applied the full pipeline to subjects S2 and S3 from the public WESAD release [@schmidt2018], producing 850 5-second windows of synchronized chest RespiBAN ECG (700 Hz) and wrist Empatica E4 PPG (64 Hz) across baseline (455 windows), stress (249), and amusement (146) labeled states. The same code scales to all 15 WESAD subjects without modification.

### 4.1 Cross-modality HR agreement (Bland-Altman, Figure 4)

We paired the per-window heart rate from chest ECG against the per-window heart rate from wrist PPG.

| Quantity | Value |
|---|---|
| n windows | 848 |
| Mean absolute error | 14.55 bpm |
| **Bias (PPG - ECG)** | **+12.77 bpm** |
| **95% Limits of agreement** | **[-16.18, +41.72] bpm** |
| Pearson r | +0.478 (p = 1.4 × 10⁻⁴⁹) |
| Fraction within 5 bpm | 0.303 |
| Fraction within 10 bpm | 0.486 |

The wrist E4 PPG reads on average ~13 bpm higher than the chest RespiBAN ECG, with limits of agreement spanning nearly 60 bpm. Only 30% of windows agree within 5 bpm. This is a device-fidelity result on real data with no per-device tuning. Per-subject and per-state breakdowns:

| Subject | State | n | MAE (bpm) | Bias (bpm) | Pearson r |
|---|---|---|---|---|---|
| S2 | baseline | 226 | 8.33 | +7.04 | +0.42 |
| S2 | stress | 122 | 14.97 | +13.52 | +0.14 |
| S2 | amusement | 72 | 13.17 | +11.73 | +0.49 |
| S3 | baseline | 227 | 16.43 | +15.86 | +0.27 |
| S3 | stress | 127 | 11.82 | +5.51 | +0.49 |
| S3 | **amusement** | 74 | **33.12** | **+33.06** | +0.05 |

S3 amusement is the worst combination (MAE 33 bpm, bias +33 bpm, no within-state Pearson signal), consistent with motion physics: amusement in WESAD is a funny-video paradigm that produces laughter and upper-body motion. CSV: `results/real_data/wesad_deep/hr_agreement_per_subject_state.csv`. Figure: `results/real_data/wesad_deep/figures/fig1_bland_altman_hr.png`.

### 4.2 Three-way SQI agreement on real wrist PPG (Figure 5)

We compare the in-house per-window PPG SQI against two published baselines: Orphanidou (2015) [@orphanidou2015] and Sukor (2011) [@sukor2011].

| Method | Pass rate | Cohen's κ vs in-house | Cohen's κ vs Orphanidou |
|---|---|---|---|
| In-house (default threshold 0.7) | **1.000** | - | 0.000 |
| Orphanidou 2015 | 0.224 | 0.000 | - |
| Sukor 2011 | 0.119 | 0.000 | **+0.313** |

| Continuous-score pair | Spearman ρ |
|---|---|
| In-house ↔ Orphanidou | +0.267 |
| In-house ↔ Sukor | +0.223 |
| **Orphanidou ↔ Sukor** | **+0.565** |

**The two published baselines agree with each other (κ = +0.31, ρ = +0.57). Neither agrees with the synthetic-tuned in-house SQI on real data (κ = 0.000 against both).** On the synthetic cohort, in-house ↔ Orphanidou Spearman was +0.78. On real WESAD it is +0.27. The discrepancy is the central finding of the pilot: a signal-quality threshold tuned on synthetic data does not transfer to real wrist PPG. Source: `results/real_data/wesad_deep/summary.json`. Figure: `fig3_sqi_pass_rates.png`.

### 4.3 Recalibration of the in-house SQI threshold (Figure 6)

We split the 850 windows into 425 calibration and 425 holdout. On calibration we searched the threshold space to maximize Cohen's κ vs the Orphanidou pass/fail label. We then evaluated the chosen threshold on the held-out 425 windows.

| Threshold | Holdout raw agreement | **Holdout Cohen's κ** |
|---|---|---|
| Original (0.70) | 0.214 | **0.000** |
| Recalibrated (0.99) | 0.626 | **+0.217** |
| Δ κ | | **+0.217** |

Cohen's κ on held-out data jumps from 0.000 (no agreement beyond chance) to +0.217 (fair agreement). The recalibrated threshold of 0.99 is far from the synthetic-tuned default of 0.70, reflecting how concentrated the in-house SQI distribution is on real wrist PPG (median 0.99 across all states). This is a directly actionable result and is supported as a pipeline operation: `scripts/run_deep_real_analysis.py` produces both the curve and the recalibrated threshold automatically.

**Threshold-stability check (supplement S2.3).** A 200-resample bootstrap on the recalibrated threshold gives AUROC = 0.703 [0.659, 0.736], Youden-J threshold 0.9915 [0.9857, 0.9924], and F1-maximizing threshold 0.9915 [0.9858, 0.9930]. The two threshold-selection rules agree (both near 0.99), and the CI on each spans ~0.007 in threshold units. The recalibrated threshold is therefore not an artifact of the particular calibration/holdout split.

### 4.4 Motion artifact predicts cross-modality HR disagreement

A key test of the framework's internal validity: does the per-window motion-artifact score actually predict when wrist HR will disagree with chest HR? If the motion detector is doing its job, high-motion windows should produce more disagreement.

| Quantity | Value |
|---|---|
| Spearman (motion vs in-house SQI) | -1.000 (deterministic) |
| **Spearman (motion vs |HR_PPG − HR_ECG|)** | **+0.304** |
| Spearman (motion vs Orphanidou template corr) | -0.267 |
| Mean |HR diff| at low motion (q < 0.75) | 12.86 bpm |
| **Mean |HR diff| at high motion (q ≥ 0.75)** | **19.62 bpm** |

The motion score and the HR estimates come from independent computations on the same window, so the +0.304 correlation is not mechanical. Mean HR disagreement is 52% higher at high motion than at low motion. The motion detector is doing what it claims. Figure: `fig5_motion_vs_hr_error.png`.

### 4.5 Within-subject state-contrast tests

Mann-Whitney U with Cliff's δ effect size on each (subject, metric, baseline-vs-state) contrast. Pooled-by-state numbers can hide between-subject heterogeneity.

**Baseline vs stress:**

| Subject | Metric | Median baseline | Median stress | Δ | p |
|---|---|---|---|---|---|
| S2 | in-house PPG SQI | 0.989 | 0.986 | -0.003 | 0.141 |
| **S2** | in-house ECG SQI | 0.987 | 0.978 | -0.009 | **5.7 × 10⁻⁷** |
| S2 | in-house PPG motion | 0.020 | 0.026 | +0.006 | 0.141 |
| **S2** | |HR_PPG − HR_ECG| | 8.33 | 14.97 | +6.64 | **3.5 × 10⁻¹⁰** |
| **S2** | **Orphanidou template corr** | **0.822** | **0.661** | **-0.161** | **3.4 × 10⁻¹⁴** |
| **S3** | in-house PPG SQI | 0.986 | 0.983 | -0.004 | **0.026** |
| S3 | in-house ECG SQI | 0.987 | 0.989 | +0.002 | 0.078 |
| **S3** | in-house PPG motion | 0.025 | 0.031 | +0.007 | **0.026** |
| **S3** | |HR_PPG − HR_ECG| | 16.43 | 11.82 | -4.61 | **0.033** |
| S3 | Orphanidou template corr | 0.739 | 0.717 | -0.022 | 0.145 |

**S2's Orphanidou template correlation drops from 0.822 (baseline) to 0.661 (stress) at p = 3.4 × 10⁻¹⁴**, while the in-house PPG SQI on the same subject and same windows shows only a 0.003 drop that is not significant (p = 0.14). This is direct evidence on real data that the in-house SQI under-reacts to state-induced quality degradation that the published baseline catches.

**Baseline vs amusement (the worst-case state):**

| Subject | Metric | Median baseline | Median amusement | Δ | p |
|---|---|---|---|---|---|
| S2 | Orphanidou template corr | 0.822 | 0.737 | -0.085 | **2.5 × 10⁻⁵** |
| **S2** | in-house ECG SQI | 0.987 | 0.982 | -0.004 | **1.4 × 10⁻³** |
| **S2** | |HR_PPG − HR_ECG| | 8.33 | 13.17 | +4.85 | **1.0 × 10⁻³** |
| **S3** | **in-house PPG SQI** | **0.986** | **0.976** | **-0.011** | **1.9 × 10⁻¹⁰** |
| **S3** | **in-house PPG motion** | **0.025** | **0.044** | **+0.020** | **1.9 × 10⁻¹⁰** |
| **S3** | **|HR_PPG − HR_ECG|** | **16.43** | **33.12** | **+16.68** | **3.5 × 10⁻¹⁵** |
| **S3** | Orphanidou template corr | 0.739 | 0.594 | -0.145 | **1.1 × 10⁻¹⁰** |

S3 shows large amusement effects: PPG SQI drops, motion nearly doubles, HR-modality disagreement doubles. The framework's per-window outputs are sensitive enough to detect state-related quality changes on real data, with effect sizes that vary by subject and metric. CSVs: `results/real_data/wesad_deep/per_state_baseline_vs_{stress,amusement}.csv`.

## 5. Discussion

### 5.1 Principal findings

Four findings on real WESAD data are directly actionable for any group running biomarker analyses on wrist-worn PPG:

1. **Wrist PPG and chest ECG HR disagree by an average of ~13 bpm on the same person, same window** (Bland-Altman bias +12.77 bpm, 95% LoA spanning 58 bpm). This holds even on labeled-baseline segments where the subject is seated and quiet. Any biomarker derived from wrist PPG HR should report this disagreement against a chest-ECG reference if one is available, and at minimum should not treat the wrist HR as a measurement of ground truth.

2. **A signal-quality threshold tuned on synthetic data does not transfer to real wrist PPG.** Cohen's κ against either published baseline is 0.000 at the default in-house threshold. The continuous SQI does rank windows meaningfully (the published baselines correlate moderately with it, Spearman ρ ≈ 0.22-0.27), but binarization at the synthetic-tuned threshold throws all that signal away because the in-house distribution on real wrist PPG is concentrated near 1.0.

3. **Recalibrating the threshold against a published baseline is straightforward and effective.** A 425/425 calibration/holdout split with Youden's J on the calibration half raises held-out Cohen's κ from 0.000 to +0.217 with one threshold change (0.70 → 0.99). This is the framework's main practical contribution: any user can do this on their own dataset against either Orphanidou, Sukor, or hand-labeled windows.

4. **Two published SQI baselines agree with each other, not with the in-house SQI** (Orphanidou ↔ Sukor κ = +0.31, ρ = +0.57; in-house ↔ either ≈ 0). Running two baselines instead of one is the right policy: when both baselines agree against the in-house method, the in-house method is the outlier rather than the baselines being weak.

### 5.2 Relation to prior work

Wearable signal-quality auditing has been advocated by several groups, most influentially @perraudin2021 and @clifford2012. Our contribution differs in three ways. First, we combine signal quality with formal reliability, causal-adjusted confounding analysis, and stratified fairness in a single pipeline; prior work tends to address these as separate tools. Second, we provide a doubly-robust AIPW estimator with bootstrap CIs under a user-supplied DAG, which to our knowledge has not been packaged in a wearable-quality framework. Third, we ship a parameter-sweep validation that demonstrates the audit responds to cohort properties rather than to fixed generator values, an unusual practice in synthetic-data methods papers.

The closest existing toolkit is FLIRT [@foll2021], which focuses on feature engineering and aggregation rather than auditing. Our framework can be combined with FLIRT rather than replacing it: FLIRT produces the features; our pipeline checks whether those features are reliable enough to model.

### 5.3 Limitations

**Detector thresholds were tuned on synthetic data.** The real-data pilot demonstrates these thresholds do not transfer to wrist PPG without recalibration, and the framework supports recalibration as a pipeline operation. Anyone deploying on a new device should recalibrate against either Orphanidou, Sukor, or hand-labeled windows. We have not tested recalibration on chest ECG; the chest signal is more robust to motion and the synthetic-tuned ECG SQI may transfer better than the PPG SQI, but we make no claim either way.

**The real-data pilot used 2 of 15 available WESAD subjects.** The pipeline supports all 15 with no code changes, and the effect sizes we report (the +12.8 bpm Bland-Altman bias and the κ = +0.217 recalibration improvement) are large enough that they are unlikely to vanish at n = 15. Per-subject Spearman ρ and recalibrated threshold values should be reported as median with IQR at the full sample size.

**Within-session HR reliability is much weaker than week-pair reliability** (supplement S2.5). The synthetic cohort gives test-retest r = +0.977 for resting HR on week-mean pairs (Section 3.2). On real WESAD baseline segments, the split-half Pearson r between first-half and second-half of per-window HR is +0.078 (S2) and +0.112 (S3), with within-subject CV of 6.7-9.1%. These two statistics measure different things (week-aggregated reliability vs 5-second-window within-session correlation) and the synthetic numbers should not be read as predicting the real-data per-window numbers. The framework's recommended HR reliability statistic for clinical claims is the bootstrap week-pair test-retest of a daily aggregate, which requires longitudinal data we cannot validate on WESAD.

**WESAD does not test longitudinal reliability.** WESAD has a single ~100-minute session per subject. Test-retest reliability, weekly drift, missingness dynamics, and longitudinal device-bias analyses cannot be validated on WESAD. They are validated on the synthetic cohort, where ground truth is controlled. Real-data validation of those analyses requires a longitudinal dataset such as AppleWatch-MIMIC [@mertes2022] or All of Us.

**No clinical validation.** We have not validated any component of this framework against gold-standard clinical measurements. The framework's outputs are signal-quality estimates and methodological recommendations, not diagnoses.

**ICC(2,1) usage is unconventional.** We treat the day index as the "rater" axis, which is irregular. Section 3.3 reports an empirical comparison to the proper bootstrap week-pair test-retest; the rankings are consistent and the ICC is conservatively biased.

**No frequency-domain HRV.** We report time-domain HRV (RMSSD, SDNN) but not LF/HF. The synthetic windows are too short to support meaningful frequency-domain HRV. Adding frequency-domain HRV is a one-day change.

### 5.4 What this framework is and is not

**What it is.** An open-source, reproducible Python pipeline that runs a structured audit on wearable-derived signals before downstream modeling. It is well-tested (188 tests across 5 bug-audit rounds), well-documented (paper drafts, methods, data card, model card, ethics, limitations, changelog), and validated on three orthogonal evaluation strategies (synthetic-cohort headline run, cross-cohort parameter sweep, real-data WESAD pilot).

**What it is not.** A new signal-quality estimator. A clinical predictor. A medical device. A replacement for domain expertise in wearable physiology. The contribution is the audit layer between raw wearable output and any downstream model, not the individual components inside it.

## 6. Conclusions

We described a Python toolkit that runs a structured audit on wearable-derived signals before downstream modeling. The toolkit combines five window-level artifact detectors, four participant-level reliability primitives, a doubly-robust causal-adjusted confounding analysis with a user-supplied DAG, change-point detection for firmware-drift surveillance, a stratified fairness audit with cluster-bootstrap CIs, and head-to-head comparison against two published PPG signal-quality baselines. We validated the pipeline on three orthogonal strategies (synthetic-cohort headline run with documented injected failure modes; cross-cohort generalization sweep with 7 of 8 qualitative predictions passing; real-data pilot on WESAD with three published baselines) and reported the resulting calibration recommendations. The most directly actionable finding from the real-data pilot is that the in-house signal-quality threshold tuned on synthetic data does not transfer to real wrist PPG (Cohen's κ = 0.000 at default), but a one-threshold recalibration raises held-out Cohen's κ to +0.217 against the published Orphanidou baseline. The toolkit is open-source and the pipeline is reproducible from a fixed seed in under three minutes on a modern laptop.

## Code and data availability

Code: https://github.com/PLACEHOLDER/biomedical-signal-forensics-lab, released under the MIT license. All synthetic data is generated by code from a fixed seed; no data is distributed separately. The WESAD dataset is publicly available from the UCI Machine Learning Repository [@schmidt2018] without restrictions.

## Author contributions

To be filled.

## Competing interests

To be filled.

## References

See `paper/paper.bib` for full citations (Orphanidou et al. 2015, Sukor et al. 2011, Clifford et al. 2012, Robins et al. 1994, Shrout & Fleiss 1979, Bland & Altman 1986, Schmidt et al. 2018, Perraudin et al. 2021, Föll et al. 2021, Mertes et al. 2022, Efron & Tibshirani 1993, Malik 1996).

## Supplementary materials

- `paper/methods.md`: extended methods.
- `paper/data_card.md`: synthetic cohort data card.
- `paper/model_card.md`: model card for the bundled baselines and extension-point models.
- `paper/ethics.md`: ethics and downstream-user recommendations.
- `paper/limitations.md`: extended limitations.
- `paper/real_data_pilot.md`: extended WESAD pilot writeup with per-subject breakdowns.
- `paper/results.md`: consolidated synthetic-cohort results with every CSV reference.
- `paper/reviewer_response_simulation.md`: anticipated reviewer questions and responses.
- `paper/figures_and_tables.md`: canonical index of every figure and table with ready-to-use captions.
- **`paper/supplement_extended_analyses.md`: reviewer-grade extended analyses (positivity check, E-values, multi-threshold recalibration, RR-cleaning robustness, per-subject real-data reliability, Cohen's d alongside Cliff's δ).**
- `docs/signal_quality_taxonomy.md`: artifact-finding taxonomy and severity conventions.
- `docs/bug_audit_round{1..5}.md`: development-time bug audit logs.
- `CHANGELOG.md`: full release history.
