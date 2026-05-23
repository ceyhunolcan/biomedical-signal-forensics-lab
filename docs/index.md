# biomedical-signal-forensics-lab

An open-source Python toolkit for auditing wearable physiological signal
pipelines. It targets four failure modes that commonly invalidate
downstream conclusions in digital-health research.

!!! warning "Research prototype only"
    This toolkit is a research prototype. Not medical advice, diagnosis,
    treatment, or a medical device.

## What this toolkit does

1. **Signal-quality auditing.** Four signal-quality binarisations
   (in-house, [Orphanidou 2015](https://doi.org/10.1088/0967-3334/36/8/1781),
   [Sukor 2011](https://doi.org/10.1088/0967-3334/32/4/004),
   [Elgendi 2016](https://doi.org/10.3390/bioengineering3040021)) compared
   on the same windows, with pairwise Cohen's kappa and consensus-failure
   rates.
2. **Algorithmic fairness audit.** Per-stratum performance differences
   detected and decomposed on synthetic cohorts with injected disparities
   in device family and skin tone.
3. **Causal sensitivity analysis.** AIPW doubly-robust estimation with
   E-values and back-door adjustment under a user-supplied DAG.
4. **Downstream-task impact testing.** Per-fold AUROC comparison under
   different preprocessing regimes, paired Wilcoxon signed-rank test
   over LOSO folds.

## Key results on real wrist PPG (WESAD, n=15)

- Bland-Altman bias **+3.57 bpm**, 95% LoA **[-23.14, +30.28]** bpm,
  MAE 9.66 bpm, Pearson r = +0.70.
- Three published SQI baselines collectively reject **44.6%** of windows
  (2,936 of 6,585) that the in-house default threshold accepts.
- Downstream classifier AUROC differs by 0.019 between raw and cleaned
  preprocessing; paired Wilcoxon p = 1.5e-4 over 15 LOSO folds.

## Where to go next

- [Getting started](getting-started.md): install and run the pipeline.
- [Reproducing the paper](reproducing-paper.md): step-by-step
  reproduction of every numerical claim.
- [Reporting standards](reporting-standards.md): per-item TRIPOD+AI and
  STARD 2015 compliance.
- [API reference](api-reference.md): module-level documentation.
- [Citing](citing.md): how to cite the software.

## Status

- Latest release: see the [GitHub releases page](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases).
- Tests: 235 passing on Python 3.10, 3.11, 3.12.
- License: [MIT](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/blob/main/LICENSE).
- DOI: [10.5281/zenodo.20349806](https://doi.org/10.5281/zenodo.20349806).
