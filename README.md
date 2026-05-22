# biomedical-signal-forensics-lab

[![CI](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)
[![Version](https://img.shields.io/github/v/tag/ceyhunolcan/biomedical-signal-forensics-lab?label=release&color=blue)](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases)
[![Tests](https://img.shields.io/badge/tests-235%20passing-brightgreen)](tests/)
<!-- After Zenodo integration is enabled (see ZENODO_SETUP.md), replace the
     placeholder below with the actual DOI badge that Zenodo provides. -->
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20349806.svg)](https://doi.org/10.5281/zenodo.20349806)

An open-source Python toolkit for auditing wearable physiological signal
pipelines. It targets four failure modes that commonly invalidate
downstream conclusions in digital-health research:

1. **Signal-quality thresholds** that pass on real wrist PPG despite
   consensus rejection by published baselines.
2. **Algorithmic-fairness disparities** driven by device family, skin
   tone, and other site-of-inequity variables.
3. **Confounded causal interpretations** that reverse sign under
   back-door adjustment.
4. **Downstream-task degradation** measurable in classifier AUROC under
   different preprocessing choices.

> Research prototype only. Not medical advice, diagnosis, treatment, or a
> medical device.

## What this toolkit does

| Module | Function |
|---|---|
| `src/signals/` | PPG and ECG preprocessing; four signal-quality baselines (in-house, Orphanidou 2015, Sukor 2011, Elgendi 2016) |
| `src/evaluation/` | Real-data validation against WESAD (n=15 subjects, 6,585 windows); four-way SQI agreement; Bland-Altman; bootstrap CIs |
| `src/confounding/` | Causal sensitivity analysis: back-door adjustment, AIPW doubly-robust estimation, E-values |
| `src/reliability/` | ICC computation, test-retest stability, bootstrap reliability |
| `src/models/` | Downstream LF/HF biomarker classifier with LOSO cross-validation |
| `src/reports/` | Publication-grade figure generation and summary JSON writers |

## Quickstart

```bash
# Clone and install
git clone https://github.com/ceyhunolcan/biomedical-signal-forensics-lab.git
cd biomedical-signal-forensics-lab
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Run the test suite (should print 235 passed)
python scripts/run_tests_minimal.py

# Run the synthetic pipeline (no external data needed)
python scripts/run_pipeline.py

# Run the WESAD real-data validation (requires the WESAD dataset)
# Download WESAD from https://archive.ics.uci.edu/dataset/465/wesad and point
# the script at the local path:
python scripts/run_deep_real_analysis.py --path /path/to/WESAD
```

Outputs land in `results/`. Figures land in `paper/figures/`.

## Reproducing the paper analyses

The full analysis pipeline used in the manuscript is reproducible end-to-end:

```bash
python scripts/run_pipeline.py                  # synthetic cohort (Sections 3-4.5)
python scripts/run_deep_real_analysis.py        # WESAD real data (Sections 4.1-4.3)
python scripts/run_extended_analyses.py         # supplementary analyses
python scripts/run_downstream_audit_demo.py     # downstream classifier (Section 4.6)
python scripts/generate_flow_diagram.py         # Figure 1 (STARD flow)
```

Each script writes a JSON summary to `results/` that the manuscript
references directly. The manuscript and supplementary materials are in
`paper/`.

## Reporting standards compliance

Per-item compliance documentation for the EQUATOR-Network reporting
standards relevant to digital-health AI research:

- `paper/checklists/tripod_ai_checklist.md` (TRIPOD+AI, Collins et al. 2024)
- `paper/checklists/stard_2015_checklist.md` (STARD 2015, Bossuyt et al. 2015)
- `paper/checklists/consort_ai_applicability.md` (CONSORT-AI, Liu et al. 2020, does not apply, with rationale)
- `paper/checklists/decide_ai_applicability.md` (DECIDE-AI, Vasey et al. 2022, does not apply, with rationale)

A STARD-style data flow diagram is provided as Figure 1
(`paper/figures/fig_flow_diagram.png`).

## Citing this software

If you use this toolkit in academic work, please cite the software:

```bibtex
@software{olcan2026biomedical,
  author       = {Olcan, Ceyhun},
  title        = {{biomedical-signal-forensics-lab}: An open-source toolkit
                  for auditing wearable physiological signal pipelines},
  year         = {2026},
  version      = {v0.13.0},
  url          = {https://github.com/ceyhunolcan/biomedical-signal-forensics-lab},
  doi          = {10.5281/zenodo.20349806}
}
```

The "Cite this repository" button in the right sidebar of the GitHub repo
page surfaces the same metadata in plain text and BibTeX from
[`CITATION.cff`](CITATION.cff). Replace the DOI placeholder once the first
Zenodo deposit is minted; see [`ZENODO_SETUP.md`](ZENODO_SETUP.md) for the
one-time integration steps.

## License

MIT. See [LICENSE](LICENSE).

## Contact

Ceyhun Olcan,
Center for Technology and Behavioral Health,
Geisel School of Medicine at Dartmouth,
Lebanon, NH 03766, USA.
Email: ceyhun.olcan.27 [at] dartmouth.edu.
ORCID: [0000-0002-6326-6071](https://orcid.org/0000-0002-6326-6071).

## Acknowledgments

This toolkit makes use of the public WESAD dataset released by Schmidt
et al. (2018) and builds methodologically on the signal-quality indices
of Orphanidou et al. (2015), Sukor et al. (2011), and Elgendi (2016).
Reporting-standards guidance follows TRIPOD+AI (Collins et al. 2024) and
STARD 2015 (Bossuyt et al. 2015). Full bibliographic details are in
[`paper/paper.bib`](paper/paper.bib).
