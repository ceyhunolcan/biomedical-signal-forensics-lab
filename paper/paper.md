---
title: 'biomedical-signal-forensics-lab: an open-source toolkit for auditing wearable physiological signal pipelines'
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
date: 23 May 2026
bibliography: paper.bib
---

# Summary

Wearable physiological signals (heart rate, heart-rate variability, photoplethysmography, step counts, sleep stages) are increasingly used as training targets and outcomes in digital-health machine-learning pipelines. Each number a researcher receives is already a model output of the device: optical sensing, motion correction, manufacturer filtering, and a peak detector have all run before any value is stored. Pooled signal-quality summaries treat the device as a single instrument, but the same device on the same person can be reliable at rest and substantially biased during motion. A held-out test set dominated by quiet conditions surfaces neither problem.

`biomedical-signal-forensics-lab` is a Python toolkit that audits wearable-derived signals before they enter downstream modeling. It runs four published signal-quality indices side by side (an in-house threshold-based estimator, Orphanidou 2015 [@orphanidou2015], Sukor 2011 [@sukor2011], and Elgendi 2016 [@elgendi2016]); performs doubly-robust causal-adjusted confounding analysis under a user-supplied directed acyclic graph [@robins1994] with E-values for unmeasured-confounding sensitivity [@vanderweele2017]; runs a stratified algorithmic-fairness audit with cluster-bootstrap confidence intervals; monitors firmware drift via online and offline change-point detection; and quantifies the downstream effect of the audit on a leave-one-subject-out stress classifier. Results roll up into a methodology-recommendations layer that flags causally fragile estimates, downstream-detrimental quality filters, and stratum-specific disparities.

We validated the toolkit on the public WESAD dataset [@schmidt2018]. Across 6,585 thirty-second windows from all 15 subjects, the audit surfaced a Bland-Altman bias of +3.57 bpm between wrist PPG and chest ECG heart rate (95% limits of agreement [-23.14, +30.28]; mean absolute error 9.66 bpm; Pearson r = +0.70), found that three independent published baselines collectively reject 44.6% of windows that the in-house threshold-based pipeline passes (median pairwise Cohen's kappa = -0.20), and measured a small but statistically detectable effect of the audit pipeline on stress-classification leave-one-subject-out AUROC (0.804 to 0.823, delta = +0.019; Wilcoxon signed-rank p = 1.5e-4 on paired window scores). Recalibrating the in-house threshold against the published baselines produces zero change in held-out kappa (delta kappa = 0.000), supporting the claim that quality filtering alone is insufficient at this sample size.

# Statement of need

The wearable-quality literature contains good per-window methods [@orphanidou2015; @clifford2012; @sukor2011; @elgendi2016], good missingness-as-information methods [@perraudin2021], good causal-inference methods [@robins1994; @vanderweele2017], and good reliability methods [@bland1986; @shrout1979]. No widely-used open-source pipeline combines them into a single audit that runs end-to-end on raw wearable signals and produces reporting-standards-compliant supplementary materials. Researchers end up writing one-off quality filters per project, producing inconsistent and often incomparable results across papers.

`biomedical-signal-forensics-lab` fills that gap by combining the components into a single auditable layer that sits before downstream modeling. Trust-score weights and category thresholds are exposed in YAML configuration rather than hard-coded. The doubly-robust AIPW estimator runs alongside the screening Pearson correlation so adjusted and unadjusted effects can be reported together. Every figure in the auto-generated report is reproducible from the bundled synthetic cohort with a fixed seed, and the same code runs end-to-end on real WESAD data through a documented adapter (`biomedical_signal_forensics_lab.data.wesad_adapter`).

Target users are research groups building digital biomarkers from wearable data who need a defensible methodological foundation that does not depend on a specific device, manufacturer SDK, or outcome. The framework is non-clinical: it produces signal-quality estimates and methodological recommendations, not diagnoses.

# State of the field

Several mature open-source Python packages cover parts of the wearable-signal analysis stack. NeuroKit2 [@makowski2021] provides signal-processing primitives and quality metrics across modalities (ECG, PPG, EDA, respiration). HeartPy [@vangent2019] focuses on heart-rate variability extraction from PPG. The hrv-analysis package offers time- and frequency-domain HRV measures with strong test coverage. BioSPPy [@carreiras2015] provides classical preprocessing and feature extraction for biosignals.

None of these libraries combine multi-baseline signal-quality auditing, algorithmic-fairness analysis, doubly-robust causal-adjusted confounding, and downstream-task impact measurement in a single end-to-end pipeline. They are excellent building blocks for primitives, and `biomedical-signal-forensics-lab` consumes their outputs where applicable. The four-way signal-quality comparison (in-house, Orphanidou, Sukor, Elgendi) is implemented directly because no existing package runs all three published baselines head-to-head against a custom estimator and reports agreement statistics with cluster-bootstrap confidence intervals.

The following two tables make the positioning concrete. Table 1 covers the audit layer that defines this toolkit's contribution; Table 2 covers the upstream primitives where existing libraries are strong and this toolkit relies on them rather than duplicating their functionality.

Table 1. Audit-layer capability comparison.

| Capability | bsf-lab | NeuroKit2 | HeartPy | hrv-analysis | BioSPPy |
|---|:---:|:---:|:---:|:---:|:---:|
| Multi-baseline SQI comparison | yes | no | no | no | no |
| Pairwise SQI agreement metrics (kappa, rho) | yes | no | no | no | no |
| Algorithmic-fairness audit | yes | no | no | no | no |
| Doubly-robust causal-adjusted estimation (AIPW) | yes | no | no | no | no |
| E-value confounding sensitivity | yes | no | no | no | no |
| Change-point detection | yes | no | no | no | no |
| LOSO downstream-task impact | yes | no | no | no | no |
| Cluster-bootstrap confidence intervals | yes | no | no | no | no |
| ICC(2,1) reliability primitives | yes | partial | no | no | no |
| YAML-configurable thresholds | yes | no | no | no | no |
| Multi-device real-data adapters | yes | partial | no | no | no |
| TRIPOD+AI and STARD 2015 checklists | yes | no | no | no | no |

Table 2. Primitives comparison.

| Primitive | bsf-lab | NeuroKit2 | HeartPy | hrv-analysis | BioSPPy |
|---|:---:|:---:|:---:|:---:|:---:|
| PPG quality estimation | 4 methods | 1 method | 1 method | no | basic |
| Multi-modal signals (ECG, PPG, EDA, EMG, RSP) | PPG and ECG | broad coverage | PPG only | HRV only | broad coverage |
| HRV time/frequency/nonlinear features | partial | yes | yes | yes | partial |
| Built-in peak detectors | partial | yes | yes | no | yes |
| Streaming / real-time processing | no | partial | yes | no | no |

The statistical methodology integrated by this package, including Bland-Altman limits of agreement [@bland1986], intraclass correlation [@shrout1979], doubly-robust treatment-effect estimation [@robins1994], and E-value sensitivity analysis [@vanderweele2017], exists in general-purpose packages such as statsmodels, scikit-learn, and scipy. The contribution of `biomedical-signal-forensics-lab` is the integration of these methods with the wearable-signal preprocessing stack and the wrapping of them into a single pipeline whose outputs feed a methodology-recommendations layer.

# Software design

The toolkit is organised as a modular pipeline that consumes raw or device-summary wearable data and produces auditable artifacts at four layers: signal-quality (windowed indices and pairwise agreement), reliability (per-subject test-retest and drift estimates), causal (DAG-based AIPW adjustment with E-values), and downstream (leave-one-subject-out classifier impact). Each layer exposes a documented Python API and writes a JSON summary alongside intermediate CSVs, so downstream consumers can use either the programmatic interface or the on-disk artifacts.

Three design choices deserve note. First, signal-quality thresholds and trust-score weights are exposed in YAML configuration rather than hard-coded in source, so recalibration against a new device or population is a one-file change rather than a code edit. Second, an adapter pattern decouples dataset-specific I/O from the audit logic; the WESAD adapter (`biomedical_signal_forensics_lab.data.wesad_adapter`) is one of three reference implementations alongside Fitbit-like and Empatica-like adapters, and adding a new dataset is a single class that returns windowed signals. Third, the doubly-robust AIPW estimator runs alongside the screening Pearson correlation rather than replacing it, so unadjusted and adjusted effects are reported together; this surfaces causal fragility (a sign flip after back-door adjustment) rather than hiding it.

Package functionality is organised around the four audit layers. The signal-quality audit runs the in-house threshold-based estimator alongside Orphanidou 2015, Sukor 2011, and Elgendi 2016 on every window, with pairwise agreement (Spearman rho, Cohen's kappa, full crosstabs) in the report. The algorithmic-fairness audit operates over any categorical column (device family, skin-tone proxy, sex, age band) with per-component disparity tables, cluster-bootstrap confidence intervals, and forest plots. The causal-adjusted confounding analysis exposes both screening Pearson correlations and AIPW estimation with user-supplied DAGs (back-door identification, cycle detection), plus E-values for unmeasured-confounding sensitivity. Reliability primitives include ICC(2,1) with an empirical defense against the week-pair correlation, bootstrap test-retest with cluster bootstrap CIs, rolling coefficient of variation, drift slope via linear regression with NaN handling, and a normalized device-bias estimator. The downstream-task impact module measures change in leave-one-subject-out AUROC of a heart-rate-variability stress classifier before and after the audit pipeline, plus paired window-level Wilcoxon tests. Change-point surveillance for firmware drift is provided through online BOCPD and offline binary segmentation. A Digital Biomarker Trust Score combines six components into a composite with weights learnable from data against a user-defined downstream reproducibility task. The package also ships a synthetic data generator, real-data adapters, a detector-recalibration helper, a FastAPI service, a Streamlit dashboard, and a markdown report generator.

# Reproducibility

All figures, tables, and statistics in the documentation are reproducible from five scripts run in order: `run_pipeline.py`, `run_signal_audit.py`, `train_quality_model.py`, `generate_report.py`, and `run_cross_cohort_check.py`. End-to-end runtime is under three minutes on a modern laptop CPU. Seeds are fixed in `configs/default.yaml`. The test suite contains 235 tests, organised across five bug-audit rounds and covering the synthetic generator, signal-processing primitives, artifact detectors, reliability metrics, the trust score under edge cases (empty cohorts, all-NaN columns, single-device cohorts, multi-level categorical treatments), the four SQI baselines, the AIPW estimator, the cross-cohort sweep, the WESAD adapter on a synthetic fixture, and the deep real-data analysis pipeline. Continuous integration runs the matrix on Python 3.11 and 3.12.

The WESAD validation is reproduced by `python scripts/run_deep_real_analysis.py --path /path/to/WESAD`. Wall clock is approximately three minutes for the full 15-subject run. Every number reported above has a corresponding row in `results/real_data/wesad_deep/window_table.csv` (n = 6,585) and an entry in `results/real_data/wesad_deep/summary.json`.

# Research impact statement

This software was developed at the Center for Technology and Behavioral Health at the Geisel School of Medicine at Dartmouth as part of methodological work on wearable-derived digital biomarkers. At the time of submission the package is in early-stage public release (PyPI v0.16.2, archived to Zenodo at doi.org/10.5281/zenodo.20349806). Near-term significance is supported by three reproducible elements that reviewers and prospective users can verify directly: the WESAD validation summarised above, with per-window data in `results/real_data/wesad_deep/window_table.csv`; the cross-cohort generalization sweep across five synthetic regimes, with seven of eight qualitative predictions matching predicted directions; and per-item compliance documentation against the TRIPOD+AI [@collins2024] and STARD 2015 [@bossuyt2015] reporting standards in `paper/checklists/`.

Prospective users are research groups building digital biomarkers from consumer-grade wearables who need a defensible methodological foundation before downstream modeling. Independent replication on a longitudinal dataset such as AppleWatch-MIMIC or All of Us would strengthen the test-retest and weekly-drift analyses, which are currently validated only on the synthetic generator; this is in scope for a follow-up real-data study.

# Limitations

Detector thresholds were tuned on the synthetic generator. The WESAD validation demonstrates that they do not transfer to wrist PPG without recalibration. The framework supports recalibration as a pipeline operation; anyone deploying on a new device should recalibrate against Orphanidou, Sukor, Elgendi, or hand-labeled windows before drawing conclusions.

WESAD provides a single ~100-minute session per subject and no demographic variables relevant to fairness audits. Test-retest reliability, weekly drift, missingness dynamics, and longitudinal device-bias analyses cannot be validated on WESAD. They are validated on the synthetic cohort, where ground truth is controlled. External replication on a longitudinal real-world dataset such as the AppleWatch-MIMIC linkage or All of Us is in scope for future work.

The downstream effect of the audit at n = 15 (delta AUROC = +0.019, delta kappa = 0.000) is small. A larger external cohort is needed to determine whether the framework produces clinically meaningful improvements on stress detection or any other downstream task. The framework does not produce clinical labels and is not a medical device.

# AI usage disclosure

Generative AI assistants were used during development for code drafting and manuscript editing; all outputs were reviewed and validated by the author, who made all design decisions.

# Acknowledgements

The author thanks the maintainers of the WESAD dataset [@schmidt2018] for releasing the chest-ECG and wrist-PPG data on which this toolkit was validated. The signal-quality auditing pipeline reuses and extends published methodologies of Orphanidou et al. [@orphanidou2015], Sukor et al. [@sukor2011], and Elgendi [@elgendi2016]. Causal-inference methodology follows Robins et al. [@robins1994] and VanderWeele and Ding [@vanderweele2017]. Bland-Altman analysis follows Bland and Altman [@bland1986]; intraclass-correlation methodology follows Shrout and Fleiss [@shrout1979]. The toolkit composes with the NeuroKit2 [@makowski2021], HeartPy [@vangent2019], and BioSPPy [@carreiras2015] ecosystems for signal-processing primitives.

# References
