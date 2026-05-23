# FUTURE-AI compliance documentation

This document maps `biomedical-signal-forensics-lab` against the six FUTURE-AI principles for trustworthy AI in healthcare (Lekadir et al. 2025, *BMJ*). Each section gives an honest assessment of where the toolkit is strong, where coverage is partial, and what remains for future work.

The toolkit is a non-clinical research prototype. It produces signal-quality estimates and methodology recommendations, not diagnoses. FUTURE-AI was designed for clinical AI; the same trustworthy-AI principles apply here because the toolkit feeds downstream clinical-AI research.

## F: Fairness

**Definition.** Performance should be similar across individuals with similar characteristics regardless of sensitive attributes (sex, race, skin tone, age, device family).

**Status: partial.**

**Strengths:**

- Stratified algorithmic-fairness audit module over any categorical column (device family, skin-tone proxy, sex, age band)
- Per-component disparity tables with cluster-bootstrap 95% confidence intervals
- Forest plots for visual comparison across strata
- Synthetic cohort includes a skin-tone proxy that depresses PPG SQI by construction, allowing the audit to be exercised on data with controlled disparities

**Gaps:**

- WESAD does not provide demographic variables relevant to fairness audits, so empirical fairness performance on real data is currently demonstrated only on the synthetic cohort
- Skin-tone effects on PPG, well-documented in the dermatology and pulse-oximetry literature, cannot be directly evaluated on WESAD
- A diverse real-world cohort such as All of Us or AppleWatch-MIMIC is needed for empirical fairness validation

## U: Universality

**Definition.** The tool should generalise beyond the data on which it was developed.

**Status: partial.**

**Strengths:**

- Three reference data adapters (Fitbit-like, Empatica-like, WESAD) with documented column expectations
- Cross-cohort generalization sweep across five synthetic regimes (default, strong environment, inverted skin tone, severe device bias, clean world), with 7 of 8 qualitative predictions matching expected directions
- YAML-configurable thresholds and trust-score weights, so site-specific recalibration is a config edit rather than a code change
- Detector-recalibration helper for tuning thresholds against Orphanidou, Sukor, Elgendi, or hand-labeled artifact data using held-out evaluation splits

**Gaps:**

- Real-data validation is currently single-dataset (WESAD only)
- Multi-cohort external validation on AppleWatch-MIMIC, All of Us, or other longitudinal wearable datasets is scoped for future work and not yet completed

## T: Traceability

**Definition.** Development, deployment, and updates should be documented to enable scrutiny.

**Status: strong.**

**Strengths:**

- Full git history from initial commit through present, public on GitHub
- Semantic versioning with PyPI releases (currently v0.16.2)
- Zenodo concept DOI for versioned archival citation (10.5281/zenodo.20349806)
- All figures in the paper reproducible from generator scripts and the WESAD window table CSV
- Auto-generated audit reports include provenance metadata (config hash, code version, dataset path)
- Continuous integration logs preserved on GitHub Actions
- All results in `results/` written to disk as CSV with seed-pinned regeneration

**Gaps:**

- None at this scope. Production deployment in a clinical setting would require additional audit-log infrastructure not covered by the research prototype.

## U: Usability

**Definition.** End users should be able to safely and effectively use the tool.

**Status: strong.**

**Strengths:**

- Documentation site at https://ceyhunolcan.github.io/biomedical-signal-forensics-lab/ with quickstart, methods, results, comparison, reproducing-the-paper, and API reference pages
- Multiple usage modes (Python API, FastAPI service, Streamlit dashboard, markdown report generator) for different research workflows
- 235 passing tests on Python 3.11 and 3.12 give end users confidence in correctness
- CONTRIBUTING.md and CODE_OF_CONDUCT.md present
- "Who should use this" section in the README with explicit good-fit and not-a-fit lists, to set expectations honestly

**Gaps:**

- A worked-example demo notebook is in scope for the next release

## R: Robustness

**Definition.** The tool should be technically sound and reliable.

**Status: strong.**

**Strengths:**

- 235 tests organised across five bug-audit rounds covering the synthetic generator, signal-processing primitives, artifact detectors, reliability metrics, trust score under edge cases (empty cohorts, all-NaN columns, single-device cohorts, multi-level categorical treatments), the four SQI baselines, the AIPW estimator, the cross-cohort sweep, the WESAD adapter on a synthetic fixture, and the deep real-data analysis pipeline
- Test matrix runs on Python 3.11 and 3.12 in CI
- Recalibration helper enables tuning thresholds against published baselines or hand-labeled data using held-out evaluation splits to prevent overfitting
- E-value sensitivity analysis surfaces robustness of causal claims to unmeasured confounding
- Bland-Altman analysis reports both bias and limits of agreement, surfacing variance that point estimates would hide
- Cluster-bootstrap confidence intervals respect within-subject correlation in repeated-measures data

**Gaps:**

- Adversarial robustness (input perturbation) is not currently tested; this is a research-prototype scope choice rather than a planned feature

## E: Explainability

**Definition.** The tool should be explainable to relevant stakeholders.

**Status: partial.**

**Strengths:**

- Causal-adjusted confounding analysis uses user-supplied directed acyclic graphs, making the assumed causal structure explicit and inspectable
- AIPW estimation reports both adjusted and unadjusted effects side by side, surfacing what assumptions are doing
- E-values quantify how much unmeasured confounding would be needed to nullify the observed effect, making sensitivity assumptions concrete
- Per-component disparity tables and forest plots make stratum-specific effects visible rather than hidden in aggregates
- The methodology-recommendations layer outputs explicit, plain-language recommendations rather than opaque scores
- All decision thresholds are exposed in YAML configuration with documented meaning

**Gaps:**

- Model-level interpretability tooling (SHAP, LIME, attention maps) is not currently integrated; the toolkit's audits operate at the pipeline-decision level rather than the model-internals level
- A future release could integrate model-interpretation primitives for the downstream stress classifier

## Summary

| Principle | Status |
|---|---|
| Fairness | partial (capability strong, real-data evaluation pending diverse cohort) |
| Universality | partial (multi-cohort external validation in scope) |
| Traceability | strong |
| Usability | strong |
| Robustness | strong |
| Explainability | partial (decision-level strong, model-level not implemented) |

Three principles are at strong compliance, three at partial. The partial-compliance gaps are data-availability gaps rather than capability gaps: WESAD lacks demographic variables, and second-dataset replication is in scope rather than complete. Addressing both is a multi-week external-validation work stream.

This document will be updated at each major release to reflect changes in status. For the FUTURE-AI framework itself see Lekadir et al. (2025).
