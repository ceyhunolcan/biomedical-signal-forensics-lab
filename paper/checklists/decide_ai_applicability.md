# DECIDE-AI applicability assessment

**Reference**: Vasey B, Nagendran M, Campbell B, et al. *Reporting guideline
for the early-stage clinical evaluation of decision support systems driven
by artificial intelligence: DECIDE-AI.* Nature Medicine
2022;28(5):924-933. doi:10.1038/s41591-022-01772-9

## Does DECIDE-AI apply to this paper? No.

DECIDE-AI is a 27-item reporting guideline specifically for the early-stage
clinical evaluation of AI-based decision support systems being used by
clinicians on real patients in real clinical settings. It sits in the
EQUATOR landscape between DEVELOPMENT-stage standards (TRIPOD+AI) and
TRIAL-stage standards (CONSORT-AI), filling the gap of "first clinical use
under monitoring."

This paper presents a methodology audit using retrospective public data
(WESAD). The pipeline described has not been used by any clinician, on any
patient, in any clinical setting. DECIDE-AI is therefore not applicable.

The paper references DECIDE-AI for completeness because future work using
this toolkit might enter that phase, and an honest reader of the paper
deserves a pointer to the relevant standard for that next step.

## What would DECIDE-AI require if this toolkit entered early clinical use?

If a clinical team deployed the SQI auditing pipeline in a real care
setting under monitoring, DECIDE-AI would require reporting on:

- the clinical setting and stage of deployment, including how patients
  were selected and what care decisions the AI output informed,
- the version of the AI system deployed (the repository release tag would
  provide this directly),
- the human-AI interaction model, including whether clinicians override
  the AI output and how often,
- patient-relevant outcomes and a safety profile,
- learning curves and performance changes during the early-use period,
- ethical, regulatory, and consent considerations specific to the
  deployment site.

None of these items can be addressed in the current paper because none of
those activities have occurred. This document exists to flag DECIDE-AI as
the right standard for the next step, not as one this paper claims to
satisfy.

## Why include this document at all if the standard does not apply?

Reviewers familiar with the EQUATOR landscape may reasonably ask whether
the authors considered DECIDE-AI. Including an explicit applicability
assessment makes the answer transparent: the standard was considered, the
work does not fall within its scope, and a future deployment study should
return to it.
