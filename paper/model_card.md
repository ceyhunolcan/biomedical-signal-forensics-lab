# Model Card

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

## Overview

This card documents the model components bundled with `biomedical-signal-forensics-lab`. There are two tiers:

**Baselines (the contribution side).** These three are trained, evaluated, and reported in the headline leaderboard. They demonstrate that the framework's signal-quality and artifact-burden estimates can be used as training targets.

1. Logistic regression (linear baseline)
2. Random forest (nonlinear ensemble baseline)
3. Isolation forest (unsupervised anomaly detector baseline)

**Extension points (not the contribution).** These exist as code scaffolding for users who want to plug in deep models. They are not in the headline leaderboard, not trained or evaluated as part of the canonical pipeline by default, and not proposed as anyone's preferred quality detector. If you want to extend the framework with a deep model, read these as starter code, not as a benchmark.

4. Quality autoencoder (PyTorch): `src/models/quality_autoencoder.py`
5. Sequence GRU (PyTorch): `src/models/sequence_model.py`

PyTorch components live as extension points rather than headline models. The framework's contribution is the auditable pipeline and the trust score, not a novel detector. A hand-tuned autoencoder in the leaderboard would invite comparisons against the wearable-quality literature that the framework is not positioned to win or lose.

All bundled components are trained on synthetic data only. None are proposed as detectors anyone should deploy.

## Intended use

- Sanity-check the trust-score pipeline on synthetic data.
- Provide a baseline against which new detectors can be compared.
- Populate `results/model_leaderboard.csv`.

## Out-of-scope use

- Predicting any clinical outcome.
- Triggering an alert in a consumer wearable application.
- Quality scoring for any specific commercial device without re-training and re-validation.
- Any deployment outside an explicitly research-only context.

## Training data

All training data is synthetic (300 participants × 60 days, ~18,000 daily records, ~1,800 short signal windows). Generation is described in `paper/data_card.md`. No human data of any kind is used to train the bundled checkpoints.

## Features

The four feature groups (see `src/models/anomaly_detector.py` for the exact column names):

- **Signal features.** Mean and standard deviation of resting HR, HRV RMSSD/SDNN, sleep duration and efficiency, step count, wearable minutes.
- **Artifact features.** Per-day aggregated motion, dropout, noise-spike, and flatline severities (when window data is available).
- **Reliability features.** Rolling CV of resting HR and HRV, drift slope of the same.
- **Confounding features (autoencoder + confounding variant only).** Temperature, humidity, AQI, heat index.

## Targets

The models are trained to predict the `signal_quality_ground_truth` and `artifact_burden_ground_truth` fields. These are themselves synthetic. We do not pretend they are clinical ground truth.

## Evaluation

Held-out test set is a 20% participant-level split (i.e., participants in the test set do not appear in training). Metrics:

- `quality_detection_AUROC`: AUROC for binary quality (ground truth > 0.7).
- `artifact_detection_F1`: macro F1 for high-artifact-burden day flagging.
- `calibration_error`: expected calibration error at 10 bins.
- `robustness_score`: fraction of test-set predictions preserved under controlled Gaussian feature perturbation.

Numbers populate `results/model_leaderboard.csv` after running `scripts/train_quality_model.py`.

## Known failure modes

- The autoencoder reconstructs the dominant cohort distribution well and fails on tails. The "+ confounding" variant partially compensates but introduces a different failure: it learns to use environmental covariates instead of signal features when both are predictive.
- Isolation forest is sensitive to feature scaling. We standardize inside the pipeline, but downstream users moving to real data should re-check.
- None of the models have been audited for performance differences across the simulated skin-tone proxy or device-type strata. This is deliberate. Running that audit is on the to-do list, and is exactly the kind of analysis the framework is supposed to make easy.

## Fairness considerations

The synthetic generator includes a `skin_tone_proxy` that applies a documented penalty to PPG signal quality. This is included so that any downstream fairness audit on real data has a synthetic analog to test against. The bundled models do not adjust for it and should not be assumed to be fair across that axis. See `paper/ethics.md` for discussion.

## Environment

- Python 3.11+
- CPU-only by default. PyTorch will use a GPU if available but training time on the synthetic cohort is small enough that this is not necessary.
- Approximate training time on a 2024 laptop CPU: under 1 minute for the baselines, under 2 minutes for the autoencoder.

## Version

Model card version: 0.1.0. Matches the `biomedical-signal-forensics-lab` package version. Update both together when retraining.
