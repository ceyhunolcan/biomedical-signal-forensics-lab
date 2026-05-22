# Methods

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

## Cohort

The reference cohort is synthetic: 300 simulated participants, 60 days each, with daily summary records and a 10% random sample of short ECG-like and PPG-like windows. Static participant attributes include age, sex, baseline heart rate, baseline HRV, baseline activity, device type (one of three simulated families), a skin-tone proxy, a climate-sensitivity coefficient, and a per-participant missingness tendency. The generator is parameterized so that a researcher can adjust cohort size, day count, and the strength of each confounding pathway without modifying source code.

The synthetic cohort exists to allow reproducibility of every figure and statistic in the audit pipeline without distributing identifiable data. It is not a replacement for validation on real wearable data. Anyone applying the framework to a real device should expect to recalibrate detector thresholds.

## Daily-summary generative model

For each participant-day, the generator first draws a stress level, then derives sleep, HRV, and activity from a participant-specific baseline plus state-dependent perturbations:

- Heat load (temperature_c + a humidity term) shortens sleep and depresses RMSSD with a participant-specific sensitivity.
- Air quality (AQI) reduces sleep efficiency above a threshold.
- High activity days raise step counts and active minutes and inject motion noise into the next-day PPG windows.
- Device type contributes a fixed additive offset to resting HR (device B: +3.8 bpm, device C: −2.1 bpm, with device A as reference) and a multiplicative penalty to signal-quality ground truth (0.92 and 0.85 respectively).
- Skin-tone proxy applies a documented 0.12 × proxy penalty to PPG signal quality. This is included specifically so downstream fairness audits have something to find.

Missingness is state-dependent. The per-day probability that a record is missing is:

```
miss_prob = participant_tendency
          + 0.15 × stress
          + 0.08 × (1 − sleep_efficiency)
          + 0.01 × heat_load
```

capped at 0.6. State-dependent missingness is the single most important property of the generator. It is what breaks naive imputation methods and what makes "missingness as signal" a meaningful module rather than a slogan.

## Short signal windows

For ~10% of participant-days the generator emits a 5-second ECG-like window at 250 Hz and a 5-second PPG-like window at 64 Hz. The ECG is a sum of narrow Gaussians at RR-interval-spaced centers plus white noise scaled by per-day noise level. The PPG is a fundamental sinusoid at the day's heart rate plus a second harmonic plus noise scaled by motion proxy. These won't fool a cardiologist. They give the artifact detectors something concrete to operate on, which is all we need for the methodological claim.

## Artifact detection

Five detectors operate on each window: motion, sensor dropout, noise spike, flatline, and timestamp irregularity. Each returns an `ArtifactFinding` with a boolean flag, a severity in `[0, 1]`, and a short text explanation. The window-level classifier aggregates findings into a single artifact burden.

Detector thresholds are configurable in `configs/artifact_detection.yaml` and were hand-tuned on the synthetic generator. We do not claim these thresholds transfer to real devices.

## Reliability metrics

We report:

- **Test-retest reliability.** Split-half correlation within each participant's daily-summary series.
- **Intraclass correlation coefficient.** ICC(2,1) two-way random, absolute agreement formulation, applied to repeated daily measurements as if the daily index were the "rater" axis.
- **Temporal stability.** Rolling coefficient of variation over a configurable window plus a drift slope from a linear fit.
- **Device bias.** Per-column mean offset between each non-reference device and device A, normalized by the cohort standard deviation of the column.

The reliability module is conservative. It does not produce confidence intervals on these statistics; those depend on cohort structure decisions that should be made downstream.

## Digital Biomarker Trust Score

Six components, each scaled to `[0, 100]` so that higher is always better:

| Component | Source |
|-----------|--------|
| signal_quality | aggregated SQI on windows, calibrated against ground-truth quality when present |
| artifact_burden | mean window-level burden, inverted |
| temporal_stability | inverse rolling CV, capped |
| missingness_risk | inverse missing fraction with a penalty for consecutive runs |
| device_bias | inverse normalized bias against the reference device |
| confounding_risk | inverse maximum absolute correlation between metrics and environmental/behavioral covariates |

The overall score is a weighted mean with weights specified in `configs/reliability.yaml`. Defaults: signal_quality 0.25, artifact_burden 0.20, temporal_stability 0.20, missingness_risk 0.15, device_bias 0.10, confounding_risk 0.10. Category thresholds: high ≥ 80, moderate ≥ 60, low ≥ 40, below that "unreliable."

The weights are not learned. They are a defensible default that we expose because the right weighting depends on the downstream use. A study that filters by wear time can de-emphasize missingness; a study that compares devices cannot de-emphasize device bias.

## Models

Three baselines and two PyTorch models. The baselines (logistic regression, random forest, isolation forest) operate on tabular signal/artifact/reliability features extracted from daily summaries. The PyTorch models are a small autoencoder over the same feature set and a variant that additionally consumes environmental and behavioral confounders. The autoencoder has three hidden layers (widths 32, 16, 8); it trains from a cold start on CPU in under a minute on the synthetic cohort.

We do not propose any of these as final models. They exist to demonstrate that the framework's outputs are usable as training targets and to populate the model leaderboard.

## Evaluation

We report AUROC for quality detection, macro F1 for artifact detection, expected calibration error, and a robustness score computed by perturbation stability: predictions on the test set are compared to predictions on the same set with controlled noise injected, and the score is the fraction of predictions that survive the perturbation. None of these numbers should be interpreted as performance on real wearables.

## Reproducibility

Every figure and statistic in the audit pipeline is produced by `scripts/run_pipeline.py`, `scripts/run_signal_audit.py`, `scripts/train_quality_model.py`, and `scripts/generate_report.py`, in that order. Seeds are fixed in `configs/default.yaml`. Outputs land under `results/`. The whole pipeline runs end-to-end on a laptop in a few minutes.
