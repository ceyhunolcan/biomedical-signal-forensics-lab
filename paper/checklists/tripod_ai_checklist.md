# TRIPOD+AI compliance checklist

**Reference**: Collins GS, Moons KGM, Dhiman P, et al. *TRIPOD+AI statement:
updated guidance for reporting clinical prediction models that use regression
or machine learning methods.* BMJ 2024;385:e078378.
doi:10.1136/bmj-2023-078378

**Applicability to this paper**: TRIPOD+AI applies to the Section 4.6
downstream-audit classifier (LF/HF biomarker -> baseline/stress label, LOSO
cross-validation). It does not apply to the SQI-agreement analysis in
Sections 4.1-4.3, which is framed as a diagnostic-accuracy comparison (see
STARD 2015 checklist) rather than a prediction-model deployment. The
downstream classifier in Section 4.6 is a research-stage demonstration, not a
clinical-deployment candidate; the items below reflect that scope honestly.

Item numbering follows the published TRIPOD+AI checklist. Item statements are
paraphrased; the full text of each item is in the original publication.

---

## Title and abstract

**Item 1 (Title).** Identifies the study as developing or validating a
prediction model, mentions the target population, the outcome, and the AI
methods used.

- *This paper.* The main title positions the work as a "methodology audit of
  wearable physiological signals," not as a prediction-model paper.
  Section 4.6 (the downstream audit) is a sub-study; its sub-heading
  identifies it as a classifier evaluation. The full title is appropriate
  for the methodology audit as a whole.

**Item 2 (Abstract).** Structured abstract reporting objectives, methods,
results, conclusions.

- *This paper.* Manuscript abstract is structured. Section 4.6 results
  (AUROC 0.804 -> 0.823, Wilcoxon p = 1.5e-4) are reported in the abstract.

## Introduction

**Item 3a (Background and rationale).** Explains the medical context and the
need for a prediction model.

- *This paper.* Section 1 motivates the audit; Section 4.6 motivates the
  downstream classifier as a check on whether the SQI-binarisation choice
  has measurable consequences for a downstream prediction task.

**Item 3b (Objectives).** States objectives, including whether the study
develops, validates, or updates a model.

- *This paper.* Section 4.6 develops a per-subject LF/HF classifier and
  evaluates it under two SQI preprocessing regimes (raw vs in-house cleaned).
  Objective is to test whether SQI choice changes downstream performance.

## Methods

**Item 4a (Source of data).** Describes the data source, including dates,
geographic location, setting.

- *This paper.* WESAD (Schmidt et al. 2018), released 2018, lab-based
  acquisition at the University of Siegen. Section 3.1 (Data).

**Item 4b (Eligibility criteria).** Describes participant eligibility.

- *This paper.* All 15 WESAD subjects with successful chest-ECG and wrist-PPG
  synchronisation included. No additional eligibility filter applied. Stated
  in Section 3.1.

**Item 5a (Setting).** Geographic and temporal setting.

- *This paper.* Lab-based, single-site, 2018. Stated in Section 3.1.

**Item 5b (Outcome).** Definition of the outcome being predicted, including
how and when it was measured.

- *This paper.* Outcome is the binary label baseline vs stress, defined by
  the WESAD protocol annotations. Section 4.6.

**Item 6 (Predictors).** Predictors used, including how and when measured.

- *This paper.* Single predictor: per-subject LF/HF ratio computed on RR
  intervals derived from chest ECG. Section 4.6.

**Item 7 (Sample size).** Sample size justification.

- *This paper.* n=15 subjects, dictated by WESAD. Section 4.6 explicitly
  states this is not powered as a confirmatory study; it is a research-stage
  demonstration. Section 6 (Limitations) acknowledges the small n.

**Item 8 (Missing data).** Handling of missing data.

- *This paper.* No subject-level missingness; all 15 subjects contributed one
  baseline and one stress LF/HF measurement. Stated in Section 4.6.

**Item 9 (Statistical analysis).** Statistical methods used.

- *This paper.* LOSO cross-validation (15 folds, each with 14 train + 1
  test); per-fold AUROC; paired Wilcoxon signed-rank test comparing per-fold
  AUROC under the two preprocessing regimes; bootstrap confidence intervals.
  Section 4.6.

**Item 10a (Model development).** Predictors selected, methods for model
specification.

- *This paper.* Single-predictor logistic regression. No predictor selection
  required. Section 4.6.

**Item 10b (Model specification).** Final model specification.

- *This paper.* Logistic regression with one continuous predictor (LF/HF
  ratio). Coefficients reported in supplement.

**Item 10c (Model performance).** Discrimination, calibration, etc.

- *This paper.* AUROC reported (mean and per-fold). Calibration not reported
  because the analysis focus is on relative performance between two
  preprocessing regimes, not on calibration of the classifier itself. This
  is stated as a limitation.

**Item 10d (Internal validation).** Description of internal validation.

- *This paper.* LOSO is the internal validation strategy. Section 4.6.

## AI-specific items

**Item AI-1 (Software/version).** Software and version used.

- *This paper.* Python 3.10/3.11/3.12, scikit-learn pinned in
  `pyproject.toml`. CI matrix tests all three Python versions.

**Item AI-2 (Reproducibility).** Code and data availability.

- *This paper.* All code public at
  https://github.com/ceyhunolcan/biomedical-signal-forensics-lab under MIT.
  WESAD is public via the original release. Section 7 (Reproducibility).

**Item AI-3 (Computational resources).** Computational requirements.

- *This paper.* The full pipeline runs on a laptop in under 10 minutes; no
  GPU required. Stated in repository README.

**Item AI-4 (Fairness and bias).** Considerations of fairness and bias.

- *This paper.* The synthetic cohort (Sections 3-4.5) was constructed
  specifically to inject and recover fairness disparities including
  device-family and skin-tone. WESAD itself is not demographically diverse
  (15 subjects, demographics not stratified); this limitation is stated in
  Section 6.

## Results

**Item 11 (Risk groups).** If applicable, definition of risk groups.

- *This paper.* Not applicable (binary classification, no stratified risk
  groups).

**Item 12 (Development vs validation).** Numbers in each set.

- *This paper.* LOSO: every subject contributes both as training (in 14
  folds) and as test (in 1 fold).

**Item 13a (Participants).** Flow of participants through the study.

- *This paper.* See Figure 1 flow diagram.

**Item 13b (Performance).** Model performance with confidence intervals.

- *This paper.* AUROC 0.804 (95% CI from bootstrap) under raw preprocessing;
  0.823 under cleaned preprocessing; paired Wilcoxon p = 1.5e-4 (n=15).
  Section 4.6.

**Item 14a (Final model).** Specification of the final model.

- *This paper.* Final model is the logistic regression with LF/HF as
  predictor; coefficients in supplement.

**Item 14b (Performance interpretation).**

- *This paper.* Section 4.6 explicitly notes the AUROC difference is small
  (0.019) but consistently in the same direction across all 15 subjects,
  hence the strong Wilcoxon p-value despite small absolute effect.

## Discussion

**Item 15 (Interpretation).** Overall interpretation including comparison
with other models.

- *This paper.* Section 5 interprets the downstream result within the
  broader audit framing. No comparison with other published classifiers is
  attempted because the contribution is the audit, not the classifier.

**Item 16 (Limitations).** Study limitations.

- *This paper.* Section 6 enumerates: small n; single-site dataset; single
  predictor; absence of external validation; no calibration analysis.

**Item 17 (Implications).** Implications for clinical practice and future
research.

- *This paper.* Section 5 states the downstream result is a research-stage
  signal that the SQI-binarisation choice has measurable downstream effect,
  not a deployment claim.

## Other information

**Item 18 (Data sharing).** Statement on data sharing.

- *This paper.* WESAD is public. All derived artefacts (window tables,
  summary JSONs) are in the repository under
  `results/real_data/wesad_deep/`.

**Item 19 (Funding).** Funding statement.

- *This paper.* No external funding; self-supported research. To be stated
  in the author affiliation block once finalised.

---

## Summary of compliance

| Category | Items | Compliance |
|---|---:|---|
| Title and abstract | 2 | Compliant |
| Introduction | 2 | Compliant |
| Methods | 11 | Compliant (calibration analysis is missing, acknowledged in Section 6) |
| Results | 5 | Compliant |
| Discussion | 3 | Compliant |
| Other | 2 | Compliant once author block is finalised |

**Items not addressed**: TRIPOD+AI item 10c calibration analysis. The
analysis focus is on relative performance between preprocessing regimes
rather than on absolute calibration of the downstream classifier. This is an
acknowledged limitation rather than a TRIPOD+AI violation: calibration is
out of scope for the audit framing of Section 4.6. A future deployment-style
study should add reliability diagrams and a Hosmer-Lemeshow or
Spiegelhalter test before clinical use is considered.

**Items to address before submission**: item 19 (author block / funding
statement). Tracked in the npj DM polish queue.
