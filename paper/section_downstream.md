### 4.6 Downstream model performance with vs without audit filtering

The framework's signal-quality audit is methodological infrastructure: it does not by itself produce a clinical prediction. To show that the audit nevertheless changes downstream model behavior, we evaluated two distinct downstream tasks on the WESAD wrist PPG data under four data-conditioning regimes: (i) no audit (all windows), (ii) in-house SQI default threshold pass, (iii) Orphanidou (2015) pass, (iv) both in-house and Orphanidou pass.

**Task A. Baseline-vs-stress classification.** We trained a logistic regression on three wrist PPG features (PPG-derived HR, motion artifact score, in-house SQI) to discriminate baseline from stress windows. Validation used strict leave-one-subject-out (LOSO) cross-validation across all 15 WESAD subjects; features were standardized within each fold and the classifier was scored on the held-out subject.

| Condition | n subjects | Mean AUROC | 95% bootstrap CI | Median AUROC |
|---|---|---|---|---|
| no audit | 15 | 0.804 | [0.716, 0.871] | 0.850 |
| in-house pass (≥ 0.70) | 15 | 0.804 | [0.716, 0.871] | 0.850 |
| **Orphanidou pass** | **14** | **0.823** | **[0.744, 0.906]** | **0.822** |
| both | 14 | 0.823 | [0.744, 0.906] | 0.822 |

| Condition vs no-audit | n paired | Mean Δ AUROC | n improved / n worse | Wilcoxon p (one-sided, greater) |
|---|---|---|---|---|
| in-house | 15 | 0.000 | 0 / 0 | 1.000 |
| **Orphanidou** | **14** | **+0.027** | **10 / 4** | **0.052** |
| both | 14 | +0.027 | 10 / 4 | 0.052 |

The in-house SQI default threshold passes every window (pass rate 1.000; Section 4.2), so "in-house" is identical to "no audit" by construction. The Orphanidou-filtered condition shows a +0.027 mean improvement in held-out subject AUROC with 10 of 14 subjects improving, just outside conventional significance (p = 0.052). We report this as a suggestive trend rather than a significant effect.

**Task B. Per-subject biomarker correlation.** For each subject, we computed the Spearman correlation between the wrist-PPG-derived HR and the chest-ECG-derived HR under each audit condition. We then paired the per-subject ρ values across conditions and tested whether audit filtering produces a consistent improvement (one-sided Wilcoxon signed-rank).

| Comparison | n paired | Mean Δ ρ | Median Δ ρ | n improved / n worse | Wilcoxon p (greater) |
|---|---|---|---|---|---|
| in-house vs all | 15 | 0.000 | 0.000 | 0 / 0 | 1.000 |
| **Orphanidou vs all** | **15** | **+0.102** | **+0.110** | **13 / 2** | **1.5e-04** |
| both vs all | 15 | +0.102 | +0.110 | 13 / 2 | 1.5e-04 |

Restricting to Orphanidou-passing windows improves the per-subject correlation between wrist PPG HR and chest ECG HR by a median of **+0.110** across the 15-subject cohort, with **13 of 15 subjects improving** and **2 declining** (subjects S4, S8 show a slight decline). The paired Wilcoxon test gives **p = 1.5e-04**, comfortably significant. The largest improvements are in subjects whose unfiltered correlation was modest: S10 (0.65 → 0.78), S9 (0.47 → 0.76), S13 (0.42 → 0.54), S6 (0.53 → 0.71).

**Combined interpretation.** Audit filtering reliably improves window-level biomarker estimation but only marginally improves cohort-level classification. The Spearman improvement (p < 0.001) is the more direct test of the framework's value because it operates at the per-window level where the audit acts. The classification result (p = 0.05) is more demanding because LOSO held-out evaluation on n = 15 has limited statistical power; the +0.027 mean improvement is consistent with a real effect that the sample size does not let us declare significant. The trade-off is data retention: Orphanidou filtering keeps roughly 26% of windows. For subjects with already-strong correlation (S14, S16, S17 all at ρ ≥ 0.83 without filtering), the improvement is modest; for subjects with weaker correlation (S2, S5, S15 at ρ < 0.60 without filtering), the gain is substantial.

**Trade-off characterization.** Figure 10 panel D plots per-subject retention against Δρ. Subjects above the y = 0 line benefit from filtering; the small minority below (S4, S8) lose information at the audit threshold. A practitioner deploying the framework can read this trade-off plot directly: for any new dataset they can compute per-subject retention and Δ and decide whether to filter, threshold differently, or skip the audit entirely.

Figure 10 (`results/downstream_demo/figure_downstream.png`):
- Panel A: LOSO AUROC distributions by audit condition.
- Panel B: per-subject paired Δ AUROC vs no-audit, by audit variant.
- Panel C: per-subject biomarker ρ under each condition.
- Panel D: per-subject retention vs Δρ trade-off (Orphanidou condition).

Source: `results/downstream_demo/classification_summary.csv`, `results/downstream_demo/biomarker_correlation.csv`, `results/downstream_demo/figure_downstream.png`. Reproducible end-to-end from `python scripts/run_downstream_audit_demo.py`.