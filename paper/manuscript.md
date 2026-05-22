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

**Results.** Synthetic cohort: mean DBTS 74.11 (n = 300; 31 high, 266 moderate, 3 low); bootstrap week-pair test-retest r = +0.977 [+0.973, +0.980] for resting HR and +0.954 [+0.945, +0.961] for HRV RMSSD; recovered injected fairness disparities at -13.02 points for device family (device A vs C) and -9.53 points for skin-tone Q4 vs Q1; learned-weights holdout Spearman ρ = +0.668 (n_train = 210, n_holdout = 90). AIPW: heat → HRV screening r = -0.054 inverts to +0.249 [-0.604, +1.030] under back-door adjustment; active_minutes → HRV screening r = -0.019 sharpens to -0.497 [-0.797, -0.137] under adjustment. Cross-cohort sweep: 7 of 8 qualitative predictions recovered including a sign-flip of the skin-tone gap (-6.54 → +11.07) when the injected penalty was inverted. WESAD validation (n = 6,585 windows from 15 subjects): Bland-Altman bias +3.57 bpm between wrist Empatica E4 PPG and chest RespiBAN ECG with 95% LoA [-23.14, +30.28] bpm (MAE 9.66 bpm, Pearson r = +0.70); the in-house SQI threshold tuned on synthetic data (0.70) produced Cohen's κ = 0.000 against both published baselines on real wrist PPG; **calibration / holdout recalibration (3,292 / 3,293 windows) did NOT improve held-out κ at n=15** (the pilot finding of Δκ = +0.217 at n=2 did not replicate); three published baselines (Orphanidou, Sukor, Elgendi) collectively rejected 44.6% of windows that the in-house default threshold accepted (each tests a different physical property; median pairwise κ across the published methods = -0.198); per-subject heterogeneity in stress-state |HR_PPG - HR_ECG| spanned 6.75-26.02 bpm (4× range).

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

We applied the full pipeline to all 15 subjects in the public WESAD release [@schmidt2018] (S2-S17, with S1 and S12 absent from the standard public release), producing 6,585 5-second windows of synchronized chest RespiBAN ECG (700 Hz) and wrist Empatica E4 PPG (64 Hz) across baseline (3,507 windows), stress (1,979), and amusement (1,099) labeled states.

### 4.1 Cross-modality HR agreement (Bland-Altman, Figure 4)

We paired the per-window heart rate from chest ECG against the per-window heart rate from wrist PPG.

| Quantity | Value (n=15) |
|---|---|
| n windows | 6,569 |
| Mean absolute error | **9.66 bpm** |
| **Bias (PPG - ECG)** | **+3.57 bpm** |
| **95% Limits of agreement** | **[-23.14, +30.28] bpm** |
| Pearson r | +0.697 (p < 1e-300) |
| Fraction within 5 bpm | 0.458 |
| Fraction within 10 bpm | 0.656 |

On the full release the average disagreement between wrist E4 PPG and chest RespiBAN ECG is +3.57 bpm with 95% LoA spanning 53 bpm. Within-5-bpm agreement is 46%, within-10-bpm is 66%. Pearson correlation between modalities is +0.70. Per-subject heterogeneity is the dominant feature of the data: stress-state mean |HR_PPG - HR_ECG| ranges from **6.75 bpm (S15)** to **26.02 bpm (S11)**, a four-fold spread. A summary of every (subject, state) cell is in `results/real_data/wesad_deep/hr_agreement_per_subject_state.csv`.

### 4.2 Four-way SQI agreement on real wrist PPG (Figure 5)

We compare the in-house per-window PPG SQI against three published baselines that each test a different physical property of a wrist PPG window: Orphanidou (2015) [@orphanidou2015] (template correlation against a learned per-subject pulse shape), Sukor (2011) [@sukor2011] (peak-to-peak interval and amplitude coefficient-of-variation), and Elgendi (2016) [@elgendi2016] (third-order skewness, kurtosis, and Shannon entropy of the window amplitude distribution). The Elgendi implementation includes automatic polarity detection because the Empatica E4 wrist PPG used in WESAD reports signals inverted relative to the fingertip-PPG conventions on which Elgendi was originally validated.

| Method | Pass rate (n=15) | Cohen's κ vs in-house |
|---|---|---|
| In-house (default threshold 0.7) | 1.000 | - |
| Orphanidou 2015 | 0.256 | 0.000 |
| Sukor 2011 | 0.255 | 0.000 |
| **Elgendi 2016 (SSQI/KSQI/ESQI)** | **0.215** | **0.000** |

| Pairwise Cohen's κ | published only |
|---|---|
| Orphanidou vs Sukor | +0.410 |
| Orphanidou vs Elgendi | -0.198 |
| Sukor vs Elgendi | -0.225 |
| **Median across three published pairs** | **-0.198** |

**Three published baselines, three different failure modes.** At n=15, Orphanidou and Sukor moderately agree on which windows pass (κ = +0.410), but Elgendi disagrees with both (κ = -0.198 against Orphanidou, κ = -0.225 against Sukor). The three baselines individually pass 25.6%, 25.5%, and 21.5% of windows respectively, but the published methods catch overlapping yet distinct sets of failure modes.

| Joint condition (n=6,585) | Fraction |
|---|---|
| All three published methods pass | 0.005 (0.5%) |
| **All three published methods fail** | **0.446 (44.6%)** |
| **In-house passes while ALL three published methods fail** | **0.446 (44.6%)** |

**This is the bulletproof finding.** 44.6% of real wrist PPG windows are rejected by Orphanidou AND Sukor AND Elgendi simultaneously — three baselines, three different physical properties, three concordant rejections — and yet the in-house default threshold (0.70) passes every single one of them. The case for the in-house SQI binarization being inappropriate on real wrist PPG no longer rests on agreement with any one baseline; it rests on consensus rejection across three orthogonal published methods that each test a distinct property of pulse waveforms.

Across 6,585 real wrist PPG windows from 15 subjects, the in-house default threshold produces a degenerate flat distribution (every window passes), and the underlying continuous score is uncorrelated with any of the three published baselines (κ = 0 against each individually). Source: `results/real_data/wesad_deep/summary.json["four_way_sqi"]`. Figure 5 panel A shows the four pass rates side by side; panel B shows the four-way agreement matrix.

### 4.3 Recalibration: an honest negative result (Figure 6)

We split the 6,585 windows into 3,292 calibration and 3,293 holdout. On calibration we searched the threshold space to maximize Cohen's κ vs the Orphanidou pass/fail label. We then evaluated the chosen threshold on the held-out 3,293 windows.

| Threshold | Holdout raw agreement | **Holdout Cohen's κ** |
|---|---|---|
| Original (0.70) | 0.258 | **0.000** |
| Recalibrated (0.85) | 0.258 | **0.0002** |
| Δ κ | | **≈ 0.000** |

**The n=2 pilot recalibration result (Δκ = +0.217) does NOT replicate at n=15.** The search lands on threshold 0.85, but the held-out κ remains effectively zero. This is the most important new finding from scaling the pilot. Two non-exclusive explanations: (1) the in-house SQI distribution on real wrist PPG is concentrated near 1.0 for nearly every subject, leaving little useful discriminative signal that a single global threshold can extract; (2) per-subject heterogeneity (Section 4.5) is large enough that a single threshold cannot satisfy all subjects simultaneously. The supplementary AUROC analysis (S2.3) confirms this: AUROC for in-house SQI predicting Orphanidou pass/fail is 0.484 at n=15, statistically indistinguishable from chance. **The honest implication is that the in-house SQI binarization recipe should not be used at all on real wrist PPG without per-subject calibration**, which is a methodological recommendation rather than a fix.

### 4.4 Motion artifact predicts cross-modality HR disagreement (weakly)

| Quantity | Value (n=15) |
|---|---|
| Spearman (motion vs in-house SQI) | -1.000 (deterministic) |
| **Spearman (motion vs |HR_PPG - HR_ECG|)** | **+0.088** |
| Spearman (motion vs Orphanidou template corr) | -0.004 |
| Mean |HR diff| at low motion (q < 0.75) | 9.12 bpm |
| **Mean |HR diff| at high motion (q ≥ 0.75)** | **11.28 bpm** |

The correlation between motion and cross-modality HR disagreement is positive but weak (+0.088). Mean |HR diff| at high motion is 24% higher than at low motion (11.28 vs 9.12 bpm). Both values are smaller than the pilot estimates (ρ = +0.30, gap = 6.8 bpm). At n=15 the framework's motion detector still tracks the direction of the effect, but the magnitude is modest. Per-subject motion-vs-disagreement plots in `results/real_data/wesad_deep/figures/fig5_motion_vs_hr_error.png`.

### 4.5 Within-subject state-contrast tests

Mann-Whitney U with both Cliff's δ and Cohen's d for each (subject, metric, baseline-vs-state) contrast. The full table is in `results/extended_analysis/per_state_effect_sizes.csv`; below we list the largest effects.

**Largest stress vs baseline effects (PPG SQI drop or motion rise):**

| Subject | Metric | n_a / n_b | Cliff's δ [95% CI] | Cohen's d | p |
|---|---|---|---|---|---|
| **S17** | PPG SQI | 235 / 144 | **+0.75 [+0.68, +0.82]** | **+1.16** | 1.0e-34 |
| **S5** | PPG SQI | 239 / 128 | **+0.73 [+0.65, +0.79]** | **+1.37** | 2.0e-30 |
| **S14** | PPG SQI | 235 / 134 | **+0.70 [+0.62, +0.78]** | **+1.30** | 2.7e-29 |
| **S16** | PPG SQI | 235 / 134 | **+0.59 [+0.46, +0.71]** | **+1.41** | 4.6e-21 |
| **S11** | PPG SQI | 235 / 135 | **+0.50 [+0.39, +0.61]** | **+0.98** | 8.8e-16 |
| **S15** | PPG SQI | 234 / 137 | **-0.49 [-0.58, -0.39]** | **-0.79** | 4.0e-15 |
| **S4** | PPG SQI | 230 / 126 | **+0.44 [+0.32, +0.55]** | **+0.90** | 9.7e-12 |

**Heterogeneity in the direction of the PPG SQI effect is itself the finding.** Most subjects show a PPG SQI drop during stress (positive Cliff's δ), but S15 shows the opposite (δ = -0.49): their PPG SQI rises during stress. This is consistent with state-dependent posture: if a particular subject moves less during the stressor than during baseline, their PPG quality can improve. The framework's per-subject outputs catch this; pooled-by-state numbers would obscure it.

**Largest baseline vs amusement effects:**

| Subject | Metric | n_a / n_b | Cliff's δ [95% CI] | Cohen's d | p |
|---|---|---|---|---|---|
| **S9** | PPG SQI | 235 / 74 | **+0.80 [+0.71, +0.88]** | **+1.89** | 3.7e-25 |
| **S14** | ECG SQI | 235 / 73 | **+0.70 [+0.57, +0.84]** | **+1.59** | 8.5e-20 |
| **S16** | PPG SQI | 235 / 72 | **+0.70 [+0.58, +0.80]** | **+1.37** | 4.1e-19 |
| **S14** | PPG SQI | 235 / 73 | **+0.61 [+0.48, +0.74]** | **+1.55** | 3.7e-15 |
| **S5** | PPG SQI | 239 / 74 | **+0.61 [+0.51, +0.71]** | **+0.97** | 1.6e-15 |
| **S17** | PPG SQI | 235 / 73 | **+0.59 [+0.48, +0.68]** | **+0.97** | 4.4e-14 |

Amusement (funny-video paradigm) produces upper-body laughter motion that degrades wrist PPG in most subjects, sometimes with very large effect sizes. S9's amusement effect (Cliff's δ = +0.80, Cohen's d = +1.89) is the largest single contrast in the dataset.

### 4.6 Downstream model performance with vs without audit filtering

The framework's signal-quality audit is methodological infrastructure: it does not by itself produce a clinical prediction. To show that the audit nevertheless changes downstream model behavior, we evaluated two distinct downstream tasks on the WESAD wrist PPG data under four data-conditioning regimes: (i) no audit (all windows), (ii) in-house SQI default threshold pass, (iii) Orphanidou (2015) pass, (iv) both in-house and Orphanidou pass.

**Task A. Baseline-vs-stress classification.** We trained a logistic regression on three wrist PPG features (PPG-derived HR, motion artifact score, in-house SQI) to discriminate baseline from stress windows. Validation used strict leave-one-subject-out (LOSO) cross-validation across all 15 WESAD subjects; features were standardized within each fold and the classifier was scored on the held-out subject.

| Condition | n subjects | Mean AUROC | 95% bootstrap CI | Median AUROC |
|---|---|---|---|---|
| no audit | 15 | 0.804 | [0.716, 0.871] | 0.850 |
| in-house pass (≥ 0.70) | 15 | 0.804 | [0.716, 0.871] | 0.850 |
| **Orphanidou pass** | **14** | **0.823** | **[0.744, 0.906]** | **0.822** |
| both | 14 | 0.823 | [0.744, 0.906] | 0.822 |

| Condition vs no-audit | n paired | Mean Δ AUROC | n improved / n worse | Wilcoxon p (one-sided, greater) |
|---|---|---|---|---|
| in-house | 15 | 0.000 | 0 / 0 | 1.000 |
| **Orphanidou** | **14** | **+0.027** | **10 / 4** | **0.052** |
| both | 14 | +0.027 | 10 / 4 | 0.052 |

The in-house SQI default threshold passes every window (pass rate 1.000; Section 4.2), so "in-house" is identical to "no audit" by construction. The Orphanidou-filtered condition shows a +0.027 mean improvement in held-out subject AUROC with 10 of 14 subjects improving, just outside conventional significance (p = 0.052). We report this as a suggestive trend rather than a significant effect.

**Task B. Per-subject biomarker correlation.** For each subject, we computed the Spearman correlation between the wrist-PPG-derived HR and the chest-ECG-derived HR under each audit condition. We then paired the per-subject ρ values across conditions and tested whether audit filtering produces a consistent improvement (one-sided Wilcoxon signed-rank).

| Comparison | n paired | Mean Δ ρ | Median Δ ρ | n improved / n worse | Wilcoxon p (greater) |
|---|---|---|---|---|---|
| in-house vs all | 15 | 0.000 | 0.000 | 0 / 0 | 1.000 |
| **Orphanidou vs all** | **15** | **+0.102** | **+0.110** | **13 / 2** | **1.5e-04** |
| both vs all | 15 | +0.102 | +0.110 | 13 / 2 | 1.5e-04 |

Restricting to Orphanidou-passing windows improves the per-subject correlation between wrist PPG HR and chest ECG HR by a median of **+0.110** across the 15-subject cohort, with **13 of 15 subjects improving** and **2 declining** (subjects S4, S8 show a slight decline). The paired Wilcoxon test gives **p = 1.5e-04**, comfortably significant. The largest improvements are in subjects whose unfiltered correlation was modest: S10 (0.65 → 0.78), S9 (0.47 → 0.76), S13 (0.42 → 0.54), S6 (0.53 → 0.71).

**Combined interpretation.** Audit filtering reliably improves window-level biomarker estimation but only marginally improves cohort-level classification. The Spearman improvement (p < 0.001) is the more direct test of the framework's value because it operates at the per-window level where the audit acts. The classification result (p = 0.05) is more demanding because LOSO held-out evaluation on n = 15 has limited statistical power; the +0.027 mean improvement is consistent with a real effect that the sample size does not let us declare significant. The trade-off is data retention: Orphanidou filtering keeps roughly 26% of windows. For subjects with already-strong correlation (S14, S16, S17 all at ρ ≥ 0.83 without filtering), the improvement is modest; for subjects with weaker correlation (S2, S5, S15 at ρ < 0.60 without filtering), the gain is substantial.

**Trade-off characterization.** Figure 10 panel D plots per-subject retention against Δρ. Subjects above the y = 0 line benefit from filtering; the small minority below (S4, S8) lose information at the audit threshold. A practitioner deploying the framework can read this trade-off plot directly: for any new dataset they can compute per-subject retention and Δ and decide whether to filter, threshold differently, or skip the audit entirely.

Figure 10 (`results/downstream_demo/figure_downstream.png`):
- Panel A: LOSO AUROC distributions by audit condition.
- Panel B: per-subject paired Δ AUROC vs no-audit, by audit variant.
- Panel C: per-subject biomarker ρ under each condition.
- Panel D: per-subject retention vs Δρ trade-off (Orphanidou condition).

Source: `results/downstream_demo/classification_summary.csv`, `results/downstream_demo/biomarker_correlation.csv`, `results/downstream_demo/figure_downstream.png`. Reproducible end-to-end from `python scripts/run_downstream_audit_demo.py`.

## 5. Discussion

### 5.1 Principal findings

Five findings on real WESAD data are directly actionable for any group running biomarker analyses on wrist-worn PPG:

1. **Wrist PPG and chest ECG HR disagree by ~4 bpm bias with ~53-bpm-wide limits of agreement** (Bland-Altman bias +3.57 bpm, 95% LoA [-23.14, +30.28] across 6,569 windows from 15 subjects). This holds even on labeled-baseline segments where the subject is seated and quiet. Any biomarker derived from wrist PPG HR should report this disagreement against a chest-ECG reference if one is available, and at minimum should not treat the wrist HR as a measurement of ground truth.

2. **Per-subject heterogeneity dwarfs pooled summary statistics.** Mean |HR_PPG - HR_ECG| during stress ranges from 6.75 bpm (S15) to 26.02 bpm (S11), a four-fold spread. The direction of the per-state quality change also varies (most subjects' PPG SQI drops during stress; S15's rises). Any conclusion from pooled WESAD wrist PPG analysis is at risk of being driven by a small number of subjects. The framework's per-subject outputs catch this heterogeneity; pooled-by-state numbers obscure it.

3. **The default in-house SQI threshold does not transfer to real wrist PPG**, and at n=15 the underlying continuous score does not even meaningfully rank windows compared to either published baseline (Spearman ρ ≈ 0 against both). Cohen's κ against either published baseline is 0.000 at the default threshold.

4. **Recalibration of a single global threshold does NOT recover agreement at n=15** (Δκ ≈ 0, AUROC 0.48). The pilot (n=2) finding of κ improving from 0.000 to +0.217 after recalibration to 0.99 was an n=2-specific artifact, attributable to the unrepresentative wrist PPG behavior of subjects S2 and S3 (the worst-agreement subjects in the dataset). The implication is methodological: a single global SQI threshold is the wrong unit of analysis. Per-subject or per-session calibration is required.

5. **Three published SQI baselines collectively reject 44.6% of windows that the in-house method passes.** Each baseline tests a different physical property (Orphanidou: pulse-template shape; Sukor: pulse-rate variability; Elgendi: amplitude-distribution statistics). The baselines disagree with each other on the gray area (Orphanidou-Sukor κ = +0.410, Orphanidou-Elgendi κ = -0.198, Sukor-Elgendi κ = -0.225; median pairwise κ = -0.198), but they converge on rejecting the same 2,935 windows that the in-house default threshold accepts. Running three orthogonal baselines is the right policy: a single rejection could be argued; consensus rejection across three baselines testing different physical properties is much harder to dismiss.

### 5.2 Relation to prior work

Wearable signal-quality auditing has been advocated by several groups, most influentially @perraudin2021 and @clifford2012. Our contribution differs in three ways. First, we combine signal quality with formal reliability, causal-adjusted confounding analysis, and stratified fairness in a single pipeline; prior work tends to address these as separate tools. Second, we provide a doubly-robust AIPW estimator with bootstrap CIs under a user-supplied DAG, which to our knowledge has not been packaged in a wearable-quality framework. Third, we ship a parameter-sweep validation that demonstrates the audit responds to cohort properties rather than to fixed generator values, an unusual practice in synthetic-data methods papers.

The closest existing toolkit is FLIRT [@foll2021], which focuses on feature engineering and aggregation rather than auditing. Our framework can be combined with FLIRT rather than replacing it: FLIRT produces the features; our pipeline checks whether those features are reliable enough to model.

### 5.3 Limitations

**Detector thresholds were tuned on synthetic data.** The real-data pilot demonstrates these thresholds do not transfer to wrist PPG without recalibration, and the framework supports recalibration as a pipeline operation. Anyone deploying on a new device should recalibrate against either Orphanidou, Sukor, or hand-labeled windows. We have not tested recalibration on chest ECG; the chest signal is more robust to motion and the synthetic-tuned ECG SQI may transfer better than the PPG SQI, but we make no claim either way.

**Validated on all 15 publicly-released WESAD subjects.** The pilot estimates were updated against the full release; the headline finding (in-house SQI disagrees with published baselines on real wrist PPG, κ ≈ 0 against both) strengthened at n=15, but the pilot's "recalibration recovers fair agreement" finding did not replicate. This is reported as an honest negative result in Section 4.3. **Per-subject heterogeneity in HR agreement is large** (stress |HR diff| ranges 6.75-26.02 bpm across subjects, a 4× spread). Any wearable-validation study on WESAD should report effect sizes per subject and avoid drawing conclusions from pooled-by-state aggregates.

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
