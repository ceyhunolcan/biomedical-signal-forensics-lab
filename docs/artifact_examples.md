# Artifact Examples

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

Worked examples of what each detector fires on. Use this as the manual reference when interpreting the audit report or tuning detector thresholds.

## Motion artifact (PPG)

**What the signal looks like.** A pulsatile waveform whose amplitude envelope drifts within the window, with extra high-frequency content above the heart-rate band. On a smartwatch this is what walking, hand-waving, or typing typically produces.

**Detector logic.** We compute the rolling amplitude variance and the ratio of power above 4 Hz to power in the 0.5–4 Hz cardiac band. Either being elevated raises the severity score.

**Common false positives.** Tachycardia. A genuinely fast heart rate increases the cardiac-band power but can also push spectral energy upward.

**Common false negatives.** Low-frequency baseline wander from clothing pressure. This shifts the DC level without injecting high-frequency power and is best caught by the bandpass step rather than the motion detector.

## Sensor dropout

**What the signal looks like.** Long runs of zero or near-zero values, often at the start of a recording or after a movement event that broke skin contact.

**Detector logic.** Identify samples with absolute value below a threshold, then run-length-encode. Any run longer than ~250 ms at the nominal sampling rate is flagged. Severity scales with the longest run as a fraction of the window.

**Common false positives.** Genuinely quiet physiology. We mitigate by requiring sustained low amplitude, not a single low sample.

**Common false negatives.** Saturation. An ADC clipped at its rail looks like a flatline, not a dropout, and is handled by the flatline detector instead.

## Noise spikes

**What the signal looks like.** Isolated samples whose magnitude is many standard deviations above the local distribution. Often electrical interference or contact glitches.

**Detector logic.** Robust z-score with the median absolute deviation as the spread estimate. Samples beyond ±6 MAD-z are flagged.

**Common false positives.** R-peaks on raw ECG before bandpass filtering. We always run detection after the bandpass step to avoid this.

## Flatline

**What the signal looks like.** A window of constant or near-constant value where physiology should produce visible variation.

**Detector logic.** Rolling variance over a short sub-window. If sub-window variance stays below a floor for more than a configurable fraction of the window, the window is flagged.

**When this fires legitimately.** ADC saturation, sensor unplugged, sensor pressed too hard against skin.

## Timestamp irregularity

**What the signal looks like.** A "regular" recording whose inter-sample times drift, jitter, or jump. The sample values themselves can look fine.

**Detector logic.** Compute consecutive timestamp deltas. Flag jitter as their standard deviation divided by the median delta. Flag gaps as the count of deltas above 2× the median.

**Why it matters.** RMSSD, SDNN, and every frequency-domain HRV metric assume the samples are equally spaced. A few percent of timing jitter shows up directly in HRV estimates.

## Impossible physiology

Hard thresholds applied to daily summaries. Defaults:

| Metric | Plausible range |
|--------|-----------------|
| Resting HR | 30 – 130 bpm |
| HRV RMSSD | 2 – 200 ms |
| HRV SDNN | 5 – 250 ms |
| Sleep duration | 0 – 14 hours |
| Sleep efficiency | 0 – 1 |
| Step count | 0 – 50,000 |

Values outside these ranges are flagged as a hard error rather than scored as low quality. The thresholds are wide so legitimate edge cases (a fit athlete, a sick day) aren't mislabeled.

## Wearable non-wear

Distinguished from sensor dropout by duration and by the corresponding `wearable_minutes` value. A day with fewer than ~6 hours of wear is not "missing data". It is a different kind of day, and we keep it out of within-participant stability calculations.

## How to test detector behavior

`tests/test_artifact_detection.py` contains the minimum a CI run should check: each detector fires on a clearly degraded signal and stays quiet on a clean one. When tuning thresholds, run these tests first; if they still pass on synthetic data, the threshold change is at least not catastrophic.
