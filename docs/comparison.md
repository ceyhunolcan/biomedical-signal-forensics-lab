# Comparison with existing toolkits

A common first question is "how does this toolkit relate to neurokit2 or
heartpy?". The short answer is that the existing tools and this toolkit
target different problems and are complementary rather than substitutes.

The existing tools provide comprehensive signal processing primitives:
filtering, peak detection, HRV features, cardiorespiratory analysis. This
toolkit assumes those primitives already exist and adds an audit layer that
asks a different question: *given* a signal-processing pipeline, what is the
evidence that its outputs are quality-controlled, fairness-aware,
causally-interpretable, and downstream-stable?

The table below maps the feature coverage. Entries reflect the state of each
project at the time of writing and are intended to be charitable; corrections
welcome via pull request.

## Feature coverage

| Capability | neurokit2 | heartpy | hrv-analysis | BiosPPy | this toolkit |
|---|---|---|---|---|---|
| ECG peak detection | yes | partial | indirect | yes | uses heartpy/neurokit2 |
| PPG peak detection | yes | yes | indirect | yes | uses heartpy/neurokit2 |
| HRV feature computation | yes | yes | yes | yes | uses external |
| EDA / EMG / respiration | yes | no | no | yes | scope-limited |
| Multiple SQI baselines compared | no | no | no | no | **yes (4-way)** |
| Pairwise SQI agreement (Cohen's kappa) | no | no | no | no | **yes** |
| Fairness audit by stratum | no | no | no | no | **yes** |
| Causal sensitivity (AIPW, E-values) | no | no | no | no | **yes** |
| Negative-control exposures | no | no | no | no | **yes** |
| Downstream-task impact (LOSO) | no | no | no | no | **yes** |
| Reporting-standards checklists shipped | no | no | no | no | **yes** |
| Test suite size | large | small | small | medium | 235 tests |
| Trusted-publisher PyPI release | yes | yes | yes | yes | yes |
| Zenodo concept DOI | varies | varies | varies | varies | yes |

## When to use which

| If you need to | Reach for |
|---|---|
| Filter, detect peaks, extract HRV features from raw signals | neurokit2 or heartpy |
| A single end-to-end PPG/ECG pipeline with good defaults | neurokit2 |
| Compare a quality-control choice against published baselines | this toolkit |
| Audit a digital-health analysis for fairness, causal, or downstream issues | this toolkit |
| Produce reporting-standards-compliant supplementary materials | this toolkit |
| Deploy a clinical decision-support system | none of these; consult regulatory pathway |

## Composability

This toolkit is designed to wrap existing pipelines, not replace them. A
typical workflow is:

1. Process the raw signals using neurokit2 (peak detection, basic HRV).
2. Pass the resulting per-window features into the audit pipeline here.
3. Read the methodology recommendations and adjust the pipeline if any audit
   flags an issue.
4. Re-run the downstream analysis with the adjusted pipeline.

The toolkit imports nothing from neurokit2 or heartpy directly (to keep the
dependency surface small) but the example notebooks in `notebooks/` show how
to combine them.

## A note on charity

The "no" entries in the table above do not mean the corresponding projects
are deficient. They mean the audit layer is out of scope for those projects,
which is a reasonable scope decision; the existence of this toolkit does not
imply that other tools should have included an audit layer. Conversely, the
"yes" entries in this toolkit do not mean the audit replaces deep signal
processing expertise; they mean the toolkit provides quantitative evidence
that the practitioner uses to inform analytic decisions.

If a comparison row is inaccurate or out of date, please open an issue at
https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/issues with the
correction.

## Citation pointers for the comparison

- neurokit2: Makowski et al. (2021), *Behavior Research Methods*.
- heartpy: van Gent et al. (2019), *Journal of Open Research Software*.
- hrv-analysis: Champseix (2018), open-source release.
- BiosPPy: Carreiras et al. (2015), open-source release.

Full bibliographic detail for the baselines compared in the SQI audit
(Orphanidou 2015, Sukor 2011, Elgendi 2016) is in
[`paper/paper.bib`](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/blob/main/paper/paper.bib).
