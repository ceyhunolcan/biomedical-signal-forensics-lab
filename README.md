# biomedical-signal-forensics-lab

**A toolkit for detecting artifacts, confounding, and reliability failures in wearable physiological signals.**

[![tests](https://github.com/PLACEHOLDER/biomedical-signal-forensics-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/PLACEHOLDER/biomedical-signal-forensics-lab/actions/workflows/tests.yml)
[![lint](https://github.com/PLACEHOLDER/biomedical-signal-forensics-lab/actions/workflows/lint.yml/badge.svg)](https://github.com/PLACEHOLDER/biomedical-signal-forensics-lab/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device. Outputs are signal-quality estimates and methodological recommendations, not clinical findings.

**Quick links:** [Results](paper/results.md) · [Methods](paper/methods.md) · [Limitations](paper/limitations.md) · [Ethics](paper/ethics.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md)

---

## What it is

A wrist-worn HR reading is already a model output. By the time it reaches your dataframe it has passed through optical sensing, motion correction, manufacturer-specific filtering, and a peak detector you don't see. So when downstream code treats that number as ground truth and trains on it, what's actually being learned is partly physiology and partly the device's idiosyncrasies.

This repo runs an audit before that step. It checks five things on the same data:

- Are the signals clean enough to use? (signal quality, artifact burden)
- Are repeated measurements on the same person stable? (test-retest, ICC, drift)
- Do different devices agree on the same person? (device bias)
- Are environmental variables driving the results? (heat, AQI, motion as confounders)
- Is missingness random, or does it correlate with the state you care about? (state-dependent missingness)

Each check produces a score in 0–100. Together they roll up to a single number called the **Digital Biomarker Trust Score**, reported with its components so you can see which one is dragging it down.

The whole thing runs on synthetic data: 300 simulated participants over 60 days, with realistic state-dependent missingness, heat-coupled HRV, motion-coupled PPG noise, three device families with different biases, and a skin-tone proxy that depresses PPG SQI. The synthetic cohort exists so the audit pipeline has something concrete to chew on. Nothing here has been validated against a real wearable. The framing is methodological, not clinical.

Bundled with the audit pipeline: three baseline detectors (logistic regression, random forest, isolation forest), a small PyTorch autoencoder, a FastAPI service, a Streamlit dashboard, and a script that generates a markdown report with figures. CPU only.

---

## Why bother

Most wearable-AI papers report a single signal-quality number per device or per study and treat it like a property of the device. It isn't. The same device can produce reliable HR estimates while a participant is sitting still and badly biased estimates while they're walking. If your held-out test set is dominated by sitting, you won't notice. Three things in particular keep showing up:

1. **Artifacts that look like physiology.** A PPG dropout during a run reads, to a downstream model, like a sudden change in vascular tone. Most "free-living" datasets are dominated by motion noise that gets averaged into the daily summary.
2. **Environmental confounding.** Heat suppresses HRV. Poor air quality fragments sleep. A multi-site cohort can produce a "biomarker" that is mostly a weather instrument.
3. **State-dependent missingness.** People stop wearing the device when they're sick, stressed, traveling, or sleeping poorly. Exactly the days the model most wants to see. Imputing those days as if they were random makes things worse, not better.

The framework treats those three as the main thing, not as nuisance variables to be dropped.

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │  Synthetic Signal Generator         │
                    │  (participants × days × windows)    │
                    └──────────────┬──────────────────────┘
                                   │
                ┌──────────────────┼─────────────────────┐
                ▼                  ▼                     ▼
        ┌──────────────┐   ┌──────────────┐     ┌──────────────┐
        │   Signals    │   │  Artifacts   │     │ Confounding  │
        │  ECG/PPG/HRV │   │  Motion/etc. │     │  Heat/AQI    │
        └──────┬───────┘   └──────┬───────┘     └──────┬───────┘
               │                  │                    │
               └──────────────────┼────────────────────┘
                                  ▼
                       ┌─────────────────────┐
                       │  Reliability Engine │
                       │  ICC / Test-Retest  │
                       └──────────┬──────────┘
                                  ▼
                       ┌─────────────────────┐
                       │ Digital Biomarker   │
                       │   Trust Score       │
                       └──────────┬──────────┘
                                  ▼
                    ┌──────────┬──┴──┬─────────┐
                    ▼          ▼     ▼         ▼
                 Report      API   Dashboard  Model
                 (Markdown)  (FastAPI) (Streamlit)  (PyTorch)
```

---

## Signal-quality taxonomy

| Layer | What it captures | Example metric |
|---|---|---|
| **Acquisition** | Was the sensor in contact, sampling at the expected rate? | non-wear minutes, sampling regularity |
| **Waveform** | Is the raw signal physiologically plausible? | SQI, flatline ratio, impossible-value count |
| **Feature** | Are derived features (HRV, peak intervals) stable under perturbation? | RMSSD, coefficient of variation |
| **Daily summary** | Does the day-level number reflect a representative window? | wearable-minute coverage, weighted SQI |
| **Cross-day** | Is the signal reproducible within-person across days? | ICC, rolling CoV, drift |

## Artifact taxonomy

- **Motion**: high-frequency baseline wander, PPG amplitude variance
- **Dropout**: sustained zero or NaN segments
- **Noise spike**: point outliers exceeding plausible physiological deltas
- **Flatline**: sub-physiological variance over an extended window
- **Timestamp irregularity**: jitter, gaps, or duplicates in the time index
- **Impossible physiology**: values outside survivable ranges (HR < 25, > 220, etc.)
- **Non-wear**: extended low-motion plus flat-PPG combination

## Reliability framework

The reliability engine computes test-retest correlation, intraclass correlation coefficient (ICC(2,1) form), day-to-day stability via rolling coefficient of variation, missingness-adjusted reliability, device-bias estimates from group comparisons, and temporal drift via slope on a normalized rolling mean. All metrics are reported with confidence intervals where possible.

## Digital Biomarker Trust Score

Six sub-scores, each in [0, 100], combined with documented weights:

| Component | Default weight |
|---|---|
| `signal_quality_score` | 0.25 |
| `artifact_burden_score` | 0.20 |
| `temporal_stability_score` | 0.20 |
| `missingness_risk_score` | 0.15 |
| `device_bias_score` | 0.10 |
| `confounding_risk_score` | 0.10 |

Weights are exposed in `configs/reliability.yaml` and a sensitivity analysis over them is part of the test suite. Output categories: `high` (≥80), `moderate` (60–79), `low` (40–59), `unreliable` (<40).

---

## Publication-level extensions (v0.2)

The default pipeline above is the screening layer. Five additional modules turn that screening into a defensible adjusted analysis. All of them run automatically as part of `scripts/run_signal_audit.py` and contribute sections to the generated report.

### 1. Causal-adjusted confounding (`src/confounding/causal_inference.py`)
Pearson correlations are a fast screen, not an estimate. This module adds:
- A minimal DAG class with back-door identification (no networkx dependency).
- **G-computation** (standardization) with bootstrap CIs.
- **AIPW** (augmented inverse-propensity weighting), a doubly-robust estimator that is consistent if either the outcome model or the propensity model is correct.
- A `screening_vs_adjusted_table` helper that emits both columns side by side.

On the synthetic cohort, the screening correlation `heat_index → hrv_rmssd` of -0.054 shrinks to an AIPW estimate of +0.25 (CI [-0.60, +1.03]) once you adjust for stress, activity, sleep, AQI, and temperature. Exactly the kind of "the correlation was doing the work for something else" pattern the audit is supposed to surface.

### 2. Change-point surveillance (`src/reliability/change_point.py`)
Detects step changes in any per-participant daily-summary series. Two implementations:
- **Binary segmentation** (offline, fast, F-stat stopping rule).
- **BOCPD** (Bayesian online change-point detection) with a Normal-Inverse-Gamma model and MAP-run-length collapse as the detection signal.

The intended use is firmware-drift surveillance: a cluster of change-points at the same calendar week across many participants strongly suggests a manufacturer pipeline change rather than physiology. The function `scan_cohort` runs detection per participant and returns a long-format frame ready to plot.

### 3. Stratified fairness audit (`src/reliability/fairness_audit.py`)
Recomputes the full six-component DBTS within each level of a chosen stratifier (`device_type`, `skin_tone_proxy`, age band, sex, whatever) with cluster-bootstrap CIs on the overall score. The companion `disparity_summary` ranks components by the max–min gap so the worst-off stratum is easy to find. A forest plot is added to the figure gallery (`results/figures/fairness_forest_*.png`).

On the bundled synthetic cohort the audit recovers both injected biases cleanly: device_C scores 13 points below device_A on signal quality (matches the 0.85 vs 1.0 SQI multiplier), and the skin-tone-proxy Q4 stratum scores 9.5 points below Q1 (matches the 0.12 × proxy penalty).

### 4. Learned trust-score weights (`src/reliability/weight_optimization.py`)
The default six weights are a prior, not a discovery. This module:
- Defines a downstream reproducibility target (week-over-week stability of a chosen metric, default HRV RMSSD).
- Searches the 6-simplex via Dirichlet sampling + local-grid refinement for the weighting that maximizes Spearman ρ between DBTS and the target.
- Reports both the train and **30% participant-held-out** correlations.
- Includes a `sensitivity_table` that quantifies how much the participant ranking moves under small weight perturbations.

On the synthetic cohort this recovers `temporal_stability_score` as the dominant predictor (learned weight 0.81 vs default 0.20), with holdout ρ ≈ +0.59 and a participant-ranking that is stable to perturbations of magnitude 0.2 (median rank correlation > 0.98).

### 5. Real-data adapter framework (`src/data/real_data_adapter.py`)
The framework's claim only matters if it can run on real data. This module supplies:
- A `RealDataAdapter` base class that maps a foreign schema onto our canonical columns, validates the result, and writes a schema-compliant CSV.
- Three reference adapters (`FitbitLikeAdapter`, `EmpaticaLikeAdapter`, `GenericDailySummaryAdapter`) that handle the unit conversions and column renames real exports actually need.
- `recalibrate_detector`, which takes labeled artifact data and re-tunes any detector's threshold by maximizing F1 against the labels.

The adapters are tested against synthetic foreign-schema fixtures. No real datasets are bundled.

---

## Synthetic data

The generator produces a cohort with realistic biological and behavioral correlations rather than independent Gaussians:

- Motion increases PPG noise and shrinks the usable window for HRV.
- Heat reduces sleep efficiency and HRV with a person-specific sensitivity.
- AQI shifts sleep architecture and next-day fatigue proxies.
- Device type biases HR and PPG quality (we ship three synthetic device classes).
- Missingness is state-dependent: low-wear days cluster around poor-sleep and high-stress days, not uniformly at random.
- Skin-tone proxy modulates PPG SNR in a fixed, documented way to allow downstream bias auditing.

The defaults: 300 participants × 60 days = 18,000 daily records, plus 5-second short windows per participant-day for ECG- and PPG-like waveform inspection.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Pipeline

```bash
# 1. generate synthetic dataset (writes data/synthetic/synthetic_signal_dataset.csv)
python scripts/run_pipeline.py

# 2. run the forensic audit (artifacts, reliability, confounding)
python scripts/run_signal_audit.py

# 3. train the quality autoencoder + baselines
python scripts/train_quality_model.py

# 4. generate the markdown report
python scripts/generate_report.py

# 5. launch the Streamlit dashboard
python scripts/launch_dashboard.py

# 6. launch the FastAPI service (separate terminal)
uvicorn src.api.main:app --reload --port 8000
```

## Tests

```bash
pytest -q
```

## Docker

```bash
docker compose up --build
```

---

## Example outputs

After running the pipeline you'll find:

- `data/synthetic/synthetic_signal_dataset.csv`: daily and static cohort table
- `data/synthetic/synthetic_windows.npz`: short signal windows
- `results/figures/`: trust-score radar, reliability heatmap, confounding scatter
- `results/reports/signal_forensics_report.md`: full audit report
- `results/model_leaderboard.csv`: comparative model performance

A condensed example of the report's headline section:

```
Cohort: 300 participants, 60 days
Mean Digital Biomarker Trust Score: 67.4 (moderate)
Participants with trust score < 40: 38 (12.7%)
Top confounder: heat_index ↔ hrv_rmssd, r = -0.31
Top device-bias delta: device_B vs device_A on resting_hr, +3.8 bpm
Recommended exclusions: 7.2% of participant-days
```

---

## Limitations

The data is synthetic. The biological correlations are hand-coded to be plausible, not exhaustive. We don't simulate every artifact mode found in real PPG (e.g. ambient light leakage), every HRV correction scheme, or every wear-time policy. The trust score is a methodological summary, not a calibrated probability of anything clinical. The framework is meant to be a scaffold that real signals can be plugged into, with the synthetic cohort serving as a development substrate.

## Ethics

No human data is used. The skin-tone proxy is included so downstream fairness audits of PPG-based features have something to test against. It is a documented, controllable variable, not a personal identifier. All outputs are framed as research-methodological recommendations. No clinical claims are made. We use "participant", "signal-quality estimate", and "non-clinical audit" instead of "patient", "diagnosis", or "treatment".

## Citing this work

If this scaffold is useful in a methodological paper or audit:

```
Biomedical Signal Forensics Lab (2026). A reliability framework for wearable-derived
digital biomarkers. Research prototype. https://github.com/<user>/biomedical-signal-forensics-lab
```

A draft preprint outline lives in `paper/preprint_outline.md`.
