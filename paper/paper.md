---
title: 'biomedical-signal-forensics-lab: a reliability framework for wearable-derived digital biomarkers, with real-data validation on WESAD'
tags:
  - Python
  - wearable computing
  - digital biomarkers
  - signal quality
  - reliability
  - reproducibility
  - causal inference
  - fairness audit
authors:
  - name: Ceyhun Olcan
    orcid: 0000-0002-6326-6071
    affiliation: 1
affiliations:
 - name: Center for Technology and Behavioral Health, Geisel School of Medicine at Dartmouth, Lebanon, NH 03766, USA
   index: 1
date: 21 May 2026
bibliography: paper.bib
---

# Summary

Wearable physiological measurements (heart rate, HRV, PPG, sleep stages, step counts) are increasingly used as training targets and outcomes in machine-learning pipelines. The numbers feeding those pipelines are already model outputs of the device: optical sensing, motion correction, manufacturer-specific filtering, and a peak detector have all run before any researcher sees the value. Pooled signal-quality summaries treat the device as a single instrument, but the same device on the same person can be reliable at rest and substantially biased during motion, and a held-out test set dominated by quiet conditions will not surface either failure.

`biomedical-signal-forensics-lab` is a Python toolkit that runs a structured audit on wearable-derived signals before they enter downstream modeling. It combines five window-level artifact detectors, four participant-level reliability primitives, a doubly-robust causal-adjusted confounding analysis under a user-supplied DAG [@robins1994], change-point detection for firmware-drift surveillance, and a stratified fairness audit with cluster-bootstrap confidence intervals, all rolled up into a six-component Digital Biomarker Trust Score (DBTS) with documented YAML-configurable weights. It compares the in-house signal-quality index head-to-head against two published baselines (Orphanidou 2015 [@orphanidou2015]; Sukor 2011 [@sukor2011]) and reports the agreement. A markdown report and a set of publication-style figures are produced automatically.

The toolkit ships with a 300-participant, 60-day synthetic cohort containing five injected failure modes (state-dependent missingness, heat-coupled HRV, motion-coupled PPG noise, three device families with documented biases, and a skin-tone proxy that depresses PPG SQI). A cross-cohort parameter sweep across five generative regimes confirms that the audit responds in the predicted direction (7 of 8 qualitative predictions pass), addressing the obvious concern that detectors tuned on synthetic data might trivially recover their own training signal.

We further validated the toolkit on real data from the public WESAD dataset [@schmidt2018]. Across 850 5-second windows from 2 of the 15 available subjects, the audit surfaced a Bland-Altman bias of +12.8 bpm between wrist Empatica E4 PPG and chest RespiBAN ECG with 95% limits of agreement spanning 58 bpm, identified that the in-house SQI threshold tuned on synthetic data (0.70) produces Cohen's κ = 0.000 against both published baselines on real wrist PPG, and recalibrated the threshold to 0.99 to recover held-out κ = +0.217. The framework's per-window motion artifact score predicted cross-modality HR disagreement on real data (Spearman ρ = +0.30). The two published baselines agreed with each other (κ = +0.31) but neither agreed with the synthetic-tuned in-house SQI on real data, identifying the in-house SQI as the outlier rather than the published baselines. A 10-section deep writeup of the real-data pilot is in `paper/real_data_pilot.md`, and the journal-format long manuscript is in `paper/manuscript.md`.

# Statement of need

Most published wearable-AI work reports a single aggregate signal-quality number per device or per study and proceeds as if that number were a property of the device. It is not. The wearable-quality literature contains good per-window methods [@orphanidou2015; @clifford2012; @sukor2011], good missingness-as-information methods [@perraudin2021], good causal-inference methods [@robins1994], and good reliability methods [@bland1986; @shrout1979], but no widely-used pipeline that combines them into a single audit with both synthetic and real-data validation. Researchers end up writing their own one-off quality filters per project, which produces inconsistent and often incomparable results across papers.

`biomedical-signal-forensics-lab` fills that gap by combining the components into a single auditable layer that sits before downstream modeling. The trust-score weights and category thresholds are exposed in a YAML config rather than hard-coded in source, the AIPW estimator runs alongside the screening correlation so adjusted and unadjusted effects can be reported together, every figure in the auto-generated report is reproducible from the bundled synthetic cohort with a fixed seed, and the same code runs end-to-end on real WESAD data through a documented adapter (`src/data/wesad_adapter.py`).

The target users are research groups building digital biomarkers from wearable data who need a defensible methodological foundation that does not depend on a specific device, a specific manufacturer SDK, or a specific outcome. The framework is non-clinical: it produces signal-quality estimates and methodological recommendations, not diagnoses.

# Features

- **Synthetic data generator** with state-dependent missingness, heat- and AQI-coupled physiology, motion-coupled PPG noise, three device families, and a skin-tone proxy. Generative coefficients are exposed at module level for reproducible perturbation studies.
- **Window-level artifact detection** for motion, sensor dropout, noise spikes, flatlines, and timestamp irregularity, each with a `[0, 1]` severity score and a boolean flag.
- **Reliability layer** with bootstrap week-pair test-retest correlations and cluster bootstrap CIs, ICC(2,1) with an empirical defense against the proper week-pair correlation, rolling coefficient of variation, drift slope via linear regression with NaN handling, and a normalized device-bias estimator.
- **Causal-adjusted confounding analysis** with both screening Pearson correlations and a doubly-robust AIPW estimator that supports user-supplied DAGs (with back-door identification and cycle detection) and cluster-bootstrap CIs.
- **Change-point detection** for firmware-drift surveillance, with both online BOCPD and offline binary segmentation implementations.
- **Stratified fairness audit** over any categorical column (device, skin-tone proxy, sex, age band) with per-component disparity tables, cluster-bootstrap CIs, and forest plots.
- **Digital Biomarker Trust Score (DBTS)** combining six components into a single composite, with weights learnable from data against a user-defined downstream reproducibility task.
- **Three published baselines for comparison.** In-house SQI, Orphanidou (2015), and Sukor (2011) run side by side on every audit, with agreement metrics (Spearman ρ, Cohen's κ, full 2×2 crosstab) in the auto-generated report.
- **Real-data adapters** with three reference implementations (Fitbit-like, Empatica-like, generic daily summary) plus a documented WESAD adapter, plus a detector-recalibration helper that tunes thresholds against either Orphanidou, Sukor, or hand-labeled artifact data using a held-out evaluation split.
- **Cross-cohort generalization sweep** that runs the audit on five synthetic regimes (default, strong environment, inverted skin tone, severe device bias, clean world) and verifies 8 qualitative predictions about how the framework should respond.
- **FastAPI service**, **Streamlit dashboard**, and **markdown report generator** for programmatic and visual inspection.

# Reproducibility

All figures, tables, and statistics in the bundled documentation are reproduced by five scripts run in order: `run_pipeline.py`, `run_signal_audit.py`, `train_quality_model.py`, `generate_report.py`, and the optional `run_cross_cohort_check.py`. End-to-end runtime is under three minutes on a modern laptop CPU. Seeds are fixed in `configs/default.yaml`. The test suite contains 188 tests across 5 bug-audit rounds, covering the synthetic generator, signal processing primitives, artifact detectors, reliability metrics, the trust score under edge cases (empty cohorts, all-NaN columns, single-device cohorts, multi-level categorical treatments), three SQI baselines, the AIPW estimator, the cross-cohort sweep, the WESAD adapter on a synthetic fixture, and the deep real-data analysis pipeline.

The WESAD pilot is reproduced by two additional scripts run on a downloaded WESAD copy: `run_real_data_pilot.py --dataset wesad --path /path/to/wesad` followed by `run_deep_real_analysis.py --path /path/to/wesad`. Wall clock for the 2-subject pilot is ~25 seconds; the full 15-subject run is ~3 minutes. Every number in `paper/real_data_pilot.md` has a CSV in `results/real_data/wesad/` or `results/real_data/wesad_deep/`.

# Limitations

Detector thresholds were tuned on the synthetic generator. The real-data pilot demonstrates they do not transfer to wrist PPG without recalibration, and the framework supports recalibration as a pipeline operation. Anyone deploying on a new device should recalibrate against either Orphanidou, Sukor, or hand-labeled windows.

WESAD provides a single ~100-minute session per subject and no demographic variables relevant to fairness audits. Test-retest reliability, weekly drift, missingness dynamics, and longitudinal device-bias analyses cannot be validated on WESAD. They are validated on the synthetic cohort, where ground truth is controlled. Real-data validation of those analyses requires a longitudinal dataset such as AppleWatch-MIMIC or All of Us. The framework does not produce clinical labels and is not a medical device.

# Acknowledgements

The author thanks the maintainers of the WESAD dataset (Schmidt et al. 2018) for releasing the chest-ECG and wrist-PPG data on which this toolkit was validated. The signal-quality auditing pipeline reuses and extends the published methodologies of Orphanidou et al. (2015), Sukor et al. (2011), and Elgendi (2016).

# References
