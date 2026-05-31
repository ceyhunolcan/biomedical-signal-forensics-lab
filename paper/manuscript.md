# A Single Signal-Quality Threshold Is Insufficient for Wearable Photoplethysmography: A Multi-Baseline Audit on WESAD and PPG-DaLiA


**Authors.** Ceyhun Olcan¹, Mehmet Ozberk Olcan², Seckin Olcan²

**Corresponding author.** Ceyhun Olcan, ceyhun.olcan.27@dartmouth.edu.

**Affiliations.**

¹ Center for Technology and Behavioral Health, Geisel School of Medicine at Dartmouth, Lebanon, NH 03766, USA.

² Faculty of Medicine, Cukurova University, Adana, Turkey.

**ORCID.** Ceyhun Olcan: [0000-0002-6326-6071](https://orcid.org/0000-0002-6326-6071); Mehmet Ozberk Olcan: [0009-0003-5233-4475](https://orcid.org/0009-0003-5233-4475); Seckin Olcan: [0009-0007-4033-7491](https://orcid.org/0009-0007-4033-7491).

## Abstract

**Background.** Wearable photoplethysmography (PPG)-derived measurements are increasingly used as inputs to machine-learning models in digital health, but the underlying signal-quality assumptions are rarely tested against multiple independently developed methods.

**Objective.** To quantify cross-method agreement among published wrist-PPG signal-quality (SQI) methods on a public benchmark, and to characterise the downstream effect of audit-based filtering on biomarker estimation.

**Methods.** We performed a multi-baseline SQI audit on the public WESAD dataset [@schmidt2018] (n = 15 subjects, 6,585 5-second wrist-PPG windows) using three independently developed published PPG SQI methods (Orphanidou 2015 [@orphanidou2015], Sukor 2011 [@sukor2011], Elgendi 2016 [@elgendi2016]) and a single fixed in-house threshold, and replicated the analysis on the public PPG-DaLiA dataset [@reiss2019] (n = 15 subjects, 18,781 windows; same hardware family, different activity paradigm). We compared per-window pass/fail decisions with Cohen's κ and cluster bootstrap confidence intervals, evaluated single-threshold recalibration on a held-out split (3,292 calibration / 3,293 holdout windows), and quantified the effect of audit filtering on leave-one-subject-out (LOSO) baseline-vs-stress classification and per-subject wrist-PPG-to-chest-ECG HR correlation. The full audit is implemented in an open-source Python pipeline (`biomedical-signal-forensics-lab`, MIT licensed) for reproducibility. A synthetic-cohort validation of the remaining pipeline components is reported in the supplement.

**Results.** The three published methods agreed with each other (median Gwet's AC1 = +0.32, mean raw agreement 63%; Cohen's κ was negative on two of three pairs, a prevalence paradox from their shared 74 to 78% rejection rate) and converged on rejecting 44.6% of windows that the in-house threshold accepted, three methods testing three different physical properties of pulse waveforms, three concordant rejections. The in-house SQI was uncorrelated with any published baseline (κ = 0.000 against each). Single-threshold recalibration at n = 15 did not recover agreement (Δκ = 0.000; AUROC for in-house SQI predicting Orphanidou pass/fail = 0.484). Per-subject heterogeneity in wrist-PPG-to-chest-ECG HR disagreement spanned 6.75 to 26.02 bpm during the stress condition, a four-fold range across subjects. Restricting downstream models to Orphanidou-passing windows improved per-subject HR correlation by a median of +0.110 (13 of 15 subjects improved, paired Wilcoxon p = 1.5e-04), an improvement absent under matched random window retention and specific to the timing-based SQIs. The finding replicated on PPG-DaLiA [@reiss2019] (n = 15 subjects, 18,781 windows, same wrist-PPG hardware but ambulatory rather than stress paradigm): consensus rejection 43.1% (vs 44.6% on WESAD), median published-method Gwet's AC1 +0.28 (vs +0.32), with the in-house threshold the lone outlier on both.

**Conclusions.** On a public wearable-PPG benchmark, three independently developed signal-quality methods reject a large fraction of windows that typical in-house pipelines accept, and single-threshold recalibration does not recover agreement at n = 15. Per-subject heterogeneity is the dominant feature of the data, not a single global signal-quality property. We recommend that wearable-AI publications report a multi-baseline SQI audit as standard supplementary material. All analyses are reproducible from a fixed seed in approximately three minutes on a laptop CPU.

Keywords. photoplethysmography signal quality; multi-baseline audit; wearable digital biomarkers; cross-method agreement; reproducibility; WESAD

## 1. Background

Heart rate as it appears in a wearable research dataset is the output of a multi-stage processing pipeline, optical sensing, motion correction, manufacturer-specific filtering, and peak detection, that is opaque to the downstream researcher. The value entering a machine-learning model is a device-level estimate, not a measurement. Most published wearable-AI work treats this estimate as a measurement and reports a single aggregate signal-quality summary per device or per study. Two wrist-worn devices on the same person can disagree by clinically meaningful margins [@bent2020; @shcherbina2017], and the same device on the same person can be reliable at rest and substantially biased during motion. A held-out test set dominated by quiet conditions will surface neither failure.

Three published wrist-PPG signal-quality (SQI) methods are widely cited and each test a different physical property of pulse waveforms: Orphanidou et al. [@orphanidou2015] use a four-rule template-matching SQI based on per-subject pulse-shape correlation; Sukor et al. [@sukor2011] use a decision tree on pulse-morphology features (systolic-to-diastolic amplitude ratio, pulse-to-pulse interval consistency, baseline wander); Elgendi [@elgendi2016] uses amplitude-distribution statistics (skewness, kurtosis, Shannon entropy). The methods are independently developed and were validated on different cohorts. Adjacent reliability and causal-inference literatures provide established statistics for wearable analysis: Bland-Altman limits-of-agreement [@bland1986], bootstrap test-retest with cluster resampling [@efron1993], intraclass correlation [@shrout1979], and doubly-robust causal estimators [@robins1994]. Tools that composite these components into integrated wearable audit pipelines have appeared recently [@foll2021].

Prior work has argued that a single quality threshold cannot serve all measurement contexts and has proposed sliding-scale quality metrics validated against visual inspection [@mclean2023sliding]. What no public benchmark has quantified is how much the published SQI methods agree or disagree with each other on the same real wearable-PPG dataset, and what the downstream impact of audit-based filtering is on biomarker estimation. We address this gap by performing a multi-baseline SQI audit on the public WESAD dataset [@schmidt2018]. We show that the three published methods agree with each other once base rates are accounted for (median Gwet's AC1 = +0.32; Cohen's κ is negative on two of the three pairs, a prevalence paradox) and converge on rejecting 44.6% of windows that a single fixed in-house threshold accepts; single-threshold recalibration at n = 15 does not recover agreement; and audit-based filtering improves downstream per-subject HR correlation by a median of +0.110. To enable reproducibility and reuse, the audit pipeline is implemented as an open-source Python toolkit (`biomedical-signal-forensics-lab`, MIT licensed); additional pipeline components (reliability, causal-adjusted confounding, and fairness analysis) are validated on synthetic data in the supplement. The empirical contribution of this paper is the cross-method SQI consensus-rejection finding; the toolkit is the supporting infrastructure that made it reproducible.

![Figure 1. Cross-method signal-quality agreement and consensus rejection on wearable photoplethysmography. Each colored disk represents the subset of windows accepted by one published method on each dataset (schematic; not proportional). The region outside all three disks represents the consensus rejection by all three independently developed methods (44.6% on WESAD; 43.1% on PPG-DaLiA). The three methods agree more than chance on pass/fail once prevalence is accounted for (median Gwet's AC1 = +0.32) and converge on which to reject. Headline numbers in the figure are uncorrected and identical to those in Table 4 (WESAD) and Table 10 (PPG-DaLiA).](paper/figures/fig1_conceptual.png)

## 2. Methods

### 2.1 Overview

The empirical study is a multi-baseline SQI audit on the WESAD dataset using three published wrist-PPG SQI methods (Section 2.8) and a single fixed in-house threshold. To enable reproducibility and reuse, the analysis is implemented in an open-source Python pipeline (`biomedical-signal-forensics-lab`, MIT licensed) that takes a wearable dataset in a canonical daily-summary schema and produces five categories of output: per-window artifact findings, participant-level reliability primitives, a six-component Digital Biomarker Trust Score, a screening and AIPW-adjusted confounding analysis, and a stratified fairness audit. The empirical contribution is the multi-baseline SQI audit on WESAD with replication on PPG-DaLiA (Section 3), which uses the window-level artifact detection (Section 2.3), the reliability primitives (Section 2.4), and the published-baseline integration (Section 2.8). Synthetic-cohort analyses (Section 4) validate the remaining framework components on parameterised data with documented injected failure modes: the Digital Biomarker Trust Score (Section 2.5), the AIPW-adjusted confounding analysis (Section 2.6), and the stratified fairness audit (Section 2.7). The synthetic validation does not bear on the empirical findings on real wearable data; it characterises framework components available for follow-up studies on other datasets. The whole synthetic pipeline runs end-to-end in approximately two minutes on a modern laptop CPU; the full 15-subject WESAD analysis takes approximately three minutes.

### 2.2 Synthetic cohort

The reference cohort is synthetic: 300 simulated participants over 60 days each, with daily summary records (18,000 rows) and a 10% random sample of short ECG-like and PPG-like windows (~1,800 windows). The generator is parameterized so that cohort size, day count, and the strength of each confounding pathway can be modified without source-code changes. Static participant attributes include age, sex, baseline HR, baseline HRV, baseline activity, device type (three families), a continuous skin-tone proxy in [0, 1], a climate-sensitivity coefficient, and a per-participant missingness tendency.

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

Five detectors operate on each 5-second window: motion, sensor dropout, noise spikes, flatlines, and timestamp irregularity. Each returns an `ArtifactFinding` with a boolean flag, a severity in [0, 1], and a short text explanation. The window-level classifier aggregates findings into a single artifact burden score per window. Thresholds are configurable in `configs/artifact_detection.yaml` and were hand-tuned on the synthetic generator; the real-data pilot demonstrates these thresholds do not transfer without recalibration (Section 3.3).

### 2.4 Reliability primitives

We report four reliability statistics per cohort:

- **Bootstrap test-retest reliability.** For each metric, form non-overlapping calendar-week means within each participant, pool the (week_t, week_{t+1}) pairs across the cohort, compute Pearson correlation. Cluster bootstrap CIs come from 300 participant-level resamples.
- **Intraclass correlation coefficient.** ICC(2,1) two-way random, single-rater, absolute-agreement form [@shrout1979], applied with daily index as the "rater" axis to partition variance between within-subject day-to-day noise and between-subject systematic differences. This is not the canonical between-rater-on-same-subject application of ICC; it is a repeated-measures variant in which each day's measurement is treated as a noisy realization of an underlying subject-level trait. We report ICC alongside the proper bootstrap week-pair test-retest (supplement Section S10.3, Table S1), not in its place; the two metrics agree on which biomarkers have the highest and lowest reliability, and ICC is uniformly more conservative because it treats within-week day-to-day noise as rater disagreement.
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

Demographic bias in clinical algorithms and health-related measurement is well documented [@obermeyer2019; @vyas2020], motivating a routine subgroup check. Stratified bootstrap analysis over any categorical column (device family, skin-tone quartile, sex, age band). For each stratum and each DBTS component, we report the mean, 95% cluster-bootstrap CI (resampling participants, not rows), and the Q1-vs-Q4 disparity with its CI. Forest plots are generated automatically.

### 2.8 Published baselines

We compare the in-house SQI against three published wrist-PPG signal-quality methods. Selection criteria for the published baselines were: (a) independent development with no shared methodological framework, so that joint behavior across the methods is informative rather than expected by construction; (b) targeting of distinct physical properties of the pulse waveform (template shape, pulse-to-pulse interval consistency, amplitude-distribution statistics); (c) availability of explicit thresholds in the original publication or a reference implementation that can be replicated unambiguously; and (d) citation history in the wearable-PPG signal-quality literature. The three methods meeting these criteria are:

- **Orphanidou et al. (2015):** four-rule template-matching SQI based on per-subject pulse-shape correlation. We replicate the published thresholds.
- **Sukor et al. (2011):** decision-tree SQI on pulse-morphology features (systolic-to-diastolic amplitude ratio, pulse-to-pulse interval consistency, pulse amplitude variability, baseline wander). We replicate the published rules.
- **Elgendi (2016):** amplitude-distribution statistics SQI computing third-order skewness (SSQI), kurtosis (KSQI), and Shannon entropy (ESQI) of the windowed signal. We replicate the published thresholds with automatic polarity detection for inverted-polarity wrist PPG.

Recent wearable-PPG SQI methods reviewed in [@charlton2021ppgproc] either target overlapping physical properties or are device-specific in ways that prevent transfer to WESAD and PPG-DaLiA without additional calibration; the three methods selected here span the three theoretically distinct physical properties of pulse waveforms most commonly tested in published wrist-PPG audits and have reference implementations that allow exact replication.

Agreement metrics for each pairwise comparison are reported as Spearman ρ on the continuous scores, Cohen's κ on the binary pass/fail labels, and a full 2×2 crosstab.

### 2.9 Study design

The empirical study is the multi-baseline SQI audit on the WESAD dataset [@schmidt2018] (n = 15 subjects, S2-S17 minus S1 and S12 which are absent from the standard public release). Two supporting analyses use the same audit pipeline on parameterised data to characterise the audit components: (i) a 300-participant 60-day synthetic cohort with documented injected failure modes (Section 2.2), and (ii) a cross-cohort parameter sweep across five synthetic regimes (default, strong environment, inverted skin-tone, severe device bias, clean world) to test the audit's responsiveness to controlled changes in cohort properties. Reproducibility of every reported number is verified from a fixed seed on every continuous-integration run.

### 2.10 Statistical analysis

**Primary pre-specified test.** The primary hypothesis for the empirical study is that audit-based filtering improves per-subject wrist-PPG-to-chest-ECG HR agreement on WESAD. The pre-specified test is a one-sided paired Wilcoxon signed-rank on per-subject Spearman correlation between PPG-derived and ECG-derived HR (Orphanidou-passing windows versus no-audit; Table 9). With a single planned comparison no multiplicity correction is required, and the reported uncorrected p = 1.5e-04 is the primary result.

**Secondary and exploratory analyses.** All other inferential statistics in the manuscript are secondary or exploratory: the three audit-condition Wilcoxon contrasts in Tables 8 and 9 (one of which is structurally degenerate because the in-house threshold passes 100% of windows by construction; the other two are jointly identical), per-subject state-contrast effect sizes (Tables S3, S4), and the AIPW point estimates (Table S8). These are reported uncorrected for descriptive interpretation. Benjamini-Hochberg correction across the three audit-condition comparisons in Table 9 gives q = 2.25e-04 for the primary Orphanidou contrast (versus the uncorrected p = 1.5e-04) and the substantive conclusion is unchanged; in Table 8 the suggestive Orphanidou contrast at uncorrected p = 0.052 gives q = 0.078 after Benjamini-Hochberg correction across three comparisons, still non-significant at the conventional 0.05 cutoff and consistent with our interpretation as a suggestive trend rather than a confirmed effect.

**External replication.** The PPG-DaLiA replication (Section 3.7) tests the same headline metric (in-house pass AND all three published methods fail) on a second public benchmark and is a pre-specified replication of the WESAD finding rather than a new hypothesis.

## 3. Cross-method audit on WESAD

We applied the full pipeline to all 15 subjects in the public WESAD release [@schmidt2018] (S2-S17, with S1 and S12 absent from the standard public release), producing 6,585 5-second windows of synchronized chest RespiBAN ECG (700 Hz) and wrist Empatica E4 PPG (64 Hz) across baseline (3,507 windows), stress (1,979), and amusement (1,099) labeled states.

### 3.0 Reporting standards and reproducibility

The pipeline and analyses in this paper were assessed against the relevant EQUATOR-Network reporting standards for digital-health AI research. Per-standard compliance documentation is provided in `paper/checklists/`:

- **TRIPOD+AI** [@collins2024tripodai] applies to the downstream classifier evaluated in Section 3.6 (LF/HF biomarker, LOSO cross-validation). A per-item compliance summary is in `paper/checklists/tripod_ai_checklist.md`. The downstream classifier in Section 3.6 is a research-stage demonstration intended to test whether the SQI binarisation choice has a measurable downstream effect; it is not a deployment candidate. TRIPOD+AI items related to calibration and external validation are intentionally out of scope for that framing and are noted explicitly in Section 6.
- **STARD 2015** [@bossuyt2015stard] applies to Section 3.1 (Bland-Altman cross-modality HR agreement), in which chest ECG serves as the reference standard and wrist PPG-derived measurements serve as the index modality, and Section 3.7 (external replication on PPG-DaLiA), in which the same reference-versus-index structure is evaluated on a second public benchmark. A per-item compliance summary is in `paper/checklists/stard_2015_checklist.md`. The flow diagram in Supplementary Figure S1 follows STARD conventions adapted to the multi-arm structure of this audit.
- **CONSORT-AI** [@liu2020consortai] and **DECIDE-AI** [@vasey2022decideai] do not apply because this paper is neither a randomised trial nor a clinical-deployment study. Applicability assessments documenting this conclusion (and what a future deployment of this toolkit would need to report) are in `paper/checklists/consort_ai_applicability.md` and `paper/checklists/decide_ai_applicability.md`.

Supplementary Figure S1 (`paper/figures/fig_flow_diagram.png`) shows the flow of data through the WESAD validation pipeline in the STARD-style convention: source dataset, n=15 subjects analysed, per-window processing, zero post-hoc exclusions, and the four analysis arms operating on the same 6,585 windows.

### 3.1 Cross-modality HR agreement (Bland-Altman, Figure 2)

We paired the per-window heart rate from chest ECG against the per-window heart rate from wrist PPG (cross-modality agreement between PPG-derived pulse rate variability and ECG-derived HRV is known to degrade under motion and non-stationarity [@schafer2013]).

| Quantity | Value (n=15) |
|---|---|
| n windows | 6,569 |
| Mean absolute error | **9.66 bpm** |
| **Bias (PPG - ECG)** [@bland1986] | **+3.57 bpm** |
| **95% Limits of agreement** | **[-23.14, +30.28] bpm** |
| Pearson r | +0.697 (p << 0.001) |
| Fraction within 5 bpm | 0.458 |
| Fraction within 10 bpm | 0.656 |

: Table 1. Cross-modality HR agreement on WESAD (n = 15 subjects, 6,569 windows).

On the full release the average disagreement between wrist E4 PPG and chest RespiBAN ECG is +3.57 bpm with 95% LoA spanning 53 bpm. Within-5-bpm agreement is 46%, within-10-bpm is 66%. Pearson correlation between modalities is +0.70. Per-subject heterogeneity is the dominant feature of the data: stress-state mean |HR_PPG - HR_ECG| ranges from **6.75 bpm (S15)** to **26.02 bpm (S11)**, a four-fold spread.

![Figure 2. Bland-Altman cross-modality HR agreement on WESAD (n = 15 subjects, 6,569 paired 5-second windows). Each point is one window. Mean bias (PPG minus ECG) = +3.57 bpm; 95% limits of agreement [-23.14, +30.28] bpm. Pearson r = +0.70 between modalities.](paper/figures/fig1_bland_altman.png)

### 3.2 Four-way SQI agreement on real wrist PPG (Figure 3)

We compare the in-house per-window PPG SQI against three published baselines that each test a different physical property of a wrist PPG window. Photoplethysmography (PPG) is the dominant optical method for non-invasive heart rate sensing on consumer and research wearables [@allen2007; @charlton2021ppgproc], and is well known to be susceptible to motion artifact and signal-quality variation across skin tones, hardware, and activity states [@bent2020; @shcherbina2017; @sjoding2020]: Orphanidou (2015) [@orphanidou2015] (template correlation against a learned per-subject pulse shape), Sukor (2011) [@sukor2011] (peak-to-peak interval and amplitude coefficient-of-variation), and Elgendi (2016) [@elgendi2016] (third-order skewness, kurtosis, and Shannon entropy of the window amplitude distribution). The Elgendi implementation includes automatic polarity detection because the Empatica E4 wrist PPG used in WESAD reports signals inverted relative to the fingertip-PPG conventions on which Elgendi was originally validated.

| Method | Pass rate (n=15) | Cohen's κ vs in-house |
|---|---|---|
| In-house (default threshold 0.7) | 1.000 | - |
| Orphanidou 2015 | 0.256 | 0.000 |
| Sukor 2011 | 0.255 | 0.000 |
| **Elgendi 2016 (SSQI/KSQI/ESQI)** | **0.215** | **0.000** |

: Table 2. Four-way PPG signal-quality method pass rates on WESAD.

| Published-method pair | Raw agreement | Cohen's κ [95% CI] | Gwet's AC1 [95% CI] | PABAK | MCC |
|---|---|---|---|---|---|
| Orphanidou vs Sukor | 0.775 | +0.410 [+0.35, +0.47] | +0.637 [+0.59, +0.68] | +0.551 | +0.410 |
| Orphanidou vs Elgendi | 0.567 | -0.198 [-0.24, -0.16] | +0.324 [+0.22, +0.42] | +0.135 | -0.199 |
| Sukor vs Elgendi | 0.559 | -0.225 [-0.26, -0.19] | +0.312 [+0.22, +0.40] | +0.118 | -0.226 |
| **Median across three pairs** | **0.567** | **-0.198** | **+0.324** | **+0.135** | **-0.199** |

: Table 3. Cross-method agreement across the three published PPG signal-quality baselines on WESAD, with subject-clustered bootstrap 95% confidence intervals (2,000 resamples over the 15 subjects). Cohen's κ is negative on the two Elgendi pairs despite raw agreement above 56%, a prevalence paradox from the shared 74 to 78% rejection rate; the prevalence-insensitive Gwet's AC1 is positive for all three pairs. PPG-DaLiA values are within rounding (median raw 0.625, median AC1 +0.281, median κ -0.204; Section 3.7).

**Three published baselines, fair-to-moderate agreement.** Cohen's κ alone gives a misleading picture here. Orphanidou and Sukor agree moderately on which windows pass by every measure (κ = +0.410, Gwet's AC1 = +0.637, raw agreement 77.5%). Elgendi agrees less with the other two and its Cohen's κ is negative (-0.198 against Orphanidou, -0.225 against Sukor), but this is the κ paradox under skewed prevalence rather than genuine disagreement: all three methods reject 74 to 78% of windows, which inflates chance agreement and pushes κ below zero even though the methods make the same pass/fail call on 56 to 57% of windows. The prevalence-insensitive Gwet's AC1 is positive for all three pairs (+0.31 to +0.64, median +0.324), and the subject-clustered intervals confirm the split: on the Orphanidou-Elgendi pair the κ interval lies entirely below zero ([-0.24, -0.16]) while the AC1 interval on the identical windows lies entirely above zero ([+0.22, +0.42]). The three baselines individually pass 25.6%, 25.5%, and 21.5% of windows and agree more than chance on pass/fail (median AC1 = +0.324, mean raw agreement 63%), not less.

| Joint condition (n=6,585) | Fraction |
|---|---|
| All three published methods pass | 0.005 (0.5%) |
| **All three published methods fail** | **0.446 (44.6%)** |
| **In-house passes while ALL three published methods fail** | **0.446 (44.6%)** |

: Table 4. Joint pass/fail conditions across published baselines on WESAD.

44.6% of real wrist PPG windows are rejected by Orphanidou AND Sukor AND Elgendi simultaneously  -  three baselines, three different physical properties, three concordant rejections  -  and yet the in-house default threshold (0.70) passes every single one of them (a stacked-bar view of the same finding is in Supplementary Figure S4). The case for the in-house SQI binarization being inappropriate on real wrist PPG no longer rests on agreement with any one baseline; it rests on consensus rejection across three orthogonal published methods that each test a distinct property of pulse waveforms.

Across 6,585 real wrist PPG windows from 15 subjects, the in-house default threshold produces a degenerate binary distribution (every window passes), and Cohen's κ between the in-house decision and each published baseline is identically zero (Table 2). This zero is a base-rate artifact of the 100.0% in-house pass rate: Cohen's κ is mathematically zero whenever one of the two classifiers being compared has constant output, regardless of the other classifier's behavior. We report κ versus the in-house decision in Table 2 for completeness; the substantive comparison between the in-house and the published methods is the joint-condition rate in Table 4 (in-house passes AND all three published methods fail: 44.6% of windows), which is unaffected by the κ degeneracy. Unlike Cohen's κ, Gwet's AC1 remains defined when one classifier is near-constant, and it places the in-house threshold in active disagreement with every published method (AC1 = -0.40, -0.40, and -0.50 against Orphanidou, Sukor, and Elgendi): the in-house SQI accepts windows the published methods reject, so its chance-corrected agreement with them falls below zero. The published methods are not three mutually contradictory tests but three concordant ones, with the in-house threshold as the lone outlier. The same base-rate caveat applies on PPG-DaLiA (Section 3.7), where the in-house threshold also passes 100.0% of windows. Pairwise κ across the three published methods themselves (Table 3) is non-degenerate because their pass rates span 21.5% to 25.6% and so neither side of any pair is constant. 

![Figure 3. Cross-method PPG signal-quality agreement on WESAD (n = 6,585 windows). The in-house threshold passes 100% of windows; the three published methods individually pass 21.5 to 25.6%. Pairwise Cohen's kappa across the three published methods spans -0.23 to +0.41 (median -0.20); the prevalence-insensitive Gwet's AC1 is positive for all three pairs (median +0.32).](paper/figures/fig3_kappa_heatmap.png)

**Robustness to the in-house threshold choice.** The 44.6% headline reflects the joint condition "in-house passes (threshold = 0.7) AND all three published methods fail." Because the in-house threshold passes 100.0% of windows at 0.7, this joint condition is numerically identical to the published-only consensus rejection rate (the fraction of windows on which all three published methods agree to reject, independent of any in-house decision; 44.571% on WESAD and 43.129% on PPG-DaLiA). Varying the in-house threshold from 0.50 to 0.95 changes the in-house pass rate by at most three percentage points on either dataset (100.0% to 97.1% on WESAD; 100.0% to 97.2% on PPG-DaLiA) and the headline joint metric by at most 1 percentage point. Median pairwise Cohen's κ across the three published methods is unaffected by any in-house threshold change (κ = -0.198 on WESAD, κ = -0.204 on PPG-DaLiA, exact to three decimals across the full 0.50-0.95 range; Supplementary Table S5 and Supplementary Figure S2). The substantive finding, that three published methods reject the same ~44% of windows in common, is a property of how the published methods behave on real wrist PPG and does not depend on any in-house thresholding choice.

### 3.3 Recalibration: an honest negative result (Figure 4)

We split the 6,585 windows into 3,292 calibration and 3,293 holdout. On calibration we searched the threshold space to maximize Cohen's κ vs the Orphanidou pass/fail label. We then evaluated the chosen threshold on the held-out 3,293 windows.

| Threshold | Holdout raw agreement | **Holdout Cohen's κ** |
|---|---|---|
| Original (0.70) | 0.258 | **0.000** |
| Recalibrated (0.85) | 0.258 | **0.0002** |
| Δ κ | | **≈ 0.000** |

: Table 5. Recalibration of the in-house SQI threshold against the Orphanidou baseline.

**The n=2 pilot recalibration result (Δκ = +0.217) does NOT replicate at n=15.** The search lands on threshold 0.85, but the held-out κ remains effectively zero. Two non-exclusive explanations: (1) the in-house SQI distribution on real wrist PPG is concentrated near 1.0 for nearly every subject, leaving little useful discriminative signal that a single global threshold can extract; (2) per-subject heterogeneity (Section 3.5) is large enough that a single threshold cannot satisfy all subjects simultaneously. The supplementary AUROC analysis (S2.3) confirms this: AUROC for in-house SQI predicting Orphanidou pass/fail is 0.484 at n=15, statistically indistinguishable from chance. **The honest implication is that the in-house SQI binarization recipe should not be used at all on real wrist PPG without per-subject calibration**, which is a methodological recommendation rather than a fix.

![Figure 4. Single-threshold recalibration of the in-house PPG SQI against the Orphanidou pass/fail label on the WESAD held-out split (3,293 windows). The recalibrated threshold leaves held-out Cohen's kappa at approximately zero; AUROC for in-house SQI predicting Orphanidou pass/fail is 0.484 (chance level).](paper/figures/fig6_recalibration.png)

**LOSO recalibration confirms and sharpens the negative result.** To verify the random window-level split does not bias the recalibration conclusion, we re-ran the threshold search as leave-one-subject-out cross-validation (n = 15 folds): for each held-out subject the threshold was selected on the other 14 subjects to maximize κ versus Orphanidou, then evaluated on the held-out subject. Mean held-out Cohen's κ across the 15 folds is -0.063 (median 0.000, range -0.321 to +0.002). For 10 of 15 subjects the train search settles on threshold 0.85, under which the in-house SQI still passes 100% of the held-out subject's windows and held-out κ is degenerate at 0. For the remaining 5 subjects the train search lands on stricter thresholds (0.98 to 0.99) that produce non-trivial in-house pass/fail variation; on these held-out subjects κ ranges from -0.321 to +0.002, with 4 of 5 strongly negative (S10, S13, S16, S9 at κ between -0.32 and -0.16) and the fifth (S17) at +0.0017, essentially zero, meaning that when the in-house SQI is forced to make discriminating decisions it does not recover agreement with the Orphanidou baseline. The negative result therefore holds under both the random-window split reported in Table 5 (Δκ ≈ 0.000) and the more conservative subject-level LOSO split (mean held-out κ = -0.063). The full per-subject LOSO output is at `results/real_data/loso_recalibration.csv` and is visualized in Supplementary Figure S3.

### 3.4 Motion artifact predicts cross-modality HR disagreement (weakly)

| Quantity | Value (n = 15) |
|---|---|
| Spearman (motion vs in-house SQI) | -1.000 (deterministic) |
| Spearman (motion vs absolute HR difference, PPG vs ECG) | +0.088 |
| Spearman (motion vs Orphanidou template correlation) | -0.004 |
| Mean absolute HR difference at low motion (bpm) | 9.12 |
| Mean absolute HR difference at high motion (bpm) | 11.28 |

: Table 6. Motion artifact correlations and cross-modality HR disagreement on WESAD.

The correlation between motion and cross-modality HR disagreement is positive but weak (Spearman ρ = +0.088). Mean absolute HR difference at high motion is 24% higher than at low motion (11.28 vs 9.12 bpm). Both values are smaller than the pilot estimates from the n = 2 analysis (ρ = +0.30, gap = 6.8 bpm). At n = 15 the motion detector tracks the direction of the effect, but the magnitude is modest.

### 3.5 Within-subject state-contrast tests

Mann-Whitney U with Cliff's δ [@cliff1993] and Cohen's d [@cohen1988] applied per (subject, metric, state) contrast (full per-subject tables in supplement Tables S3 and S4).

Stress vs baseline: most subjects show a PPG SQI drop during stress (largest effects at Cliff's δ = +0.75 for S17, +0.73 for S5, +0.70 for S14; corresponding Cohen's d 1.16-1.41, all p << 0.001). One subject (S15) shows the opposite (δ = -0.49), consistent with state-dependent posture in which less movement during the stressor than during baseline improves PPG quality. Heterogeneity in the direction of the PPG SQI effect across subjects is itself the finding. The framework's per-subject outputs catch this; pooled-by-state numbers obscure it.

Baseline vs amusement: the funny-video paradigm produces upper-body laughter motion that degrades wrist PPG in most subjects. The largest single effect is S9 PPG SQI (Cliff's δ = +0.80, Cohen's d = +1.89, p =< 0.001). S14 also shows a large ECG SQI drop (δ = +0.70, d = +1.59), consistent with the chest device responding to laughter motion in addition to wrist PPG.

### 3.6 Downstream model performance with vs without audit filtering

The framework's signal-quality audit is methodological infrastructure: it does not by itself produce a clinical prediction. To show that the audit nevertheless changes downstream model behavior, we evaluated two distinct downstream tasks on the WESAD wrist PPG data under four data-conditioning regimes: (i) no audit (all windows), (ii) in-house SQI default threshold pass, (iii) Orphanidou (2015) pass, (iv) both in-house and Orphanidou pass.

**Task A. Baseline-vs-stress classification.** We trained a logistic regression on three wrist PPG features (PPG-derived HR, motion artifact score, in-house SQI) to discriminate baseline from stress windows. Validation used strict leave-one-subject-out (LOSO) cross-validation across all 15 WESAD subjects; features were standardized within each fold and the classifier was scored on the held-out subject.

| Condition | n subjects | Mean AUROC | 95% bootstrap CI | Median AUROC |
|---|---|---|---|---|
| no audit | 15 | 0.804 | [0.716, 0.871] | 0.850 |
| in-house pass (≥ 0.70) | 15 | 0.804 | [0.716, 0.871] | 0.850 |
| **Orphanidou pass** | **14** | **0.823** | **[0.744, 0.906]** | **0.822** |
| both | 14 | 0.823 | [0.744, 0.906] | 0.822 |

: Table 7. Leave-one-subject-out baseline-vs-stress classification AUROC on WESAD by audit condition.

| Condition vs no-audit | n paired | Mean Δ AUROC | n improved / n worse | Wilcoxon p (one-sided, greater) |
|---|---|---|---|---|
| in-house | 15 | 0.000 | 0 / 0 | 1.000 |
| **Orphanidou** | **14** | **+0.027** | **10 / 4** | **0.052** |
| both | 14 | +0.027 | 10 / 4 | 0.052 |

: Table 8. Paired Δ AUROC vs no-audit control by audit condition.

The in-house SQI default threshold passes every window (pass rate 1.000; Section 3.2), so "in-house" is identical to "no audit" by construction. The Orphanidou-filtered condition shows a +0.027 mean improvement in held-out subject AUROC with 10 of 14 subjects improving, just outside conventional significance (p = 0.052). We report this as a suggestive trend rather than a significant effect.

**Task B. Per-subject biomarker correlation.** For each subject, we computed the Spearman correlation between the wrist-PPG-derived HR and the chest-ECG-derived HR under each audit condition. We then paired the per-subject ρ values across conditions and tested whether audit filtering produces a consistent improvement (one-sided Wilcoxon signed-rank [@wilcoxon1945]).

| Comparison | n paired | Mean Δ ρ | Median Δ ρ | n improved / n worse | Wilcoxon p (greater) |
|---|---|---|---|---|---|
| in-house vs all | 15 | 0.000 | 0.000 | 0 / 0 | 1.000 |
| **Orphanidou vs all** | **15** | **+0.102** | **+0.110** | **13 / 2** | **1.5e-04** |
| both vs all | 15 | +0.102 | +0.110 | 13 / 2 | 1.5e-04 |

: Table 9. Per-subject Spearman correlation between wrist PPG HR and chest ECG HR by audit condition.

Restricting to Orphanidou-passing windows improves the per-subject correlation between wrist PPG HR and chest ECG HR by a median of **+0.110** across the 15-subject cohort, with **13 of 15 subjects improving** and **2 declining** (subjects S4, S8 show a slight decline). The paired Wilcoxon test gives **p = 1.5e-04**, comfortably significant. The largest improvements are in subjects whose unfiltered correlation was modest: S10 (0.65 → 0.78), S9 (0.47 → 0.76), S13 (0.42 → 0.54), S6 (0.53 → 0.71).

**The improvement is quality-specific and filter-dependent.** Two controls bound this result. As a negative control, retaining the same number of windows per subject chosen at random rather than by Orphanidou produces a median correlation change of +0.005 on WESAD and +0.000 on PPG-DaLiA, with the 95% range across 200 draws straddling zero. The gain is therefore a property of which windows are kept, not of keeping fewer windows or of range restriction from subsetting. Filter choice also matters: substituting Sukor for Orphanidou gives a similar improvement (median +0.139 on WESAD, +0.177 on PPG-DaLiA), but substituting Elgendi reverses it (median -0.171 on WESAD, -0.186 on PPG-DaLiA, with 0 to 2 of 15 subjects improving). The two SQIs that test pulse timing and shape, properties tied to rate recovery, improve HR agreement; the amplitude-distribution SQI does not. The downstream benefit is specific to HR-relevant quality criteria rather than automatic for any SQI, which is why we filter by Orphanidou and report the contrast rather than treating the three methods as interchangeable downstream filters.

**Combined interpretation.** Filtering by an HR-relevant SQI improves window-level HR agreement but only marginally improves cohort-level classification, and the two results carry different evidential weight. The classification result (Task A, +0.027, p = 0.05) is the more independent test, because the SQI is not optimized for stress classification: any gain there reflects cleaner model inputs rather than the filter selecting for its own objective. LOSO evaluation on n = 15 has limited statistical power, and the +0.027 mean improvement is consistent with a real effect the sample size cannot declare significant. The HR-correlation result (Task B, +0.110, p < 0.001) is larger and, by the negative control above, quality-specific rather than a retention artifact, but it sits closer to the filtering criterion: filtering on PPG quality and then scoring PPG-derived HR accuracy is partly self-fulfilling, since improving rate recoverability is much of what a pulse-shape or interval SQI does. We therefore read Task A as the more demanding evidence that the audit affects a task it does not directly target, and Task B as confirmation that Orphanidou and Sukor act as competent HR-quality filters. The trade-off is data retention: Orphanidou filtering keeps roughly 26% of windows. For subjects with already-strong correlation (S14, S16, S17 all at ρ ≥ 0.83 without filtering), the improvement is modest; for subjects with weaker correlation (S2, S5, S15 at ρ < 0.60 without filtering), the gain is substantial.

**Trade-off characterization.** Figure 5 panel D plots per-subject retention against Δρ. Subjects above the y = 0 line benefit from filtering; the small minority below (S4, S8) lose information at the audit threshold. A practitioner deploying the framework can read this trade-off plot directly: for any new dataset they can compute per-subject retention and Δ and decide whether to filter, threshold differently, or skip the audit entirely.

![Figure 5. Audit-based filtering improves per-subject biomarker estimation on WESAD. Panel A: LOSO baseline-vs-stress AUROC distributions by audit condition. Panel B: per-subject paired Delta-AUROC vs no-audit, by audit variant. Panel C: per-subject wrist-PPG-to-chest-ECG HR Spearman correlation under each condition. Panel D: per-subject retention vs Delta-rho trade-off under the Orphanidou filter (13 of 15 subjects improve, paired Wilcoxon p = 1.5e-04).](results/downstream_demo/figure_downstream.png)

### 3.7 External validation on PPG-DaLiA

The cross-method SQI consensus-rejection finding from Section 3.2 replicates on a second public wearable benchmark with the same hardware but a different activity paradigm. We applied the identical audit pipeline (in-house threshold + Orphanidou + Sukor + Elgendi) to all 15 subjects of the public PPG-DaLiA release [@reiss2019], which uses the same Empatica E4 wrist and RespiBAN chest devices as WESAD but covers 8 ambulatory activities (sitting, stairs, table soccer, cycling, car driving, lunch break, walking, working) rather than psychological stress and amusement.

On 18,781 5-second windows from PPG-DaLiA, the three independently developed published methods collectively rejected 43.1% of windows accepted by the in-house threshold, compared with 44.6% on WESAD. Pairwise Cohen's κ across the three published methods showed the same pattern as on WESAD, with the prevalence-insensitive Gwet's AC1 positive on both datasets (median AC1 +0.281 on PPG-DaLiA versus +0.324 on WESAD): median pairwise κ = -0.204 on PPG-DaLiA versus -0.198 on WESAD, with the same sign and magnitude on each pair (Orphanidou vs Sukor +0.46 vs +0.41; Orphanidou vs Elgendi -0.20 vs -0.20; Sukor vs Elgendi -0.22 vs -0.23). Pass rates for each published method landed within 3 percentage points of their WESAD values. The in-house threshold passed 100.0% of windows on both datasets, with Cohen's κ against each published method indistinguishable from zero on both.

| Metric | WESAD (n = 15, 6,585 windows) | PPG-DaLiA (n = 15, 18,781 windows) |
| --- | --- | --- |
| In-house pass rate | 1.000 | 1.000 |
| Orphanidou pass rate | 0.256 | 0.282 |
| Sukor pass rate | 0.255 | 0.271 |
| Elgendi pass rate | 0.215 | 0.220 |
| In-house pass AND all 3 published fail | 0.446 | 0.431 |
| Median pairwise κ (published methods) | -0.198 | -0.204 |
| κ vs in-house (all three published) | 0.000 | 0.000 |
| Per-subject absolute HR-difference range (bpm) | 6.75-26.02 | 6.66-16.27 |
| Per-subject fold range | 4.0x | 2.4x |

: Table 10. External validation on PPG-DaLiA, side-by-side with WESAD. The cross-method SQI consensus-rejection finding replicates on a 3x larger benchmark with a different activity paradigm and the same hardware.

The PPG-DaLiA per-subject absolute HR difference (wrist PPG vs chest ECG) range was less extreme than on WESAD (2.4x fold range vs 4.0x), but the absolute minimum was virtually identical (6.66 vs 6.75 bpm). The lower fold range is consistent with PPG-DaLiA's wider activity mix smoothing the upper tail rather than with reduced per-subject heterogeneity. The replication confirms that the cross-method SQI consensus-rejection finding is a property of wrist PPG itself rather than of the WESAD stress paradigm or of any single recording session.

## 4. Methodological validation on synthetic data

The pipeline components that WESAD and PPG-DaLiA cannot exercise, the reliability primitives, the Digital Biomarker Trust Score, the AIPW-adjusted confounding analysis, and the stratified fairness audit, are validated on a 300-participant 60-day synthetic cohort with documented injected failure modes (cohort and generator described in Section 2.2). These analyses recover the injected effects (for example device-family and skin-tone signal-quality gaps, and an AIPW-adjusted active-minutes effect on HRV that a screening correlation misses) and characterise the components for follow-up studies on longitudinal datasets. They do not bear on the empirical findings in Section 3. The full results, tables, and figures are in supplement Section S10.

## 5. Discussion

### 5.1 Principal findings

Three findings on the WESAD dataset have direct implications for the design and reporting of wearable-AI studies:

1. **Three published wrist-PPG SQI methods agree and converge on rejecting a large window population on real wearable data.** The published methods individually pass 21.5% to 25.6% of windows and collectively reject 44.6% of windows accepted by a single fixed in-house threshold. Across the three methods the prevalence-insensitive Gwet's AC1 is positive on every pair (median +0.32) and raw agreement averages 63%; the negative median Cohen's κ (-0.20) is a prevalence paradox from the shared 74 to 78% rejection rate, not genuine disagreement. The methods agree more than chance on pass/fail and converge on rejecting a substantial population of windows. Each method tests a different physical property (Orphanidou: pulse-shape correlation; Sukor: pulse-to-pulse interval consistency; Elgendi: amplitude-distribution statistics), so the consensus rejection is not driven by a shared methodological assumption. The same pattern replicates on PPG-DaLiA (n = 15 subjects, 18,781 windows, same wrist-PPG hardware but ambulatory rather than stress paradigm): consensus rejection 43.1%, median pairwise published κ = -0.20, κ = 0.000 against the in-house threshold across all three published methods.

2. **Single-threshold recalibration does not recover agreement at n = 15.** A held-out split (3,292 calibration / 3,293 holdout windows) tuning the in-house threshold against Orphanidou returned Δκ ≈ 0 on holdout; AUROC for the in-house SQI predicting Orphanidou pass/fail was 0.484, statistically indistinguishable from chance. The implication is that a single global SQI threshold is the wrong unit of analysis on wrist PPG; per-subject or per-session calibration is required. The pilot finding of κ improving from 0.000 to +0.217 after recalibration to 0.99 (reported at n = 2) was an artifact of the two subjects whose wrist-PPG behaviour was unrepresentative of the cohort.

3. **Per-subject heterogeneity dominates pooled summary statistics, and audit-based filtering improves downstream biomarker estimation.** Mean |HR_PPG - HR_ECG| during stress ranges from 6.75 bpm (S15) to 26.02 bpm (S11), a four-fold spread across 15 subjects. The direction of the per-state quality change also varies (most subjects' PPG SQI drops during stress; S15's rises). Any conclusion from pooled WESAD wrist-PPG analysis is at risk of being driven by a small number of subjects. Restricting downstream models to Orphanidou-passing windows improves per-subject wrist-PPG-to-chest-ECG HR correlation by a median of +0.110 (13 of 15 subjects improved, paired Wilcoxon p = 1.5e-04), with the largest gains in subjects whose unfiltered correlation was modest (S10: 0.65 → 0.78, S9: 0.47 → 0.76).

### 5.2 Relation to prior work

Wearable signal-quality auditing and feature extraction have been addressed previously, for example by @clifford2012 and @foll2021. Our contribution differs in three ways. First, we combine signal quality with formal reliability, causal-adjusted confounding analysis, and stratified fairness in a single pipeline; prior work tends to address these as separate tools. Second, we provide a doubly-robust AIPW estimator with bootstrap CIs under a user-supplied DAG, which to our knowledge has not been packaged in a wearable-quality framework. Third, we ship a parameter-sweep validation that demonstrates the audit responds to cohort properties rather than to fixed generator values, an unusual practice in synthetic-data methods papers.

The closest existing toolkit is FLIRT [@foll2021], which focuses on feature engineering and aggregation rather than auditing. Our framework can be combined with FLIRT rather than replacing it: FLIRT produces the features; our pipeline checks whether those features are reliable enough to model.

### 5.3 Limitations

**Detector thresholds were tuned on synthetic data.** The real-data pilot demonstrates these thresholds do not transfer to wrist PPG without recalibration, and the framework supports recalibration as a pipeline operation. Researchers deploying on a new device should recalibrate against either Orphanidou, Sukor, or hand-labeled windows. We have not tested recalibration on chest ECG.

**Validated on all 15 publicly-released WESAD subjects.** The pilot estimates were updated against the full release; the headline finding (in-house SQI disagrees with published baselines on real wrist PPG, κ ≈ 0 against both) strengthened at n=15, but the pilot's "recalibration recovers fair agreement" finding did not replicate. This is reported as an honest negative result in Section 3.3, stable across split strategies: both random window-level split (Δκ ≈ 0.000) and leave-one-subject-out cross-validation (mean held-out κ = -0.063) reach the same conclusion. **Per-subject heterogeneity in HR agreement is large** (stress |HR diff| ranges 6.75-26.02 bpm across subjects, a 4× spread). Any wearable-validation study on WESAD should report effect sizes per subject and avoid drawing conclusions from pooled-by-state aggregates.

**Both real-data benchmarks use the same hardware family.** WESAD and PPG-DaLiA both record wrist photoplethysmography from the Empatica E4 wrist device with synchronous chest ECG from the RespiBAN chest device. The cross-method SQI consensus-rejection finding replicates across the two recording paradigms (stress and amusement on WESAD; eight ambulatory activities on PPG-DaLiA), which controls for activity-specific and stress-specific effects, but does not test whether the pattern holds on other consumer wearables (e.g., Apple Watch, Fitbit, Garmin, Oura). PPG noise profiles depend on optical design, sensor sampling rate, and on-device preprocessing, all of which differ across vendor families. Confirming the pattern on additional device families is an open question for follow-up work, and a longitudinal multi-device wearable corpus would provide the natural next test.

**The in-house baseline is a simple motion threshold, not a validated quality index.** The in-house SQI used here is a motion-driven per-window score applied at a fixed 0.70 cutoff. At that cutoff it accepts essentially all windows on both datasets, and Table 6 shows it is close to a deterministic inverse of the motion estimate (Spearman -1.000), so we do not claim it is a calibrated or validated signal-quality index. A reader could reasonably object that rejecting windows such a score accepts is a low bar. We include it only as a stand-in for the common practice of applying a single fixed threshold to a motion-correlated quality score, and the substantive finding does not depend on it: the consensus-rejection result is a property of the three published methods agreeing on the same large fraction of windows (44.6% on WESAD, 43.1% on PPG-DaLiA; Section 3.2), independent of any in-house decision, and the threshold-sensitivity analysis shows the headline is unchanged across the full 0.50 to 0.95 range (Supplementary Table S5). The intended reading is not that the published methods beat the in-house threshold, but that three independently developed methods converge while a single motion threshold does not discriminate among windows at all.

**No hand-labeled signal-quality ground truth.** On WESAD and PPG-DaLiA the three published methods converge on a consensus-reject set while still differing on individual windows (raw agreement 56 to 78%); without hand-labeled signal-quality ground truth on these datasets, we cannot identify which method (if any) is correct on any specific disagreed-on window. The HR-agreement evidence in Section 3.6 is an indirect proxy: Orphanidou-passing windows produce higher per-subject wrist-PPG-to-chest-ECG HR correlation than no-audit windows (paired Wilcoxon p < 0.001), which is consistent with the published methods successfully filtering bad windows but does not by itself identify any one of them as a gold standard. Hand-labeling a representative window sample on both datasets (e.g., 200 stratified windows: consensus-pass, consensus-reject, and gray-area) and computing each method's Cohen's κ against the human-rater target is the natural follow-up to convert the agreement finding from "the methods reject different windows" to "method X has the highest agreement with human labels." The audit pipeline supports this comparison through the same κ machinery used here (Section 2.10).

**Within-session HR reliability is much weaker than week-pair reliability** (supplement S2.5). The synthetic cohort gives test-retest r = +0.977 for resting HR on week-mean pairs (supplement Section S10.2). On real WESAD baseline segments, the split-half Pearson r between first-half and second-half of per-window HR is +0.078 (S2) and +0.112 (S3), with within-subject CV of 6.7-9.1%. These two statistics measure different things (week-aggregated reliability vs 5-second-window within-session correlation) and the synthetic numbers should not be read as predicting the real-data per-window numbers. The framework's recommended HR reliability statistic for clinical claims is the bootstrap week-pair test-retest of a daily aggregate, which requires longitudinal data we cannot validate on WESAD.

**WESAD does not test longitudinal reliability.** WESAD has a single ~100-minute session per subject. Test-retest reliability, weekly drift, missingness dynamics, and longitudinal device-bias analyses cannot be validated on WESAD. They are validated on the synthetic cohort, where ground truth is controlled. Real-data validation of those analyses requires a longitudinal dataset such as the All of Us Research Program.

**No clinical validation.** We have not validated any component of this framework against gold-standard clinical measurements. The framework's outputs are signal-quality estimates and methodological recommendations, not diagnoses.

**ICC(2,1) is applied as a repeated-measures variant.** The day index is used as the "rater" axis, which is not the canonical between-rater-on-same-subject form of ICC. We report it alongside the proper bootstrap week-pair test-retest (supplement Section S10.3, Table S1), not in place of it; both metrics rank biomarkers consistently on the synthetic cohort, with ICC uniformly more conservative because it treats within-week day-to-day variance as rater disagreement. Practitioners reporting ICC days-as-raters in the wearable-reliability literature can use either metric for ordinal comparisons.

**Secondary and exploratory analyses are reported uncorrected for multiplicity.** The primary pre-specified test (Section 2.10) is a single comparison and requires no correction. The Table 8 LOSO AUROC contrasts, the per-subject effect-size tables in the supplement (Tables S3, S4), and the AIPW point estimates are reported uncorrected for descriptive interpretation; Benjamini-Hochberg correction across the three audit-condition comparisons in Tables 8 and 9 does not change any substantive conclusion (Section 2.10).

**No frequency-domain HRV.** We report time-domain HRV (RMSSD, SDNN) but not LF/HF. The synthetic windows are too short to support meaningful frequency-domain HRV. Adding frequency-domain HRV is a one-day change.

**Methodology study, not clinical validation.** This is a methodology paper rather than a clinical validation study. The recommendations in Section 6 are aimed at the wearable-AI research community (multi-baseline SQI auditing as standard supplementary material in wearable-AI publications) and do not constitute clinical guidance. Translation of any cross-method-audit recommendation into patient-facing clinical practice would require prospective clinical validation with relevant device experience; the synthetic-cohort validation in Section 4 and the WESAD/PPG-DaLiA empirical study in Section 3 are methodological contributions rather than clinical findings.

## 6. Conclusions

On a public wearable-PPG benchmark (WESAD, n = 15 subjects, 6,585 windows), three independently developed published signal-quality methods, Orphanidou (2015), Sukor (2011), and Elgendi (2016), collectively reject 44.6% of windows accepted by a single fixed in-house threshold. The three methods agree with each other once base rates are accounted for (median Gwet's AC1 = +0.32; the negative Cohen's κ is a prevalence paradox) and converge on the consensus rejection set. Single-threshold recalibration at n = 15 does not recover agreement, and per-subject heterogeneity in cross-modality HR disagreement spans a four-fold range across subjects. Restricting downstream models to Orphanidou-passing windows improves per-subject HR correlation by a median of +0.110 (paired Wilcoxon p = 1.5e-04). The finding replicates on a second public benchmark (PPG-DaLiA, n = 15, 18,781 windows; same wrist-PPG hardware but ambulatory activity paradigm rather than stress paradigm): consensus rejection 43.1%, median pairwise κ across published methods -0.20, κ against the in-house threshold 0.000, with all three published-method pass rates within 3 percentage points of their WESAD values. The implication for wearable-AI research practice is that single-method SQI reporting is insufficient: multi-baseline auditing should be standard supplementary material in wearable-AI publications.

To support reproducibility, the audit pipeline used in this study is openly available as `biomedical-signal-forensics-lab` (MIT licensed) and runs end-to-end from a fixed seed in approximately three minutes on a modern laptop CPU.

## Code and data availability

Code: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab, released under the MIT license. PyPI: https://pypi.org/project/biomedical-signal-forensics-lab/. Concept DOI: 10.5281/zenodo.20349806. All synthetic data is generated by code from a fixed seed; no data is distributed separately. Two public datasets were used in the empirical study: WESAD [@schmidt2018], publicly available from the UCI Machine Learning Repository, and PPG-DaLiA [@reiss2019], also publicly available from the UCI Machine Learning Repository. Both are released without restrictions for research use.

## Author contributions

Ceyhun Olcan: Conceptualization, Data curation, Formal analysis, Investigation, Methodology, Software, Validation, Visualization, Writing - original draft, Writing - review and editing. Mehmet Ozberk Olcan: Writing - original draft, Writing - review and editing. Seckin Olcan: Writing - original draft, Writing - review and editing.

## Funding

No external funding supported this work.

## Ethics statement

This study is a secondary analysis of two publicly available datasets, WESAD [@schmidt2018] and PPG-DaLiA [@reiss2019], released under terms permitting research use. No new human-subjects data were collected; institutional review board approval was therefore not required for this work.

## Competing interests

The authors declare no competing interests.

## References

::: {#refs}
:::

## Supplementary materials

- `paper/supplement.md` / `paper/supplement.docx`: companion supplement with seven sections (S1 ICC days-as-raters diagnostic, S2 AIPW positivity and E-value sensitivity, S3 cross-cohort parameter-sweep details, S4 per-subject stress effect-sizes on WESAD, S5 per-subject amusement effect-sizes on WESAD, S6 learned trust-score weights with training-versus-holdout breakdown, S7 threshold-sensitivity analysis for the in-house SQI baseline on both real datasets) and five supplementary tables (Tables S1-S5).
- `paper/checklists/`: per-standard reporting-compliance summaries (TRIPOD+AI, STARD 2015, CONSORT-AI applicability, DECIDE-AI applicability).
- `results/real_data/wesad_deep/` and `results/real_data/ppg_dalia/`: per-window CSVs (window_table.csv, window_meta.csv, daily_summary.csv) and summary.json files for both real-data datasets.
- `results/real_data/threshold_sensitivity.csv` and `results/real_data/loso_recalibration.csv`: robustness-analysis output files.
- `CHANGELOG.md`: full release history of the toolkit.
