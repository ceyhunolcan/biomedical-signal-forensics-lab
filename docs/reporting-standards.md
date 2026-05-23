# Reporting standards compliance

This page summarises compliance with the EQUATOR-Network reporting
standards relevant to digital-health AI research. The full per-item
checklists live in `paper/checklists/` in the repository and are pulled
in below.

## Summary

| Standard | Applies? | Coverage |
|---|---|---|
| TRIPOD+AI (Collins et al. 2024) | Partial (Section 4.6 classifier) | Per-item compliance below |
| STARD 2015 (Bossuyt et al. 2015) | Yes (Sections 4.1-4.3 SQI-as-test) | Per-item compliance below |
| CONSORT-AI (Liu et al. 2020) | No (not a randomised trial) | Applicability assessment below |
| DECIDE-AI (Vasey et al. 2022) | No (not a clinical deployment) | Applicability assessment below |

The flow diagram in
[paper/figures/fig_flow_diagram.png](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/blob/main/paper/figures/fig_flow_diagram.png)
follows STARD 2015 conventions adapted to the multi-arm structure of
this audit.

---

## TRIPOD+AI

{%
  include-markdown "../paper/checklists/tripod_ai_checklist.md"
  start="<!--start-->"
  end="<!--end-->"
  comments=false
  preserve-includer-indent=false
  trailing-newlines=false
  rewrite-relative-urls=true
%}

If the include above renders as raw text in your viewer, the full
checklist is at
[paper/checklists/tripod_ai_checklist.md](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/blob/main/paper/checklists/tripod_ai_checklist.md).

---

## STARD 2015

{%
  include-markdown "../paper/checklists/stard_2015_checklist.md"
  comments=false
  preserve-includer-indent=false
  trailing-newlines=false
  rewrite-relative-urls=true
%}

If the include above renders as raw text, the full checklist is at
[paper/checklists/stard_2015_checklist.md](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/blob/main/paper/checklists/stard_2015_checklist.md).

---

## CONSORT-AI: applicability assessment

{%
  include-markdown "../paper/checklists/consort_ai_applicability.md"
  comments=false
  preserve-includer-indent=false
  trailing-newlines=false
  rewrite-relative-urls=true
%}

---

## DECIDE-AI: applicability assessment

{%
  include-markdown "../paper/checklists/decide_ai_applicability.md"
  comments=false
  preserve-includer-indent=false
  trailing-newlines=false
  rewrite-relative-urls=true
%}
