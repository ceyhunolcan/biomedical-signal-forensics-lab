# Limitations

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

A short, honest list of the things this framework does not do or does not do well. Listed because we would rather a user notice these now than discover them while writing their own paper.

## Synthetic-only validation

Every number in this repository is computed on synthetic data. The synthetic generator is parameterized to match patterns we observed in pilot work on real wearables (state-dependent missingness, heat-coupled HRV, motion-coupled PPG, device-bias offsets, skin-tone-coupled signal degradation), but those parameters are illustrative. Detector thresholds, model performance numbers, and trust-score categories all need to be recalibrated against real data before they mean anything for a specific device or cohort.

## Detector thresholds are hand-tuned

The five artifact detectors use thresholds that were chosen by inspecting their behavior on the synthetic generator. They are not learned from labeled data. They will not transfer to real devices without re-tuning. We provide `configs/artifact_detection.yaml` so this tuning is at least a config change rather than a code change.

## ICC(2,1) usage is unconventional

We apply ICC(2,1) to daily measurements within a participant by treating the day index as the "rater" axis. The classical ICC assumes a small fixed set of raters scoring each subject; substituting calendar days is irregular. We do it because the resulting number is useful for ranking participants by within-participant noise floor, but anyone reporting an ICC from this framework in a clinical paper should describe the design carefully or use the bootstrap test-retest in `src/reliability/test_retest.py` instead. Section 7 of `paper/results.md` shows the two methods give consistent rankings on the bundled cohort.

## No frequency-domain HRV

We report time-domain HRV (RMSSD, SDNN) but not LF/HF or other frequency-domain measures. The synthetic ECG/PPG windows are too short and too simple to support a meaningful frequency-domain HRV computation. Adding longer windows is a straightforward generator change; we did not include it because the framework's claims do not depend on it.

## Simple waveform models

The ECG-like windows are sums of narrow Gaussians at RR-spaced centers. The PPG-like windows are fundamentals plus second harmonics. These are sufficient for the artifact detectors to operate on but they are not a realistic test bed for waveform-based deep learning. If your goal is to develop new ECG morphology methods, this generator is the wrong tool.

## No firmware-drift simulation

Real wearables change their algorithms mid-study via firmware updates. A participant's measurements before and after a silent update can differ in ways that look like physiology but are pipeline changes. We do not simulate this. The closest proxy in our framework is the temporal-stability component, which would flag the resulting distribution shift, but it would not attribute it to a firmware event.

## Categorical fairness analysis is left to the user

The skin-tone proxy is in the generator and the trust score will respond to it correctly when used for per-stratum audits, but the bundled pipeline does not automatically produce a fairness report. Adding stratified trust scores by user-specified columns is on the to-do list.

## Confounding analysis is correlational

We report Pearson correlations between metrics and environmental covariates. We do not run formal causal-inference machinery (DAGs, instrumental variables, mediation analysis). The `confounding_risk` component should be read as "this is the maximum strength of association we found between a metric and a candidate confounder," not as a causal claim.

## API is single-cohort

The FastAPI service accepts a participant-level summary and returns a score. It does not maintain state across calls, store cohorts, or support comparison between cohorts. A real deployment for batch auditing would need a different architecture; the API is included so that the framework can be exercised end-to-end, not because we recommend it as production infrastructure.

## Dashboard caches aggressively

The Streamlit dashboard uses `@st.cache_data` on the data loader and trust-score computation. If you regenerate the synthetic data while the dashboard is running, the dashboard will continue to show the old cohort until you clear the cache or restart. This is the expected Streamlit behavior; we note it because it surprised us during development.

## No clinical validation

We have not validated any component of this framework against gold-standard clinical measurements. We have no plans to do so in this version. If you need a clinically validated signal-quality framework, this is not it.
