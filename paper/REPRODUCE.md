# Reproducing the paper

Commands that regenerate the data tables, figures, and compiled documents for
the paper "A Single Signal-Quality Threshold Is Insufficient for Wearable
Photoplethysmography". Run everything from the repository root.

## 1. Environment

    make install-dev

Installs the runtime dependencies from `requirements.txt` plus the development
tools (pytest, ruff). The Makefile defaults to `python`; if your interpreter is
`python3`, pass it through, for example `make PYTHON=python3 all`.

## 2. Source datasets

The empirical study uses two public datasets from the UCI Machine Learning
Repository, downloaded separately (they are not redistributed here):

- WESAD: https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detection (DOI 10.24432/C57K5T)
- PPG-DaLiA: https://archive.ics.uci.edu/dataset/495/ppg+dalia (DOI 10.24432/C53890)

Download and unpack both, then point the analysis scripts in step 3 at their
locations (each script's `--help` lists the expected path option).

## 3. Real-data window tables

These regenerate the per-window analysis tables documented in
`results/README.md`:

    python3 scripts/run_wesad_deep_analysis.py      # results/real_data/wesad_deep/window_table.csv
    python3 scripts/run_ppg_dalia_audit.py          # results/real_data/ppg_dalia/window_table.csv

The real-data analysis also regenerates the figures that depend on the window
tables, including the recalibration curve (Figure 4, `fig6_recalibration.png`)
and the per-state and motion supporting panels, through
`real_data_figures.make_all_figures`.

## 4. Figures with a standalone generator

Each command writes into `paper/figures/`:

    python3 paper/figures/fig1_upset.py             # Figure 1: cross-method UpSet plot
    python3 scripts/figures/plot_bland_altman.py    # Figure 2: cross-modality heart-rate Bland-Altman
    python3 generate_results_figures.py             # Figure 3 (kappa heatmap) and Supplementary Figure S4 (rejection cascade)
    python3 scripts/run_downstream_audit_demo.py    # Figure 5: downstream stress-detection outcomes
    python3 scripts/generate_flow_diagram.py        # Supplementary Figure S1: analysis flow diagram
    python3 scripts/make_supp_figs.py               # Supplementary Figures S2 and S3

`paper/figures/fig1_upset.py` and `generate_results_figures.py` read the
committed window tables, so they reproduce Figure 1 and the rejection cascade
without the source datasets.

## 5. Synthetic-validation pipeline

The synthetic-cohort components (Supplementary Section S10 and Supplementary
Figures S5 and S6) need no external data:

    make all                 # generate the synthetic cohort, run the audit, train, and report
    make cross-cohort        # cross-cohort generalization check

## 6. Compile and check

    python3 scripts/compile_paper.py                # build manuscript.docx and supplement.docx
    python3 scripts/bug_check.py                    # validate figures, citations, sections, style
    python3 tests/test_paper_headline_numbers.py    # confirm the headline counts match the data
    make test-pytest                                # full test suite
    make lint                                       # ruff check and format check
    make check-em-dashes                            # fail on any em-dash in .md or .py
