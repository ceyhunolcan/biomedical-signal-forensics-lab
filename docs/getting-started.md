# Getting started

This page walks you from a clean checkout to your first end-to-end run
of the audit pipeline. Allow about ten minutes.

## Requirements

- Python 3.10, 3.11, or 3.12
- 2 GB of free disk space (more if you intend to use WESAD)
- No GPU required; the pipeline runs on a laptop CPU

## Install

### From PyPI (once published)

```bash
pip install biomedical-signal-forensics-lab
```

### From source

```bash
git clone https://github.com/ceyhunolcan/biomedical-signal-forensics-lab.git
cd biomedical-signal-forensics-lab
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -e .
```

## Verify the installation

```bash
python -c "import biomedical_signal_forensics_lab; print(biomedical_signal_forensics_lab.__version__)"
python scripts/run_tests_minimal.py
```

The test suite should report `Passed: 235 / Failed: 0 / Skipped: 0`.

## First run: the synthetic pipeline

The synthetic pipeline needs no external data. It generates a
300-participant 60-day cohort with five injected failure modes, runs
the audit, and writes a JSON summary plus figures.

```bash
python scripts/run_pipeline.py
```

Outputs:

- `results/synthetic/summary.json` - point estimates and confidence
  intervals for the trust score, fairness disparities, AIPW effects.
- `paper/figures/` - publication figures regenerated from the new run.

The whole pipeline takes about three minutes on a laptop.

## Second run: WESAD real-data validation

This requires the WESAD dataset. Download it from
[the UCI repository](https://archive.ics.uci.edu/dataset/465/wesad)
and unzip it locally; the script accepts the path to the unzipped
directory.

```bash
python scripts/run_deep_real_analysis.py --path /path/to/WESAD
```

Outputs:

- `results/real_data/wesad_deep/summary.json` - Bland-Altman bias, LoA,
  four-way SQI agreement, motion-vs-error correlations, recalibration
  results.
- `results/real_data/wesad_deep/figures/` - six figures used in
  Sections 4.1 through 4.3 of the manuscript.

The run takes about three minutes on a laptop.

## Troubleshooting

??? note "ImportError on `biomedical_signal_forensics_lab`"
    Confirm you installed in editable mode (`pip install -e .`) from
    inside the repository root. Also confirm your virtual environment
    is activated.

??? note "WESAD path does not point to the right place"
    The `--path` argument should point at the directory that contains
    `S2/`, `S3/`, ..., `S17/` subdirectories, not the parent ZIP file
    or a different layer of nesting.

??? note "Figures appear with a different style"
    The pipeline uses matplotlib defaults. If you have a custom
    matplotlibrc that overrides font or colour settings, the figures
    will pick up those changes. Reset with `matplotlib.rcdefaults()` or
    use a fresh environment.

## Next steps

- Reproduce every numerical claim in the manuscript:
  [Reproducing the paper](reproducing-paper.md).
- Read the reporting-standards compliance docs:
  [Reporting standards](reporting-standards.md).
- Browse the module-level API:
  [API reference](api-reference.md).
