# Signal Quality Taxonomy

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

This document defines the categories of signal quality issues the toolkit looks for. It is narrow: we describe what each label means, how we detect it on synthetic data, and what kind of false positive or negative to expect. The taxonomy is the contract between the artifact detectors, the trust score, and the audit report.

## Why a taxonomy at all

Most wearable papers report a single "signal quality" number per device or per study. That number hides everything that matters. A PPG window can be perfectly clean but recorded in the wrong physiological state. A heart-rate trace can be smooth and entirely fabricated by a manufacturer interpolation. Two devices can both score 0.9 on an internal quality metric and disagree by 4 bpm on the same wrist. A taxonomy with named, separately-measurable failure modes is the minimum needed to write down what a model is robust to and what it is not.

## Top-level categories

### 1. Acquisition-layer failures

Problems that originate at the sensor or its immediate firmware. Detectable from raw or near-raw windows.

- **Motion artifact.** Sensor displacement during movement corrupts the optical or electrical signal. We detect via short-window amplitude variance and an excess of high-frequency power relative to the cardiac band. Common on PPG during exercise, walking, or restless sleep.
- **Sensor dropout.** Extended zero or near-zero runs. Detected with run-length encoding on a low-amplitude mask. Distinguished from "non-wear" by duration and surrounding context.
- **Noise spikes.** Isolated samples or short bursts well outside the local distribution. Detected with a robust median absolute deviation z-score. Often electrical interference or contact noise.
- **Flatline.** Constant or near-constant value over a window where physiology should produce variation. Detected with rolling variance against a floor threshold.
- **Timestamp irregularity.** Sample-to-sample timing jitter or large gaps. Detected as deviation of inter-sample intervals from the nominal sampling period. Important because almost every downstream HRV metric assumes a regular grid.

### 2. Physiological-plausibility failures

Values that the sensor confidently reports but that are biologically implausible.

- **Out-of-range vitals.** Resting heart rate below 30 or above 130 bpm, RMSSD above 200 ms, sleep duration over 14 hours, etc. We treat these as hard flags rather than soft penalties.
- **Impossible transitions.** Day-over-day jumps that no physiology produces (e.g., a 40 bpm change in resting HR with no illness or fitness intervention).
- **Activity-vital inconsistency.** Very high step counts with extremely low heart rate, or zero motion with sustained tachycardia. Flagged but not auto-corrected.

### 3. Coverage failures

Problems with whether the signal was captured at all.

- **Low wearable minutes.** A daily summary built on under a few hours of wear time should not be treated like a 24-hour record.
- **Consecutive dropout days.** Strings of missing days bias longitudinal estimates more than the same total fraction scattered randomly.
- **State-dependent missingness.** Missingness that correlates with stress, sleep, or activity is informative, not random, and breaks every standard imputation method.

### 4. Cross-source reliability failures

Problems that only show up when the same construct is measured more than once.

- **Test-retest drift.** Within-participant scores from adjacent weeks that disagree more than the cohort's between-participant spread.
- **Device bias.** Systematic offsets between device models that survive after participant-level matching.
- **Algorithm version drift.** Manufacturer-side firmware or pipeline changes that move the mean. We don't simulate this directly but flag time periods where the empirical distribution shifts.

## Severity levels

For each finding we report a severity in `[0, 1]`. The conventions are simple:

| Severity | Meaning |
|----------|---------|
| 0.0 – 0.2 | Detected but unlikely to affect downstream metrics |
| 0.2 – 0.5 | Window or day should be flagged in any analysis |
| 0.5 – 0.8 | Window or day should be excluded from primary analysis |
| 0.8 – 1.0 | Strong evidence the data are unreliable |

These cutoffs are chosen to be easy to communicate, not because they came from a calibration study. Treat them as starting points.

## What is out of scope

- **Arrhythmia or rhythm classification.** Not a diagnostic project.
- **Sleep staging.** We use sleep duration and efficiency as inputs but do not produce stage labels.
- **Stress prediction.** `stress_proxy` is an input feature, not a target.
- **Device-specific tuning.** Detectors use thresholds that should be re-calibrated for any real device family.

## How the taxonomy maps to the trust score

The Digital Biomarker Trust Score has six components. Each one consumes a subset of the taxonomy:

- `signal_quality_score` ← acquisition-layer findings, aggregated
- `artifact_burden_score` ← acquisition-layer + physiological-plausibility, weighted by severity
- `temporal_stability_score` ← cross-source reliability (test-retest, drift)
- `missingness_risk_score` ← coverage failures plus state-dependent missingness
- `device_bias_score` ← cross-source reliability (device offsets)
- `confounding_risk_score` ← interactions between environmental/behavioral covariates and the metric of interest

See `paper/signal_quality_framework.md` for the formal definitions and weighting.
