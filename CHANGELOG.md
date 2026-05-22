# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

(no changes yet)

## [0.13.0] - 2026-05-22

### Added
- `CITATION.cff` so GitHub displays a "Cite this repository" button and so
  third-party citation tools (Zotero, Mendeley) can parse machine-readable
  citation metadata.
- `.zenodo.json` with explicit metadata for Zenodo deposit at release time
  (title, description, author with ORCID, license, keywords).
- `CHANGELOG.md` in Keep a Changelog format, back-filled from v0.7.1.
- README badge bar covering CI, license, supported Python versions, current
  version, and DOI (DOI placeholder until first Zenodo deposit).
- README citation block with both BibTeX and the GitHub-citation button
  approach.

### Changed
- Version strings in `pyproject.toml` and `src/__init__.py` synchronised to
  `0.13.0`. Earlier release-bump shell commands used regex patterns
  anchored on the prior version string; after `0.8.0` the pattern stopped
  matching and subsequent bumps silently no-ops'd, leaving the package
  version at `0.8.0` while git tags advanced to `v0.12.0`. The new
  `scripts/update_version.py` reads from any prior version and writes the
  target explicitly so this cannot recur.

### Fixed
- Stale `scripts/paper/` directory from an earlier manual copy step; the
  canonical figures live in `paper/figures/`.

## [0.12.0] - 2026-05-22

### Added
- Per-item reporting-standards checklists in `paper/checklists/`:
  - `tripod_ai_checklist.md` for the Section 4.6 downstream classifier
    (TRIPOD+AI, Collins et al. 2024).
  - `stard_2015_checklist.md` for Sections 4.1-4.3 SQI-as-diagnostic-test
    framing (STARD 2015, Bossuyt et al. 2015).
  - `consort_ai_applicability.md` and `decide_ai_applicability.md`
    documenting why CONSORT-AI and DECIDE-AI do not apply (not a trial,
    not a clinical deployment), and what a future deployment study using
    this toolkit would need to report.
- Figure 1: STARD-style data flow diagram (`paper/figures/fig_flow_diagram.png`
  and `.svg`), reproducible via `scripts/generate_flow_diagram.py`.
- New manuscript subsection 3.7 "Reporting standards and reproducibility"
  inserted before Section 4.

### Changed
- Manuscript text patched to cite the four reporting-standard references
  that were previously orphaned in the bibliography
  (`@collins2024tripodai`, `@bossuyt2015stard`, `@liu2020consortai`,
  `@vasey2022decideai`).

## [0.11.0] - 2026-05-22

### Added
- 21 verified bibliography entries appended to `paper/paper.bib`:
  - PPG and wearable validation: Allen 2007, Mejia-Mejia et al. 2021,
    Schaefer and Vagedes 2013, Bent et al. 2020, Shcherbina et al. 2017.
  - Algorithmic fairness in health: Obermeyer et al. 2019, Sjoding et al.
    2020, Vyas et al. 2020.
  - HRV methodology: Shaffer and Ginsberg 2017.
  - Reporting standards: Collins et al. 2024 (TRIPOD+AI), Liu et al. 2020
    (CONSORT-AI), Vasey et al. 2022 (DECIDE-AI), Bossuyt et al. 2015
    (STARD).
  - Causal inference: VanderWeele and Ding 2017 (E-value), Hernan and
    Robins 2020, Funk et al. 2011 (AIPW).
  - Statistical methods: Cohen 1988, Cliff 1993, Wilcoxon 1945, Koo and Li
    2016, Adams and MacKay 2007 (BOCPD).
- 13 citation insertions at strategic anchor points throughout the
  manuscript.

### Changed
- Total bibliography expanded from 13 to 34 verified references.

### Fixed
- Removed a single duplicate entry: `taskforce1996` (Circulation venue)
  was a re-print of the existing `malik1996` entry (European Heart Journal
  venue) for the same HRV Task Force 1996 document.

## [0.10.0] - 2026-05-22

### Added
- Elgendi 2016 (SSQI, KSQI, ESQI) as a third published SQI baseline
  alongside Orphanidou 2015 and Sukor 2011. Implementation in
  `src/signals/elgendi_sqi.py` with auto-polarity detection for the
  E4 wrist PPG signal convention.
- 16 new tests covering `elgendi_sqi` (total tests now 235).
- Four-way SQI agreement analysis in
  `src/evaluation/deep_real_analysis.py`.
- Section 4.2 (manuscript) rewritten around the consensus-rejection
  finding.

### Changed
- Section 5.1 Finding #5 generalised from two baselines to three.
- Abstract Results paragraph updated to reflect the three-baseline
  agreement finding.
- Figure 5 regenerated with four bars and a 4x4 pairwise kappa matrix.

### Key result on n=15 WESAD
- All three published SQI baselines individually pass 21-26% of wrist PPG
  windows.
- Pairwise published-vs-published Cohen's kappas: Orph-Sukor +0.41,
  Orph-Elgendi -0.20, Sukor-Elgendi -0.22 (median +/-0.20).
- All three published baselines simultaneously fail on 44.6% of windows
  (2,936 of 6,585).
- The in-house default threshold (0.70) passes every one of those 2,936
  windows.

## [0.9.0] - 2026-05-22

### Added
- Section 4.6 downstream-audit demo: per-subject LF/HF ratio (baseline vs
  stress) classifier evaluated under raw vs in-house cleaned preprocessing.
- LOSO 15-fold cross-validation.
- Paired Wilcoxon signed-rank test on per-fold AUROC.

### Key result on n=15 WESAD
- Per-subject biomarker correlation rho = +0.10 paired (13 of 15
  subjects); Wilcoxon p = 1.5e-4.
- LOSO AUROC 0.804 (raw) -> 0.823 (cleaned); paired comparison p = 0.052.

## [0.8.1] - 2026-05-21

### Added
- Supplement_extended_analyses.md completed for n=15.

### Changed
- All figures regenerated at n=15.

## [0.8.0] - 2026-05-21

### Added
- Real-data validation scaled from n=2 pilot to all 15 WESAD subjects
  (S2-S11, S13-S17).

### Changed
- 6,585 windows in total across the full cohort.

### Key result
- Bland-Altman bias +3.57 bpm between wrist Empatica E4 PPG and chest
  RespiBAN ECG, 95% LoA [-23.14, +30.28] bpm, MAE 9.66 bpm, Pearson
  r = +0.70.
- The pilot finding that recalibration improved holdout agreement
  (delta kappa = +0.22 at n=2) DID NOT replicate at n=15
  (delta kappa = 0.00).

## [0.7.1] - 2026-05-20

### Added
- Initial public release.
- n=2 WESAD pilot validation.
- Synthetic cohort with injected fairness disparities.
- AIPW causal sensitivity analysis.
- Two published SQI baselines: Orphanidou 2015, Sukor 2011.

[Unreleased]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/compare/v0.13.0...HEAD
[0.13.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/compare/v0.8.1...v0.9.0
[0.8.1]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.7.1
