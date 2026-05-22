# Reporting standards: compliance and applicability documentation

This directory contains a per-standard compliance summary for the four EQUATOR
reporting standards most often cited for digital-health methodology papers.

Two of the four apply directly to this work and are filled in item-by-item; two
do not apply and are accompanied by short applicability assessments that
explain why and what they would look like if a future deployment study used
this toolkit.

| Standard | Applies? | File |
|---|---|---|
| TRIPOD+AI (Collins et al. 2024) | Partial (Section 4.6 downstream classifier) | `tripod_ai_checklist.md` |
| STARD 2015 (Bossuyt et al. 2015) | Yes (Sections 4.1-4.3 SQI-as-diagnostic-test framing) | `stard_2015_checklist.md` |
| CONSORT-AI (Liu et al. 2020) | No (not a randomised clinical trial) | `consort_ai_applicability.md` |
| DECIDE-AI (Vasey et al. 2022) | No (not a clinical deployment study) | `decide_ai_applicability.md` |

The flow diagram in `paper/figures/fig_flow_diagram.png` is rendered in the
STARD 2015 style adapted to the multi-arm structure of this audit (one source,
four analysis arms operating on the same 6,585 windows).

## How reviewers should read this

For each applicable standard, the checklist file lists every numbered item
from the published statement, followed by:

- a one-line statement of how this paper addresses (or does not address) the
  item, and
- a pointer to the specific manuscript section, supplement, or repository
  artefact that contains the relevant content.

Where an item is partially addressed or marked "not applicable", the rationale
is stated rather than asserted. Items that are not addressed at all are listed
as such, with a brief note on why and whether addressing them in a future
revision would be valuable.

## Provenance and verification

All four reporting standards are cited in `paper/paper.bib` with full
bibliographic details (publisher record verified). They are referenced in the
manuscript at the points described in each per-standard file.

The checklists below were prepared by reading each numbered item of the
published standard against the current state of the manuscript and the
repository, and are subject to revision as the paper evolves.
