# STARD 2015 compliance checklist

**Reference**: Bossuyt PM, Reitsma JB, Bruns DE, et al. *STARD 2015: an
updated list of essential items for reporting diagnostic accuracy studies.*
BMJ 2015;351:h5527. doi:10.1136/bmj.h5527

**Applicability to this paper**: STARD 2015 applies most directly to Arms
1-3 of Figure 1: HR agreement (Section 4.1), SQI agreement (Section 4.2),
and threshold recalibration (Section 4.3). In all three, chest ECG serves
as the reference standard against which wrist PPG-derived measurements
serve as the index modality. The 30 STARD 2015 items are listed below with
a per-item compliance statement.

The wording of each item is paraphrased from the published checklist;
the original BMJ paper contains the full text.

---

## Title and abstract

**Item 1.** Identification as a study of diagnostic accuracy using at least
one measure of accuracy (sensitivity, specificity, predictive values,
likelihood ratios, area under ROC curve, etc.).

- *This paper.* Section 4.2 reports Cohen's kappa as the primary agreement
  metric between four SQI binarisations on the same 6,585 windows; Section
  4.1 reports Bland-Altman bias and limits of agreement on continuous HR.
  Both are explicit accuracy / agreement measures.

**Item 2.** Structured summary of study design, methods, results, and
conclusions.

- *This paper.* Abstract is structured.

## Introduction

**Item 3.** Scientific and clinical background, including the intended use
and clinical role of the index test.

- *This paper.* Sections 1-2 motivate the audit. The "index modality" (wrist
  PPG) is positioned as a candidate component of consumer-wearable
  physiological monitoring; the comparator (chest ECG) is positioned as the
  established reference. The intended use of the SQI is to flag low-quality
  windows for exclusion before downstream analysis.

**Item 4.** Study objectives and hypotheses.

- *This paper.* Section 1 states three objectives: (a) audit synthetic-tuned
  SQI thresholds on real data, (b) compare multiple published SQI baselines,
  (c) test whether SQI choice has measurable downstream effect.

## Methods

### Study design

**Item 5.** Whether data collection was planned before the index test and
reference standard were performed (prospective) or after (retrospective).

- *This paper.* Retrospective use of the public WESAD dataset. Stated in
  Section 3.1.

### Participants

**Item 6.** Eligibility criteria.

- *This paper.* All 15 subjects in the public WESAD release. Stated in
  Section 3.1. The two subjects (S1, S12) excluded by WESAD authors before
  release are noted in Figure 1.

**Item 7.** On what basis potentially eligible participants were identified.

- *This paper.* WESAD public release; no additional selection step in this
  study.

**Item 8.** Where and when potentially eligible participants were identified
(setting, location and dates).

- *This paper.* WESAD acquisition: lab-based, University of Siegen, 2018.
  This study performed in 2025-2026.

**Item 9.** Whether participants formed a consecutive, random, or convenience
series.

- *This paper.* Convenience series (all available WESAD subjects). Stated in
  Section 3.1.

### Test methods

**Item 10a (Index test).** How and by whom the index test was performed.

- *This paper.* Index modality: wrist Empatica E4 PPG, 64 Hz, automated
  pulse-peak detection and HR computation. Algorithms in
  `src/signals/ppg_processing.py`. Algorithm version pinned by repository
  tag.

**Item 10b (Reference standard).** How and by whom the reference standard was
performed.

- *This paper.* Reference modality: chest RespiBAN ECG, 700 Hz, Pan-Tompkins
  R-peak detection followed by RR interval computation. Algorithms in
  `src/signals/ecg_processing.py`.

**Item 11.** Rationale for choosing the reference standard.

- *This paper.* Chest ECG is the established gold standard for instantaneous
  heart rate and HRV in physiological research (HRV Task Force standards;
  Schaefer and Vagedes 2013). Stated in Section 3.

**Item 12a.** Definition of and rationale for test positivity cutoffs.

- *This paper.* Four SQI binarisations are compared. The in-house cutoff
  (0.70) was inherited from prior synthetic-data tuning. The three
  published cutoffs (Orphanidou, Sukor, Elgendi) follow the published
  recommendations. The lack of agreement among these four constitutes the
  central audit finding (Section 4.2).

**Item 12b.** Whether clinical information and reference standard results
were available to performers of the index test.

- *This paper.* Both modalities are automated; no human reader involved at
  test execution. The SQI computation is blind to the ECG-derived HR by
  construction.

**Item 13a.** Whether clinical information and index test results were
available to assessors of the reference standard.

- *This paper.* Both modalities are automated; not applicable.

**Item 13b.** Definition of test positivity (cutoff) for the reference
standard.

- *This paper.* The "reference HR" is the continuous output of the ECG
  pipeline; there is no positivity cutoff. For Section 4.2, the reference
  comparator is each published SQI baseline's own pass/fail decision.

### Analysis

**Item 14.** Methods for estimating or comparing measures of diagnostic
accuracy.

- *This paper.* Bland-Altman bias and 95% limits of agreement (Section 4.1);
  Cohen's kappa pairwise between four SQI binarisations (Section 4.2);
  fraction of windows on which all three published methods reject
  (Section 4.2); paired Wilcoxon signed-rank for downstream classifier
  comparison (Section 4.6). All methods implemented in
  `src/evaluation/deep_real_analysis.py`.

**Item 15.** How indeterminate index test or reference standard results were
handled.

- *This paper.* Zero indeterminate results in either modality. Reported as
  the "Exclusions during per-window processing: 0" box in Figure 1.

**Item 16.** How missing data on the index test and reference standard were
handled.

- *This paper.* No subject-level missingness; one subject (S12) is missing
  from WESAD itself, not from this study. Reported in Figure 1.

**Item 17.** Any analyses of variability in diagnostic accuracy,
distinguishing pre-specified from exploratory.

- *This paper.* Pre-specified: per-state stratification (baseline vs
  stress vs amusement). Exploratory: per-subject heterogeneity (range
  6.75-26.02 bpm). Stated in Section 4.1 and explicitly flagged as
  exploratory.

**Item 18.** Intended sample size and how it was determined.

- *This paper.* n=15 subjects (all available WESAD subjects); 6,585 windows
  followed mechanically from 5-second non-overlapping segmentation. No
  formal power calculation; this is an exploratory audit. Acknowledged in
  Section 6.

## Results

### Participants

**Item 19.** Flow of participants, using a diagram.

- *This paper.* Figure 1 (this directory's flow diagram).

**Item 20.** Baseline demographic and clinical characteristics.

- *This paper.* WESAD demographics are stated in Schmidt et al. 2018; not
  re-tabulated here. This is a limitation acknowledged in Section 6.

**Item 21a.** Distribution of severity of disease in those with the target
condition.

- *This paper.* Not applicable (no disease target).

**Item 21b.** Distribution of alternative diagnoses in those without the
target condition.

- *This paper.* Not applicable.

**Item 22.** Time interval and any clinical interventions between index test
and reference standard.

- *This paper.* Synchronous acquisition; both modalities recorded
  simultaneously. Stated in Section 3.1.

### Test results

**Item 23.** Cross tabulation of the index test results by the results of
the reference standard.

- *This paper.* Section 4.2 reports the four-way SQI kappa matrix; this is
  the analog of a cross-tabulation for the SQI-as-test framing. The HR
  agreement (Section 4.1) is continuous, so Bland-Altman replaces the
  cross-tabulation.

**Item 24.** Estimates of diagnostic accuracy and their precision (e.g. 95%
confidence intervals).

- *This paper.* Bland-Altman LoA reported with 95% bounds; bootstrap CIs for
  Pearson r. Kappa estimates reported as point estimates; bootstrap CIs not
  yet computed for kappa (acknowledged as a planned addition for next
  revision).

**Item 25.** Any adverse events from performing the index test or the
reference standard.

- *This paper.* Not applicable (non-invasive sensors, retrospective data
  analysis only).

## Discussion

**Item 26.** Study limitations, including sources of potential bias,
statistical uncertainty, and generalisability.

- *This paper.* Section 6 enumerates: single-site dataset, small n,
  lab-controlled (not free-living), absence of demographic stratification
  in WESAD itself, single-vendor wearable (E4), and the in-house SQI was
  tuned on synthetic data rather than held out from real data.

**Item 27.** Implications for practice, including the intended use and
clinical role of the index test.

- *This paper.* Section 5 states the central practical implication: a
  signal-quality threshold tuned on synthetic data should be re-validated
  on real data before deployment; failure to do so risks accepting windows
  that all available published baselines reject.

## Other information

**Item 28.** Registration number and name of registry.

- *This paper.* This is a methodology audit, not a clinical trial; trial
  registration does not apply.

**Item 29.** Where the full study protocol can be accessed.

- *This paper.* Protocol is the repository itself; pinned by release tag.
  https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases

**Item 30.** Sources of funding and other support; role of funders.

- *This paper.* No external funding; self-supported research. To be stated
  in the author affiliation block once finalised.

---

## Summary of compliance

| Category | Items | Compliance |
|---|---:|---|
| Title and abstract | 2 | Compliant |
| Introduction | 2 | Compliant |
| Methods | 14 | Compliant; item 18 (formal power calculation) intentionally absent for exploratory audit |
| Results | 7 | Compliant; item 24 kappa CIs planned for next revision |
| Discussion | 2 | Compliant |
| Other | 3 | Compliant once author block is finalised |

**Items partially addressed**:
- Item 20 (baseline demographics): the paper refers reviewers to WESAD's
  own demographics rather than re-tabulating; acknowledged in Section 6.
- Item 24 (precision estimates): Bland-Altman LoA and Pearson r have 95%
  bootstrap CIs reported; kappa point estimates do not yet have CIs.
  Bootstrap kappa CIs are a planned addition.

**Items not applicable**: 21a, 21b, 25, 28 (no disease target, no
clinical-trial framing).
