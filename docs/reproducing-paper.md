# Reproducing the paper

This page walks through reproducing every numerical claim in the
manuscript. The full sequence runs end-to-end in under ten minutes on
a laptop CPU, with no GPU and no cloud access required.

Every script is deterministic given a fixed seed; the numbers you
see should match the manuscript to the last decimal.

## Section 3-4.5: synthetic cohort

```bash
python scripts/run_pipeline.py
```

Reproduces:

- Trust score distribution (Section 4.3)
- Bootstrap test-retest correlations (Section 4.4)
- AIPW causal-adjusted effects with E-values (Section 4.5)
- Fairness disparities by device family and skin tone (Section 4.5)
- Cross-cohort parameter sweep (Section 4.5)

Outputs:

- `results/synthetic/summary.json`
- `paper/figures/fig2_*.png` through `fig4_*.png`

## Sections 4.1 to 4.3: WESAD real-data validation

```bash
python scripts/run_deep_real_analysis.py --path /path/to/WESAD
```

Reproduces:

- Bland-Altman bias +3.57 bpm, 95% LoA [-23.14, +30.28] bpm
  (Section 4.1)
- Four-way SQI agreement matrix and consensus-rejection rate of 44.6%
  (Section 4.2)
- Recalibration analysis (delta kappa = 0.000 at n=15) (Section 4.3)

Outputs:

- `results/real_data/wesad_deep/summary.json`
- `results/real_data/wesad_deep/window_table.csv`
- `results/real_data/wesad_deep/figures/fig1_*.png` through `fig6_*.png`

## Section 4.6: downstream classifier audit

```bash
python scripts/run_downstream_audit_demo.py --path /path/to/WESAD
```

Reproduces:

- Per-subject LF/HF biomarker correlation rho = +0.10 paired
- Wilcoxon p = 1.5e-4 over 15 LOSO folds
- AUROC 0.804 (raw preprocessing) -> 0.823 (cleaned preprocessing)

Outputs:

- `results/downstream/summary.json`

## Section 4.7 and supplement

```bash
python scripts/run_extended_analyses.py
python scripts/run_cross_cohort_check.py
```

These produce the cross-cohort qualitative-prediction recovery table
and the extended supplementary analyses.

## Figure 1: STARD-style flow diagram

```bash
python scripts/generate_flow_diagram.py
```

Outputs:

- `paper/figures/fig_flow_diagram.png`
- `paper/figures/fig_flow_diagram.svg`

## Numerical reproducibility caveats

- All randomness in this pipeline is seeded. If you change a script or
  the random-number generator state, numbers may differ in the last
  decimal. The seed is set at the top of each script.
- WESAD itself is deterministic (it is a fixed dataset). Bland-Altman
  numbers in particular are exact to the cent across machines.
- Bootstrap CIs use 1,000 resamples by default; smaller numbers will
  produce noisier intervals.

## Verifying against the manuscript

Each script writes a `summary.json` whose top-level keys are the same
as the numerical claims in the manuscript. To verify a specific number,
search the manuscript for the value, then grep the corresponding
summary file.

For example, to verify the +3.57 bpm Bland-Altman bias:

```bash
python -c "
import json
s = json.load(open('results/real_data/wesad_deep/summary.json'))
print(s['hr_agreement_overall'])
"
```

If the value matches the manuscript, the analysis is reproduced.
