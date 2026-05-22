# Signal Quality Framework

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

## Framing

We treat "signal quality" not as a single scalar but as the conjunction of properties a downstream researcher actually cares about. A digital biomarker is fit for purpose when:

1. The underlying signal is not corrupted by acquisition-layer artifacts.
2. The reported values are physiologically plausible.
3. There is enough coverage over the relevant time window.
4. Repeat measurements on the same person agree within reason.
5. Measurements across devices agree within reason.
6. The variability we see is not explainable by environment or behavior alone.

Conditions 1-3 are properties of a window or a day. Conditions 4-6 require pooling across windows, days, participants, or devices. Any single-number "quality score" fails to separate these, which is why we report six components.

## Acquisition quality

For each window we compute a signal quality index (SQI) appropriate to the modality:

- **ECG-SQI.** Bandpass to 5-15 Hz, detect R-peaks, compute the dispersion of inter-peak intervals after rejecting non-physiological gaps, and combine with the residual energy in the 30-80 Hz noise band.
- **PPG-SQI.** Bandpass to 0.5-4 Hz, detect pulse peaks, compute beat-to-beat amplitude consistency, and penalize high-frequency content above 4 Hz.

These are simple. Better SQI estimators exist in the literature (template matching, learned quality classifiers). We use the simple version because the framework's claim is not "our SQI is the best." The claim is that an SQI score alone is insufficient and must be combined with the remaining five components.

## Plausibility

A short list of hard thresholds on daily summaries (see `docs/artifact_examples.md`). Out-of-range values are flagged as a hard error rather than smoothly scored as low quality. The choice matters: a model trained with a soft penalty on impossible heart rates can learn to predict them; a hard exclusion cannot.

## Coverage

Coverage failures are quantified two ways. First, the per-day missing fraction is computed from `wearable_minutes`. Second, we run-length-encode the binary "missing today" sequence per participant and report the longest run. The two numbers behave differently: 30% of days missing scattered randomly is recoverable; 30% missing in a single block is not. The `missingness_risk` component penalizes long runs disproportionately.

## Reliability

We compute three reliability statistics per participant per metric:

- Split-half correlation between odd-indexed and even-indexed days.
- ICC(2,1) treating the day index as a "rater". Unconventional but useful for surfacing within-participant noise floors.
- Rolling coefficient of variation, smoothed over a configurable window (default 7 days).

These are reported as raw numbers in the audit report and combined into the `temporal_stability` component via a monotone transform onto `[0, 100]`.

## Cross-device agreement

For each non-reference device family, we compute the mean offset against device A on every continuous metric and divide by the cohort standard deviation of that metric. This is a deliberate choice. Bland-Altman plots would be more informative for a clinical paper, but the normalized offset compresses well into a single component score and is easier to threshold in CI.

The `device_bias` component is 100 minus the maximum normalized bias across metrics, clipped to `[0, 100]`. A cohort where the worst device-by-metric offset is half a cohort standard deviation gets a device_bias score around 50.

## Confounding risk

We compute the Pearson correlation between each daily metric (HRV, sleep efficiency, resting HR, step count) and each environmental or behavioral covariate (temperature, AQI, heat index, motion proxy, sleep deficit). The `confounding_risk` component is 100 minus the maximum absolute correlation across (metric, covariate) pairs, scaled.

A confounding score of 100 means "no environmental variable correlates with any metric of interest." That is essentially never the case in a real cohort. A more honest interpretation is: a score below ~70 means at least one covariate has a correlation with at least one outcome strong enough to bias any downstream model that does not adjust for it.

## Aggregation

The overall score is a weighted mean of the six components. The defaults in `configs/reliability.yaml` weight signal quality highest (0.25), artifact burden and temporal stability next (0.20 each), missingness third (0.15), and device bias and confounding risk last (0.10 each).

These weights reflect a specific value judgment: we trust acquisition-layer measurements more than aggregated reliability statistics because they are easier to inspect. A research group using this framework should adjust the weights to match its own value judgment and report the change explicitly. We resist the temptation to learn the weights from data because there is no held-out label that we trust to learn them against.

## Category thresholds

| Category | Overall score | Recommended action |
|----------|---------------|--------------------|
| high | ≥ 80 | Use for primary analysis with standard reporting |
| moderate | 60 - 80 | Use with sensitivity analyses and stratification |
| low | 40 - 60 | Use only as a covariate or with strict exclusion |
| unreliable | < 40 | Do not use in modeling without auditing per-day flags first |

These cutoffs are starting points, not law. They were chosen to be roughly evenly spaced and to match the bands a reviewer would intuitively expect.
