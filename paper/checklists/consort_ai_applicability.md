# CONSORT-AI applicability assessment

**Reference**: Liu X, Cruz Rivera S, Moher D, Calvert MJ, Denniston AK (on
behalf of the SPIRIT-AI and CONSORT-AI Working Group). *Reporting guidelines
for clinical trial reports for interventions involving artificial
intelligence: the CONSORT-AI extension.* Nature Medicine 2020;26(9):1364-1374.
doi:10.1038/s41591-020-1034-x

## Does CONSORT-AI apply to this paper? No.

CONSORT-AI extends the CONSORT 2010 reporting standard for randomised
controlled trials, adding 14 AI-specific items on top of the base CONSORT
checklist. It is intended for clinical trial reports in which an AI-based
intervention is evaluated against a comparator (sham, standard care, or
another AI system).

This paper is a retrospective methodology audit of physiological signal
processing. It contains:

- no participant randomisation,
- no clinical intervention,
- no comparator arm in the trial sense,
- no clinical outcome,
- no enrolment of human subjects beyond use of an already-collected and
  already-released public dataset (WESAD).

CONSORT-AI is therefore not a relevant reporting standard for the work
presented. The paper references CONSORT-AI for completeness and to signal
awareness of the broader EQUATOR network landscape for digital-health AI.

## What would CONSORT-AI require if this toolkit were deployed in a trial?

A future clinical trial evaluating a signal-quality auditing pipeline
derived from this toolkit (for example, a randomised trial comparing
clinical decisions made with vs without the toolkit's quality flagging)
would need to report:

- AI-1: instructions on integrating the AI intervention into the trial
  setting, including the version of the toolkit deployed, the dependency
  pin, and the operating environment.
- AI-2: the input data handling pipeline (signal acquisition, windowing,
  pre-processing), including any data exclusion logic.
- AI-3: the output (signal-quality decision) and how it was acted on by
  clinicians or downstream systems.
- AI-4: human-AI interaction during the trial (whether clinicians could
  override the toolkit's quality flag).
- AI-5: error analysis, including any human-detected errors in the AI
  output.

The repository would supply most of the AI-1, AI-2, AI-3 content as
provenance metadata; AI-4 and AI-5 would be trial-specific.

This document exists to make the inapplicability explicit and to provide a
roadmap for any group that does choose to use this toolkit in a future
prospective clinical evaluation.
