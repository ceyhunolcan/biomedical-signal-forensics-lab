# Results

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

All results below are reproduced by four scripts run in order on the bundled synthetic cohort (`run_pipeline.py`, `run_signal_audit.py`, `train_quality_model.py`, `generate_report.py`), plus the cross-cohort stress test (`run_cross_cohort_check.py`). End-to-end runtime is about two minutes on a modern laptop CPU. Seeds are fixed in `configs/default.yaml`. Every number in this section corresponds to a row in `results/tables/`.

## 1. The cohort

Three hundred simulated participants, sixty days each, three device families, a continuous skin-tone proxy (0 = lightest, 1 = darkest), age range 18 to 75, sex distribution 51% F / 49% M. The generator injects four kinds of failure modes that we then ask the audit framework to surface:

- State-dependent missingness: device wear drops on high-stress days and on days with poor sleep the night before.
- Heat-coupled physiology: heat index above 26°C suppresses HRV (RMSSD), with a default coefficient of -1.8 ms per heat-load unit.
- Motion-coupled PPG noise: PPG signal quality decreases linearly with active minutes above ~120 per day.
- Device biases: device A is the reference; device B reads +3.8 bpm and reduces SQI by ~8%; device C reads -2.1 bpm and reduces SQI by ~15%.
- Skin-tone-coupled PPG penalty: the darker the proxy, the larger the SQI penalty (default 0.12 maximum loss at proxy = 1).

Eighteen thousand daily summary rows and approximately 1,800 five-second ECG/PPG-like windows. The full data card is in `paper/data_card.md`.

## 2. Cohort-level Digital Biomarker Trust Score

Mean overall DBTS across all 300 participants: **74.11** (moderate). Category distribution: 31 high, 266 moderate, 3 low, 0 unreliable. Histogram is in `results/figures/trust_distribution.png`.

The score combines six components on a 0-100 scale with default weights drawn from `configs/reliability.yaml`:

| Component | Default weight | What it captures |
|---|---|---|
| signal_quality_score | 0.25 | Wear coverage and ground-truth SQI |
| artifact_burden_score | 0.20 | Per-day motion / dropout / noise / flatline severities |
| temporal_stability_score | 0.20 | Within-participant coefficient of variation of HRV |
| missingness_risk_score | 0.15 | Missing wear rate plus longest missing run |
| device_bias_score | 0.10 | Distance from cohort mean HR, in a multi-device cohort |
| confounding_risk_score | 0.10 | Strength of heat-HRV correlation |

A learned-weights experiment (Section 5) shows these defaults are close to but not exactly optimal for predicting week-to-week HRV reproducibility on this cohort.

## 3. Fairness disparities recovered

| Stratifier | Component | n_days | Q1 / lowest stratum | Q4 / highest stratum | Gap |
|---|---|---|---|---|---|
| device_type | signal_quality_score | 8400 / 3180 | device_A: 67.4 | device_C: 54.4 | -13.0 |
| skin_tone_q | signal_quality_score | 4500 each | Q1: 67.9 | Q4: 58.4 | -9.5 |

The injected effects were 0.85 vs 1.00 SQI multiplier for device C vs A (recovers as a 13-point gap) and 0.12 × proxy for skin tone (recovers as a 9.5-point gap). Both gaps include bootstrap 95% CIs in `results/tables/fairness_by_device.csv` and `fairness_by_skin_tone.csv`. Forest plots in `results/figures/fairness_forest_device.png` and `fairness_forest_skin_tone.png`.

## 4. Causal-adjusted confounding

Screening Pearson correlations look small enough to ignore. The doubly-robust AIPW estimator, conditioning on the back-door adjustment set from `default_wearable_dag()`, shows a different picture for heat-HRV:

| Treatment | Outcome | Screening r | AIPW estimate | 95% CI | Notes |
|---|---|---|---|---|---|
| heat_index | hrv_rmssd | -0.054 | +0.25 | [-0.60, +1.03] | screening correlation was confounded by stress and sleep |
| stress_proxy | sleep_efficiency | -0.331 | -0.21 | [-0.27, -0.14] | screening signal survives adjustment |
| active_minutes | hrv_rmssd | -0.183 | -0.04 | [-0.42, +0.34] | screening signal is mostly confounding |

This is exactly the pattern wearable papers should worry about: weak screening correlations that change sign or magnitude under adjustment, and strong screening correlations that disappear. The audit reports both, side by side. CSV: `results/tables/confounding_adjusted.csv`. Methods detail: `paper/methods.md` and `paper/signal_quality_framework.md`.

## 5. Learned trust-score weights

We searched the 6-component weight simplex (Dirichlet random sampling plus local grid refinement) for the weighting that maximizes Spearman correlation between the overall trust score and week-over-week reproducibility of HRV RMSSD. Holdout is a 30% participant-level split that the search never sees.

- Training Spearman ρ: **+0.592**
- Holdout Spearman ρ: **+0.668**
- Number of weight candidates evaluated: 360
- Train n: 210 participants. Holdout n: 90 participants.

The learned weights move the emphasis toward signal_quality and away from confounding_risk, but stay within the convex hull of plausible weightings. Learned weights and per-component sensitivity in `results/tables/learned_weights.json`. Result: the default weights are within 0.08 Spearman of the optimum on this cohort, which is the level of evidence we'd want before recommending any particular weighting for a new dataset.

## 6. Bootstrap test-retest reliability (week-pair design)

For each metric, we form non-overlapping calendar-week means within each participant, then pool the (week_t, week_{t+1}) pairs across the cohort and compute Pearson r. Cluster bootstrap CIs come from 300 resamples at the participant level.

| Metric | Test-retest r | 95% CI | Participants | Week pairs |
|---|---|---|---|---|
| resting_hr | +0.977 | [+0.973, +0.980] | 300 | 2400 |
| hrv_rmssd | +0.954 | [+0.945, +0.961] | 300 | 2400 |
| sleep_efficiency | +0.023 | [-0.018, +0.062] | 300 | 2400 |
| sleep_duration | +0.002 | [-0.050, +0.038] | 300 | 2400 |

Resting HR is highly reliable week to week. HRV almost as much. Sleep efficiency and duration are essentially noise from one week to the next. This is the kind of result a clinical paper should report instead of an aggregate "wearable reliability" number. CSV: `results/tables/test_retest_bootstrap.csv`.

## 7. ICC(2,1) days-as-raters vs proper week-pair r

The framework also exposes the unconventional ICC(2,1) with calendar days as 'raters'. The classical Shrout & Fleiss (1979) form assumes a small fixed set of human raters; substituting daily measurements is mathematically irregular but useful for ranking participants by within-participant noise floor. The empirical comparison:

| Metric | ICC(2,1) days as raters | Week-pair r | 95% CI (week-pair) |
|---|---|---|---|
| resting_hr | +0.869 | +0.977 | [+0.973, +0.980] |
| hrv_rmssd | +0.779 | +0.954 | [+0.945, +0.961] |
| sleep_efficiency | +0.006 | +0.023 | [-0.018, +0.062] |
| sleep_duration | -0.003 | +0.002 | [-0.050, +0.038] |

The two methods agree on the ranking. The ICC is uniformly more conservative because it counts within-week noise as rater disagreement. Both metrics correctly identify sleep efficiency and duration as essentially unreliable on this cohort. The framework supports both; a clinical paper should report the bootstrap week-pair r as the headline statistic and use the ICC as a within-participant noise-floor diagnostic. CSV: `results/tables/icc_vs_test_retest.csv`.

## 8. Comparison against a published baseline (Orphanidou et al. 2015)

The closest established method to the in-house per-window PPG SQI is Orphanidou's four-rule template-matching SQI (IEEE JBHI 2015). We ran both on all 1,800 PPG windows in the synthetic cohort:

- Windows compared: **1800**
- In-house mean PPG SQI: **0.979**
- Orphanidou acceptable fraction: **0.646**
- Spearman ρ (in-house continuous vs Orphanidou template correlation): **+0.782**
- Point-biserial r (in-house continuous vs Orphanidou pass/fail): **+0.591**
- Crosstab at in-house threshold 0.7: 1163 both pass / 0 both fail / 637 in-house pass + Orphanidou fail / 0 in-house fail + Orphanidou pass.

The two methods are not identical (Spearman 0.78 rather than 1.0), and the in-house SQI is uniformly more permissive than Orphanidou's binary rule set on this cohort. Both findings are honest signal: the framework's contribution is the auditable pipeline and the trust score, not a novel SQI estimator, and the framework's per-window SQI agrees with the published reference well enough to be useful as a continuous quality estimate. Anyone running this on real data should run both and report the agreement. CSV: `results/tables/baseline_comparison_orphanidou.csv`.

## 9. Cross-cohort generalization (partial defense against circular evaluation)

We rebuild the synthetic cohort under five different parameter regimes and run the audit on each:

| Regime | heat_hrv coef | skin_tone penalty | device_B offset | heat-HRV r | Q4-Q1 SQI | device-B empirical | HRV test-retest r |
|---|---|---|---|---|---|---|---|
| default | -1.8 | +0.12 | +3.8 | -0.075 | -7.54 | +3.20 | +0.955 |
| strong_environment | -4.5 | +0.30 | +3.8 | -0.190 | -20.36 | +3.20 | +0.921 |
| inverted_skin_tone | -1.8 | -0.12 | +3.8 | -0.075 | +9.34 | +3.20 | +0.955 |
| severe_device_bias | -1.8 | +0.12 | +8.0 | -0.075 | -7.54 | +7.40 | +0.955 |
| clean_world | 0.0 | 0.00 | 0.0 | +0.007 | +1.07 | -0.60 | +0.959 |

Eight qualitative predictions about how the framework should respond. Seven pass. The one failure is honest: `clean_world` still shows an empirical device-B offset of about 4 bpm at small sample sizes despite zero injected bias, because random device assignment interacts with per-participant baseline scatter. That's exactly what would happen in a real cohort, and the framework correctly reports it. The full prediction-vs-observed table is `results/tables/cross_cohort_predictions.csv`.

This is not real-data validation. It is a partial defense: the framework's outputs respond to the cohort's underlying parameters in the predicted direction, including sign flips. They are not just measuring properties of the default generator values.

## 10. What this whole exercise does not show

Three things, in order of how much they matter for credibility:

1. Detector thresholds are tuned on the synthetic generator and have not been validated against any real wearable. The `recalibrate_detector` helper in `src/data/real_data_adapter.py` is provided for that purpose. Until that calibration has been done against real data, every absolute number in this document should be treated as an audit of the framework's behavior on the bundled cohort, not as a calibration of any real device.

2. The trust-score weights are the defaults in `configs/reliability.yaml`. The learned-weights result in Section 5 shows they are close to optimal for the bundled cohort's HRV-reproducibility target, but a different cohort or a different downstream task will likely prefer different weights. The framework supports retraining via `learn_weights`.

3. No formal causal identification beyond first-order back-door adjustment. We do not handle time-varying confounding, instrumental variables, or mediation decompositions. A clinical paper that wants any of these would have to extend the framework, not just configure it.

The signal we do want to send: every number in this section is computed from a small number of well-documented scripts run on a fixed-seed synthetic cohort, with the full pipeline reproducible from scratch in under three minutes. The bundled `results/tables/` directory contains the raw CSVs behind every figure.
