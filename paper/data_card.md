# Data Card

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

## Dataset name

`synthetic_signal_dataset`, bundled with `biomedical-signal-forensics-lab` v0.1.0.

## Summary

Synthetic wearable-physiology dataset for development and testing of signal-quality and reliability auditing methods. Built to expose, in a reproducible form, the kinds of failure modes we observed in pilot work on real wearables: state-dependent missingness, environmental confounding, device-bias offsets, motion-induced PPG artifacts, and skin-tone-coupled signal degradation.

## What's in it

- **Daily summaries:** 300 participants × 60 days = 18,000 records (minus state-dependent missingness, so the realized count is lower).
- **Short signal windows:** approximately 10% of participant-days carry a 5-second ECG-like window at 250 Hz and a 5-second PPG-like window at 64 Hz. Realized count is roughly 1,800 windows.
- **Static participant attributes:** age, sex, baseline heart rate, baseline HRV, baseline activity, device type, skin-tone proxy, climate sensitivity, missingness tendency.
- **Daily metric columns:** resting HR, HRV (RMSSD, SDNN), step count, active minutes, sleep duration, sleep efficiency, stress proxy, temperature, humidity, AQI, heat index, wearable minutes, missing-flag.
- **Ground-truth columns:** signal_quality_ground_truth, artifact_burden_ground_truth, reliability_ground_truth, each in `[0, 1]`. Synthetic. Used as training targets.

## How it's generated

Source: `src/data/synthetic_signal_generator.py`. The generator is parameterized via `CohortSpec`. The default configuration matches `configs/default.yaml`. See `paper/methods.md` for the full generative model.

Key generative choices documented in the methods file:

- Heat load depresses HRV and shortens sleep with a participant-specific sensitivity.
- High activity injects motion noise into next-day PPG.
- Three device families with documented HR offsets and SQI multipliers.
- Skin-tone proxy applies a 0.12 × proxy penalty to PPG SQI.
- Missingness probability depends on stress, sleep efficiency, and heat load.

## What it does *not* contain

- No human data of any kind. No PII, no PHI, no real wearable recordings, no de-identified clinical data.
- No clinical labels. The ground-truth columns are synthetic by construction.
- No arrhythmia simulation. The ECG waveform model is simple.
- No sleep staging.

## Intended use

- Develop and unit-test signal-quality, artifact-detection, and reliability methods.
- Reproduce all figures and statistics in this repository.
- Benchmark new detectors against the bundled baselines.
- Demonstrate the framework in teaching settings.

## Out-of-scope use

- Training any model intended for deployment on real wearables.
- Validating any clinical claim, even indirectly.
- Benchmarking commercial signal-quality pipelines.

## Known biases

- The generator imposes a specific bias pattern (skin-tone-coupled PPG penalty, device-bias offsets, heat-coupled HRV depression). These are features for the purpose of fairness auditing; they are not claims about any specific real-world device or population.
- The synthetic ECG/PPG waveforms are simple enough that detectors tuned to them will not necessarily transfer.
- Missingness is state-dependent but does not include the kinds of missingness driven by software bugs, account problems, or device returns. Important real-world sources we did not model.

## Distribution

Generated on demand. `scripts/run_pipeline.py` writes the CSV to `data/synthetic/synthetic_signal_dataset.csv` and the windows to `data/synthetic/synthetic_windows.npz`. The repository does not ship pre-generated data; running the pipeline is the canonical way to obtain the dataset.

## Reproducibility

Seed is fixed in `configs/default.yaml` (default: 42). Re-running the generator with the same seed produces byte-identical output (modulo platform-specific float behavior). When changing the seed, document the new value in any analysis that depends on it.

## License

Released under the same MIT license as the rest of the repository, with the additional non-clinical-use statement in `LICENSE`. Because the data is synthetic, there are no participant consent constraints.

## Version

Data card version: 0.1.0. Matches the package version. Update both together when the generator changes.
