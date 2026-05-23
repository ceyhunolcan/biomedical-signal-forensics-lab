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

# Features

- **Four-way signal-quality audit** running the in-house threshold-based estimator alongside Orphanidou 2015, Sukor 2011, and Elgendi 2016 on every window. Pairwise agreement metrics (Spearman rho, Cohen's kappa, full crosstabs) appear in the auto-generated report.
- **Algorithmic-fairness audit** over any categorical column (device family, skin-tone proxy, sex, age band) with per-component disparity tables, cluster-bootstrap confidence intervals, and forest plots.
- **Causal-adjusted confounding analysis** with both screening Pearson correlations and doubly-robust AIPW estimation supporting user-supplied DAGs (back-door identification and cycle detection), plus E-values for unmeasured-confounding sensitivity.
- **Reliability primitives** including ICC(2,1) with an empirical defense against the week-pair correlation, bootstrap test-retest with cluster bootstrap CIs, rolling coefficient of variation, drift slope via linear regression with NaN handling, and a normalized device-bias estimator.
- **Downstream-task impact** measured as the change in leave-one-subject-out AUROC of a heart-rate-variability stress classifier before and after the audit pipeline, plus paired window-level Wilcoxon tests.
- **Change-point surveillance** for firmware-drift detection with online BOCPD and offline binary segmentation implementations.
- **Digital Biomarker Trust Score** combining six components into a composite, with weights learnable from data against a user-defined downstream reproducibility task.
- **Synthetic data generator** with state-dependent missingness, heat- and AQI-coupled physiology, motion-coupled PPG noise, three device families, and a skin-tone proxy. Generative coefficients are exposed at module level for reproducible perturbation studies.
- **Real-data adapters** for Fitbit-like, Empatica-like, and generic daily-summary schemas, plus a documented WESAD adapter and a detector-recalibration helper that tunes thresholds against Orphanidou, Sukor, Elgendi, or hand-labeled artifact data using held-out evaluation splits.
- **FastAPI service**, **Streamlit dashboard**, and **markdown report generator** for programmatic and visual inspection.

# Reproducibility

All figures, tables, and statistics in the documentation are reproducible from five scripts run in order: `run_pipeline.py`, `run_signal_audit.py`, `train_quality_model.py`, `generate_report.py`, and `run_cross_cohort_check.py`. End-to-end runtime is under three minutes on a modern laptop CPU. Seeds are fixed in `configs/default.yaml`. The test suite contains 235 tests, organised across five bug-audit rounds and covering the synthetic generator, signal-processing primitives, artifact detectors, reliability metrics, the trust score under edge cases (empty cohorts, all-NaN columns, single-device cohorts, multi-level categorical treatments), the four SQI baselines, the AIPW estimator, the cross-cohort sweep, the WESAD adapter on a synthetic fixture, and the deep real-data analysis pipeline. Continuous integration runs the matrix on Python 3.11 and 3.12.

The WESAD validation is reproduced by `python scripts/run_deep_real_analysis.py --path /path/to/WESAD`. Wall clock is approximately three minutes for the full 15-subject run. Every number reported above has a corresponding row in `results/real_data/wesad_deep/window_table.csv` (n = 6,585) and an entry in `results/real_data/wesad_deep/summary.json`.

# Limitations

Detector thresholds were tuned on the synthetic generator. The WESAD validation demonstrates that they do not transfer to wrist PPG without recalibration. The framework supports recalibration as a pipeline operation; anyone deploying on a new device should recalibrate against Orphanidou, Sukor, Elgendi, or hand-labeled windows before drawing conclusions.

WESAD provides a single ~100-minute session per subject and no demographic variables relevant to fairness audits. Test-retest reliability, weekly drift, missingness dynamics, and longitudinal device-bias analyses cannot be validated on WESAD. They are validated on the synthetic cohort, where ground truth is controlled. External replication on a longitudinal real-world dataset such as the AppleWatch-MIMIC linkage or All of Us is in scope for future work.

The downstream effect of the audit at n = 15 (delta AUROC = +0.019, delta kappa = 0.000) is small. A larger external cohort is needed to determine whether the framework produces clinically meaningful improvements on stress detection or any other downstream task. The framework does not produce clinical labels and is not a medical device.

# Acknowledgements

The author thanks the maintainers of the WESAD dataset [@schmidt2018] for releasing the chest-ECG and wrist-PPG data on which this toolkit was validated. The signal-quality auditing pipeline reuses and extends published methodologies of Orphanidou et al. [@orphanidou2015], Sukor et al. [@sukor2011], and Elgendi [@elgendi2016]. Causal-inference methodology follows Robins et al. [@robins1994] and VanderWeele and Ding [@vanderweele2017]. Bland-Altman analysis follows Bland and Altman [@bland1986]; intraclass-correlation methodology follows Shrout and Fleiss [@shrout1979].

# References
