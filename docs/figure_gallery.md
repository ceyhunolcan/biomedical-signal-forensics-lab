# Figure Gallery

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

Reference list of the figures the report generator produces. Each figure lives in `results/figures/` after running `scripts/run_signal_audit.py` and `scripts/generate_report.py`. The intent is to make each figure self-explanatory in a paper appendix or supplementary file.

## `signal_example.png`

Two stacked panels: a representative ECG window on top, the matching PPG window below. Same time axis. Sampling rates are annotated. This is the "what does the raw data even look like" figure.

Use this to:
- give a reviewer a concrete sense of the windows the detectors operate on
- show one clean and one degraded example side by side in a supplementary

## `trust_radar.png`

Polar plot of the six Digital Biomarker Trust Score components for a single cohort or participant. Axis range is fixed at 0–100 so radars from different cohorts can be compared visually.

The six axes:
- signal quality
- artifact burden (higher = cleaner)
- temporal stability
- missingness risk (higher = lower risk)
- device bias (higher = less bias)
- confounding risk (higher = less confounded)

Higher and more uniform shapes are better. A spiky radar is informative even when the overall score is reasonable.

## `trust_distribution.png`

Histogram of overall trust scores across the cohort, with vertical dashed lines at the high / moderate / low thresholds (default 80 / 60 / 40). Useful for screening: a cohort where most participants fall in the low band is not ready for downstream modeling.

## `reliability_heatmap.png`

Participant × metric matrix of within-participant variability (coefficient of variation, clipped to a sensible range). Rows are participants sorted by overall reliability, columns are the per-day metrics. Dark cells mean high CV (unstable). This is the figure that surfaces which metric is the weak link for a given device or cohort.

## `confounding_scatter.png`

Scatter plot of an environmental variable against a physiological metric, with a linear fit overlaid. Default is heat index vs. HRV RMSSD because heat is the most consistent confounder in the synthetic generator. The slope and r-value are annotated. If the slope is large, downstream HRV-based models will pick up weather, not physiology.

## How to extend the gallery

To add a figure type, follow the pattern in `src/reports/figure_builder.py`:

1. Write a function that takes a dataframe (and any options) and returns a Matplotlib `Figure`.
2. Apply the shared style via `src.utils.plotting.apply_style`.
3. Save with `src.utils.plotting.savefig` so DPI and bbox are consistent.
4. Add the function to `write_all` so it runs as part of the standard report build.

Matplotlib only. The shared style is restrained (small font sizes, no grid by default, single-color emphasis) because these figures are meant for journal supplements, not slide decks.
