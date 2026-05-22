# Real-data pilot: WESAD

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

- Dataset: **wesad**
- Subjects: **2**
- Windows extracted: **850**

## In-house SQI vs Orphanidou (2015)

- In-house mean PPG SQI: **0.986**
- In-house mean ECG SQI: **0.986**
- Spearman ρ vs Orphanidou template correlation: **0.26738081868299757**

## SQI by labeled state

| State | n | ECG SQI | PPG SQI | PPG motion |
|---|---|---|---|---|
| amusement | 146 | 0.985 | 0.982 | 0.033 |
| baseline | 455 | 0.987 | 0.988 | 0.022 |
| stress | 249 | 0.983 | 0.984 | 0.029 |

## What this pilot does and doesn't tell us

WESAD has ~60 minutes per subject and no multi-day longitudinal data. We can therefore validate per-window signal quality and artifact-burden estimates, but not test-retest reliability, missingness dynamics, weekly reproducibility, or device-bias comparisons across calendar time. For those analyses, MIMIC-PERform or an AppleWatch-MIMIC subset is a better fit.

Numbers above were produced by `scripts/run_real_data_pilot.py --dataset wesad`. CSVs are alongside this report.