# Methods

A narrative walk-through of the four audit components. For the manuscript-grade
methods text see `paper/paper.md` and the reporting-standards checklists in
`paper/checklists/`; for inline API reference see the [API reference](api/index.md).

The audit is organised around four cooperating components, each producing
quantitative evidence that feeds a single set of methodology recommendations.

## 1. Signal-quality audit

The signal-quality component evaluates each thirty-second window of wrist PPG
against four independent indicators:

| Indicator | Reference | Threshold logic |
|---|---|---|
| In-house | this work | Amplitude, baseline drift, and beat-detection consistency thresholds tuned on synthetic data |
| Orphanidou et al. | 2015 | Template-matching against an averaged beat shape; correlation threshold 0.66 |
| Sukor et al. | 2011 | Skewness and pulse-amplitude variability of detected beats |
| Elgendi | 2016 | Signal-to-noise ratio in the cardiac frequency band |

For each window the toolkit records a pass/fail decision from each indicator
and computes pairwise Cohen's kappa across indicators. A window is considered
**consensus-rejected** when all three published baselines reject it
simultaneously, and **consensus-passed** when at least one published baseline
passes it. The in-house indicator is reported separately because its 100% pass
rate makes Cohen's kappa undefined (zero marginal variance) against the others.

The empirical finding on WESAD (44.6% consensus rejection, median pairwise
kappa = -0.20) motivates the rest of the audit: if three independent published
indicators disagree this strongly on the same six-thousand-window cohort, no
single threshold can be assumed to be correct.

## 2. Algorithmic-fairness audit

The fairness component stratifies signal-quality and downstream outcomes by:

- device family (chest-strap, wrist-worn, finger-clip)
- skin tone (Fitzpatrick I to VI when annotated)
- per-subject drift (sliding-window kappa within subject)
- motion intensity (accelerometer RMS quartile)

For each stratum the toolkit reports the difference in pass rate, the
difference in downstream AUROC, and a permutation-test p-value against the
null of stratum independence. Disparities are reported as effect sizes with
bootstrap confidence intervals; no claim of "fair" or "unfair" is made
categorically.

The audit does not claim to enumerate all sites of inequity. Inclusion of
additional strata (socioeconomic, geographic, temporal) is supported through
the `reliability.fairness_audit.add_stratum` API.

## 3. Causal-sensitivity audit

The causal-sensitivity component evaluates whether an observed exposure-outcome
association survives back-door adjustment for measured confounders, and how
robust the adjusted estimate is to unmeasured confounding.

Three methods are applied to each candidate confounder:

| Method | Reference | What it tests |
|---|---|---|
| AIPW doubly-robust estimation | Bang and Robins 2005 | Whether the exposure-outcome estimate is stable to misspecification of either the exposure model or the outcome model |
| E-value | VanderWeele and Ding 2017 | The minimum strength of association an unmeasured confounder would need with both the exposure and the outcome to fully explain the observed effect |
| Negative-control exposures | Lipsitch et al. 2010 | Whether a known-null exposure shows a spurious effect in the same direction (a positive negative control indicates residual confounding) |

The audit reports the back-door-adjusted point estimate, the E-value, and the
result of each negative control. An estimate that flips sign under back-door
adjustment, or that has an E-value below 1.5, is flagged as causally fragile
in the methodology-recommendations layer.

## 4. Downstream-impact audit

The downstream-impact component measures whether quality filtering and other
pre-processing decisions detectably move the metric the field cares about. For
stress detection on WESAD the toolkit reports:

- LOSO AUROC of a logistic-regression classifier on heart-rate variability
  features, baseline (no audit) versus after the full audit pipeline
- Recalibration kappa from a 50-50 random per-subject train/holdout split
- Spearman rho of paired window-level scores and the corresponding Wilcoxon
  signed-rank p-value

The headline downstream finding on WESAD is that quality filtering does not
improve recalibrated agreement (delta kappa = 0.000 at n = 15) but produces a
small, statistically significant paired effect (rho = +0.10, p = 1.5e-4) and a
delta-AUROC of +0.019. The toolkit emphasises that none of these effects are
clinically meaningful at this sample size, and reports them honestly rather
than rounding up.

## Methodology-recommendations layer

The four audits feed a single recommendations file
(`results/methodology_recommendations.md` after pipeline run) that summarises:

1. Which signal-quality indicator was used and why
2. Which fairness strata showed material disparities and the recommended
   reporting practice
3. Whether the causal interpretation is robust under back-door adjustment and
   the E-value for the headline effect
4. Whether the downstream effect of quality filtering is large enough to
   matter clinically

The recommendations are intentionally cautious. None of the four audits is a
substitute for prospective validation, external replication, or clinical-trial
evidence; the toolkit produces evidence about analytic choices, not about
clinical truth.

## Reporting standards

For the formal reporting-standards mapping see the [Reporting standards
page](reporting_standards.md) and the EQUATOR-Network checklists in
`paper/checklists/`. In short:

- **TRIPOD+AI** (Collins et al. 2024) applies and is mapped item by item
- **STARD 2015** (Bossuyt et al. 2015) applies and is mapped item by item
- **CONSORT-AI** (Liu et al. 2020) does not apply (non-interventional)
- **DECIDE-AI** (Vasey et al. 2022) does not apply (no clinician-AI interaction)

A STARD-style flow diagram is provided as Figure 1
(`paper/figures/fig_flow_diagram.png`).

## What this toolkit does not do

To be honest about scope:

- It does not generate new signal-quality indicators; it audits the ones
  already in the literature.
- It does not produce clinical predictions; it audits the analytic decisions
  that feed downstream models.
- It does not perform external validation; that requires a second cohort and
  is in the project roadmap.
- It does not claim that any single signal-quality threshold is correct; the
  whole point of the four-way audit is to surface disagreement.
- It does not certify a pipeline as fair, causal, or downstream-safe; it
  provides evidence that the practitioner uses to make those judgements.
