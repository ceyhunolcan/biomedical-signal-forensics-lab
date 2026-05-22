# Changelog

All notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

## [0.5.0]

The first version with real-data validation results. WESAD pilot extended from a basic shakedown into a deep analysis with publication-grade figures and statistics.

### Added
- `src/signals/sukor_sqi.py`: Sukor 2011 four-feature PPG SQI as a second published baseline alongside Orphanidou 2015. Together they give the in-house SQI two independent witnesses on real PPG.
- `src/evaluation/deep_real_analysis.py`: cross-modality HR agreement (Bland-Altman), per-state paired Wilcoxon tests, three-way SQI agreement (kappa + Spearman), motion-vs-disagreement analysis, threshold recalibration experiment.
- `src/reports/real_data_figures.py`: six publication-quality figures (Bland-Altman, HR scatter, SQI pass rates, per-state distributions, motion-vs-error, recalibration curve).
- `scripts/run_deep_real_analysis.py`: end-to-end driver that produces all five analyses and the figure pack in one ~90-second run on the full WESAD dataset.
- `paper/real_data_pilot.md`: comprehensive methods-paper-quality writeup of all real-data results. Replaces the v0.4.2 shakedown writeup.
- 30 new regression tests in `tests/test_deep_real_analysis.py` and `tests/test_sukor_sqi.py`.

### Headline real-data findings (WESAD S2, S3, n=850 windows)
- Wrist PPG vs chest ECG: MAE 14.55 bpm, bias +12.77 bpm, 95% LoA [-16, +42]. Only 30% of windows within 5 bpm of gold standard.
- HR-modality disagreement increases by 6.6 bpm under stress in S2 (Wilcoxon p = 3.5e-10).
- In-house SQI passes 100% of windows; Orphanidou passes 22%; Sukor passes 12%. Cohen's kappa between in-house and both baselines is 0.00 at the synthetic-tuned threshold.
- Motion-vs-HR-disagreement Spearman ρ = +0.30. High-motion windows have 52% higher HR-modality disagreement than low-motion.
- Recalibration helper closes substantial part of the gap: threshold 0.70 → 0.99 raises holdout κ vs Orphanidou from 0.00 to +0.22.

### Bug fixes
- `cross_modality_hr_agreement`, `three_way_sqi_agreement`, `motion_effect_analysis` now handle empty DataFrames and missing required columns cleanly (return all-NaN result with correct schema instead of crashing on `dropna(subset=...)`).

## [0.8.0]

### Full WESAD validation (n=2 -> n=15)

The real-data pilot is now a full validation against all 15 publicly-released WESAD subjects (S2-S17, with S1 and S12 absent from the standard release). 6,585 5-second windows of synchronized chest RespiBAN ECG and wrist Empatica E4 PPG across baseline (3,507), stress (1,979), and amusement (1,099) labeled states.

### Headline changes from n=2 pilot to n=15 validation
- Bland-Altman bias improved from +12.77 to +3.57 bpm. S2 and S3 were the worst-agreement subjects in the dataset.
- LoA tightened from [-16.18, +41.72] to [-23.14, +30.28] bpm. Still 53 bpm wide.
- MAE improved from 14.55 to 9.66 bpm. Pearson r between modalities improved from +0.48 to +0.70.
- Within-5-bpm fraction improved from 30% to 46%. Within-10-bpm from 49% to 66%.
- Three-way SQI: Orphanidou-Sukor agreement strengthened from kappa +0.31 to **+0.41**. The in-house SQI still disagrees with both published baselines at kappa = 0.
- **HONEST NEGATIVE FINDING**: the n=2 recalibration result (Δkappa = +0.217) does NOT replicate at n=15. The search lands on threshold 0.85, but held-out kappa stays at 0. AUROC at n=15 is 0.484 (chance). The pilot result was an n=2 artifact attributable to the unrepresentative behavior of S2 and S3.
- Per-subject heterogeneity is the new theme: stress-state mean |HR_PPG - HR_ECG| ranges from 6.75 bpm (S15) to 26.02 bpm (S11), a 4-fold spread. Direction of per-state SQI changes also varies (most subjects drop during stress; S15 rises).

### Manuscript and supplement updates
- Section 4 of paper/manuscript.md fully rewritten with n=15 numbers and per-subject heterogeneity discussion.
- Section 4.3 now reports the honest negative recalibration finding.
- Section 5.1 expanded from 4 to 5 principal findings, with per-subject heterogeneity as a dedicated finding.
- Section 5.3 limitations removed the "n=2 of 15 pilot" caveat and added a heterogeneity caveat.
- Abstract Results paragraph updated end-to-end.
- Supplement S2.3 (recalibration) and S2.5 (per-subject reliability) updated to all 15 subjects.
- Supplement S2.6 (effect sizes) updated to all 15 subjects; top-12 contrasts shown.

### Regenerated figures
- paper/figures/fig4_bland_altman.png through fig9_extended_analyses.png refreshed from n=15 outputs.
- results/extended_analysis/figure_extended.png regenerated with all 15 subjects in panels D, E, F.

### Methodology implication
A single global SQI threshold is the wrong unit of analysis on real wrist PPG. Per-subject or per-session calibration is required. This is more honest and more interesting paper material than the pilot's "just recalibrate" story.

## [0.7.1]

### Bug fixes from post-v0.7.0 audit
- `paper/supplement_extended_analyses.md`: corrected the diagnosis of the heat_index AIPW positivity violation. The cause is collinearity between `heat_index` and `temperature_c` (Pearson r = 0.997 in the synthetic cohort), not "5-covariate adjustment set is too rich for a 300-participant cohort." Including a near-perfectly collinear covariate in the propensity model pushes propensities to 0 or 1; the fix in real usage would be to drop `temperature_c` from the heat_index adjustment set.
- `paper/supplement_extended_analyses.md`: corrected the explanation of why the NN50-style RR filter gives RMSSD = 139 ms on S3. The mechanism is gap creation, not circularity. Dropping the post-jump interval leaves the kept sequence with new large diffs between non-adjacent original neighbors, which inflates RMSSD on the smaller sample.
- `scripts/run_extended_analyses.py`: updated the in-source comment on the NN50-style filter to describe its behavior accurately and flag it as a cautionary example rather than a recommended policy.
- `paper/figures_and_tables.md`: fixed three stale file references. The model leaderboard path is `results/model_leaderboard.csv`, not `results/tables/model_leaderboard.csv`. The learned-weights output is `results/tables/learned_weights.json`, not `results/tables/learned_weights_sensitivity.csv`. The architecture diagram is acknowledged as not yet generated.
- `paper/results.md`: same path fix for `learned_weights_sensitivity.csv` → `learned_weights.json`.

### Added
- `results/figures/trust_components.png`: six-panel DBTS component distributions across the 300 synthetic participants. Referenced as supplementary Figure S2.
- `results/figures/aipw_bootstrap.png`: AIPW estimates with CI distributions for the four (treatment, outcome) pairs. Referenced as supplementary Figure S3.
- `results/figures/change_points_demo.png`: demonstration of change-point detection on a synthetic firmware-drift signal. Referenced as supplementary Figure S4.
- `results/figures/reliability_diagram.png`: in-house SQI density on real WESAD data. Referenced as supplementary Figure S1.

### Verification
All paper file references resolve except `results/figures/architecture_diagram.png` which is acknowledged as not yet generated. Tests still pass 202 / 202. Em-dash count: zero across all source and docs. Vendor mention count: zero. Emoji count: zero.

## [0.7.0]

### Reviewer-grade extended analyses (top-tier journal readiness)

This release adds six reviewer-grade extended analyses that preempt questions a careful peer reviewer at npj Digital Medicine / Lancet Digital Health would ask. Every quantitative claim in the new supplement (`paper/supplement_extended_analyses.md`) is verified against a freshly-computed CSV.

### Added
- `scripts/run_extended_analyses.py` (578 LOC) implementing six reviewer-grade analyses: AIPW positivity check with Kish ESS, E-value sensitivity to unmeasured confounding (VanderWeele & Ding 2017 with Chinn 2000 RR conversion), multi-operating-point recalibration with 200-resample bootstrap CIs on AUROC, Youden's J, and F1-maximizing thresholds, RR-cleaning robustness sweep across five policies (raw, plausibility, Malik 25%, Malik 10%, NN50), per-subject within-baseline split-half HR reliability on real WESAD data, and per-state effect sizes with both Cliff's δ (bootstrap CI) and Cohen's d.
- `paper/supplement_extended_analyses.md`: full supplementary section S2 with six subsections, summary table, and figure caption.
- `results/extended_analysis/figure_extended.png`: six-panel reviewer-grade figure.
- `tests/test_extended_analyses.py`: 14 regression tests for the extended-analysis module.

### Findings surfaced by the extended analyses
- **AIPW positivity violation on heat_index treatments**: estimated propensities span 10⁻²⁴ to 1.0, with 93.4% of observations outside [0.05, 0.95] clip. Kish's ESS drops to 62.9% of nominal. The heat_index AIPW point estimates are positivity-limited and now flagged as illustrative rather than as quantitative causal claims.
- **active_minutes positivity is clean**: 0% outside clip, Kish ESS 98.5%. The -0.497 [-0.797, -0.137] active_minutes → HRV finding is the AIPW result that should anchor the methods-paper claim.
- **E-value for active_minutes → HRV**: 2.52 (point), 1.52 (CI bound). Modest robustness to unmeasured confounding.
- **Recalibrated threshold is stable**: AUROC = 0.703 [0.659, 0.736] (200-resample bootstrap), Youden's J threshold = 0.9915 [0.9857, 0.9924]. The recalibration result in Section 4.3 is not an artifact of the particular calibration/holdout split.
- **S3's high HRV holds across RR-cleaning policies**: 121 ms (raw) → 117 ms (Malik 25%, our default). Pan-Tompkins-style detector independently gives 115.6 ms. Not a detector artifact.
- **Real-data within-baseline split-half HR reliability is substantially weaker than synthetic week-pair**: r = +0.078 (S2), +0.112 (S3) vs synthetic +0.977. Different units of analysis (5-second-window vs daily-aggregate); both are now documented honestly in the limitations section.
- **Cohen's d confirms the Cliff's δ effect-size story**: S3 amusement has Cliff's δ = ±0.49 and Cohen's d = ±0.80, both large effects on their respective conventions.

### Manuscript updates
- Section 2.4 (Methods, Reliability): added documentation of the two-stage RR-cleaning policy (plausibility filter 0.4-1.5 s, Malik 25% per Task Force 1996) with reference to robustness sweep in S2.4.
- Section 3.5 (Results, Confounding): added positivity and E-value paragraph distinguishing the active_minutes finding (clean, defensible) from the heat_index findings (positivity-limited, illustrative).
- Section 4.3 (Results, Recalibration): added threshold-stability paragraph with AUROC bootstrap CI and threshold-selection-rule comparison.
- Section 5.3 (Discussion, Limitations): added paragraph distinguishing synthetic week-pair reliability from real-data within-session reliability to preempt the apparent contradiction.

### Test count
- 202 tests passing (up from 188), zero failures, one skip (test_api.py needs FastAPI).

### Reproducibility
The full pipeline plus extended analyses runs in ~3 minutes (synthetic) + ~50 seconds (WESAD pilot) + ~30 seconds (extended analyses). Every number in `paper/manuscript.md` and `paper/supplement_extended_analyses.md` is verified against a CSV in `results/`.

## [0.6.1]

### Full upgrade run with verified manuscript numbers

Every quantitative claim in `paper/manuscript.md` is now verified against a freshly-computed CSV output produced by running the full pipeline from scratch in this release. 35 of 35 claims verified, no placeholders remain.

### Pipeline run summary
- Full synthetic pipeline rebuilt in 128 seconds (cohort generation, signal audit, baseline training, report generation, cross-cohort sweep).
- Full WESAD real-data pipeline rebuilt in 52 seconds (per-window SQI + Orphanidou baseline, deep statistical analysis, three-baseline comparison with Sukor 2011, recalibration on held-out split, six publication figures).
- 188 / 188 tests passing.

### Manuscript updates
- `paper/manuscript.md` rewritten with every number replaced by the fresh CSV value.
- New AIPW finding: active_minutes → hrv_rmssd screening r = -0.019 sharpens to -0.497 [-0.797, -0.137] under back-door adjustment (CI excludes zero). The pattern wearable papers should worry about: weak screening correlations becoming statistically significant under causal adjustment.
- Per-subject × per-state HR agreement table added for WESAD (Section 4.1). S3 amusement is the worst case at MAE 33.12 bpm with bias +33.06 bpm.
- WESAD baseline-vs-amusement extended state-contrast table added (Section 4.5). S3 PPG SQI drops at p = 1.9e-10 with Cliff's δ = -0.49 during amusement; S2 Orphanidou template correlation drops at p = 2.5e-5.

### Verification
A standalone verification script confirms every quantitative claim in the manuscript matches the corresponding CSV at full precision (DBTS 74.11, week-pair r for HR +0.977 [+0.973, +0.980], device A-C gap -13.02, skin Q4-Q1 gap -9.53, Bland-Altman bias +12.77 with LoA spanning 57.90 bpm, three-way SQI agreement, held-out recalibration κ +0.217, all per-state effect sizes and p-values).

## [0.6.0]

### Paper: upgraded to top-tier journal-format draft
- `paper/manuscript.md`: full IMRaD-format manuscript (~3000 words) suitable for npj Digital Medicine / Lancet Digital Health / Nature Digital Medicine submission. Six numbered sections plus structured abstract, plain-language summary, code-and-data availability, author contributions, competing interests, references, and supplementary materials index.
- `paper/abstract.md`: rewritten as structured abstract (background, objective, methods, results, conclusions) with quantitative claims throughout.
- `paper/paper.md`: refreshed JOSS-format short paper to include real-data validation results and the three-baseline comparison.
- `paper/figures_and_tables.md`: canonical index of every figure and table referenced in the manuscript, with file locations, generation scripts, and ready-to-use captions.
- `paper/paper.bib`: added Schmidt 2018 (WESAD), Föll 2021 (FLIRT), Mertes 2022 (AppleWatch literature review), Efron & Tibshirani 1993 (bootstrap), Malik 1996 (HRV Task Force standards).

### Figures
- `results/figures/synthetic_headline.png`: four-panel headline figure for the synthetic cohort (DBTS distribution, week-pair test-retest with CIs, fairness disparities, screening vs AIPW comparison).
- `results/figures/cross_cohort_predictions.png`: three-panel cross-cohort generalization figure showing confounding strength scaling with injected coefficient, skin-tone sign-flip under inversion, and 7/8 prediction pass count.

### Paper structure (top-tier readiness)
The paper directory now provides four levels of writeup at different lengths:
1. `paper/abstract.md`: structured abstract + plain-language summary.
2. `paper/paper.md`: short JOSS-format draft (~1800 words).
3. `paper/manuscript.md`: full journal-format manuscript (~3000 words) with six sections and ~10 tables.
4. `paper/{methods, model_card, data_card, ethics, limitations, real_data_pilot, results, reviewer_response_simulation, signal_quality_framework}.md`: extended supplements.

## [0.5.1]

### Real-data validation: deep WESAD pilot (S2 + S3)
- Bland-Altman wrist E4 PPG vs chest RespiBAN ECG: bias +12.77 bpm, LoA [-16.18, +41.72], only 30% of windows within 5 bpm.
- Three-way SQI comparison (in-house vs Orphanidou 2015 vs Sukor 2011): in-house passes 100% at default threshold, Orphanidou 22%, Sukor 12%. Orphanidou ↔ Sukor κ = +0.31 (moderate agreement). In-house ↔ either baseline κ = 0.00. The in-house SQI is the outlier.
- Motion artifact predicts HR-modality disagreement on real data (Spearman +0.30; mean |HR diff| 12.9 bpm low motion vs 19.6 bpm high motion).
- Recalibration with a 425/425 train/holdout split raises Cohen's κ vs Orphanidou from 0.000 (default threshold 0.70) to +0.217 (recalibrated threshold 0.99) on held-out data.
- Within-subject state-contrast tests find S2's Orphanidou template correlation drops from 0.82 (baseline) to 0.66 (stress) at p = 3.4e-14, a clean signal that the published baseline reacts to state-induced quality degradation that the in-house binary thresholding misses.

### Added
- `paper/real_data_pilot.md` (10-section publication-format writeup of the WESAD pilot).
- `src/signals/sukor_sqi.py` (Sukor 2011 PPG SQI as a second published baseline).
- `src/evaluation/deep_real_analysis.py` (Bland-Altman, cross-modality HR agreement, three-way SQI comparison, motion-effect analysis, threshold recalibration with held-out evaluation).
- `scripts/run_deep_real_analysis.py` (end-to-end deep analysis driver, ~25 seconds wall-clock on the two-subject pilot).
- Six publication figures under `results/real_data/wesad_deep/figures/`: Bland-Altman with state coloring, HR scatter, three-way SQI pass-rate bar chart, per-state distributions panel, motion-vs-HR-error scatter with linear fit, recalibration curve.
- `tests/test_sukor_sqi.py` and `tests/test_deep_real_analysis.py` (26 new regression tests).

### Fixed
- HRV RMSSD inflation on real ECG due to occasional R-peak misdetections producing doubled RR intervals. Now applies standard two-stage RR cleaning: plausibility filter (0.4-1.5 s) plus drop intervals more than 25% from the running median (Malik 1996). Verified against Pan-Tompkins-style detector on the same subjects: HR and RMSSD agree to within 1 bpm and 1 ms.
- Duplicate `window_idx` column when concatenating per-window SQI with windows-meta DataFrame; the duplicate caused per-state aggregates to report row counts where the ECG SQI mean should have been.

## [0.4.4]

### Added
- `paper/real_data_pilot.md`: real-data validation results from the WESAD dataset (subjects S2 and S3), covering 850 5-second windows across baseline, stress, and amusement states.

### Fixed
- `scripts/run_real_data_pilot.py`: duplicate `window_idx` column when concatenating per-window SQI output with the windows-meta DataFrame; the duplicate caused the `sqi_by_state` aggregate to report row counts where the ECG SQI mean should have been.
- `src/data/wesad_adapter.py`: HRV RMSSD was inflated by ~50-100% on real ECG due to occasional R-peak misdetections. Now applies the standard two-stage RR cleaning (plausibility filter 0.4-1.5 s, then drop intervals more than 25% from the running median per Malik 1996). S2 RMSSD dropped from 127 ms to 60 ms after the fix.

### Real-data finding
On real WESAD wrist PPG, the in-house SQI and the Orphanidou (2015) baseline agree at Spearman ρ = 0.27 (vs 0.78 on the synthetic cohort). The in-house SQI passes 98.6% of windows; Orphanidou passes 22.4%. The thresholds tuned on synthetic data are too permissive for real wrist PPG and should be recalibrated against either Orphanidou or hand-labeled windows before any real-world claim. The framework's `recalibrate_detector` helper exists for this case.

## [0.4.3]

### Added
- GitHub Actions CI workflows (`tests.yml` for the test matrix on Python 3.10/3.11/3.12 plus a pipeline smoke-test job; `lint.yml` for ruff and the em-dash gate).
- Issue templates (bug report, feature request) and pull-request template under `.github/`.
- `CONTRIBUTING.md` documenting the test runners, style conventions, and the contract for adding new artifact detectors and real-data adapters.
- `CHANGELOG.md` consolidating every release back to v0.1.0.
- `Makefile` with help, install, test, lint, pipeline, audit, train, report, cross-cohort, dashboard, api, clean, check-em-dashes, verify, and all targets.
- `.gitkeep` markers for `data/synthetic/`, `data/processed/`, `data/raw/`, `results/figures/`, `results/tables/`, `results/reports/`, `results/real_data/` so the directory structure survives a fresh git clone.
- README badges (tests, lint, Python version, license) and a quick-links bar above the fold.

### Changed
- Final humanization pass on `CONTRIBUTING.md` and the v0.4.2 release notes (zero em-dashes, zero vendor mentions across all `.md` and `.py` files; only intentional em-dash is the regex pattern in `.github/workflows/lint.yml`).

## [0.4.2]

### Added
- `paper/results.md`: 10-section consolidated results document with every empirical finding (DBTS distribution, fairness disparities, AIPW-adjusted confounding, learned weights, bootstrap test-retest, ICC-vs-test-retest comparison, Orphanidou agreement, cross-cohort generalization).
- `src/data/wesad_adapter.py`: WESAD dataset adapter (Schmidt et al. 2018) producing the canonical daily-summary schema plus ECG/PPG window arrays.
- `scripts/run_real_data_pilot.py`: driver script that runs the audit pipeline against a downloaded WESAD copy.
- 10 regression tests in `tests/test_wesad_adapter.py` exercising the WESAD adapter end-to-end on a synthetic fixture.

### Changed
- Humanization pass: removed 13 lingering instances of "deliberately" / "on purpose" / "by design" as design-choice flags; trimmed "framework" overuse in `paper/ethics.md` from 11 to 5; updated `paper/reviewer_response_simulation.md` to reflect the now-shipped Orphanidou comparison.
- `paper/results.md` Section 7 documents the formal empirical defense of the unconventional ICC(2,1) days-as-raters convention.

## [0.4.1]

### Fixed
- `evaluation/cross_cohort_check.predicted_vs_observed` no longer crashes with `KeyError: 'regime'` on an empty DataFrame.
- `evaluation/cross_cohort_check._generate_regime` refuses non-finite coefficients up front instead of silently producing an all-NaN cohort.
- Report generator now surfaces the ICC method comparison as its own section (the CSV was being written but not displayed).

### Added
- 11 regression tests in `tests/test_bug_audit_round5.py`.

## [0.4.0]

### Added
- `src/evaluation/cross_cohort_check.py`: stress-test the audit on five synthetic regimes (default, strong environment, inverted skin tone, severe device bias, clean world) and verify 8 qualitative predictions about how the framework should respond.
- `scripts/run_cross_cohort_check.py`: runnable entry point that produces `results/tables/cross_cohort_regimes.csv` and `cross_cohort_predictions.csv`.
- `src/reliability/intraclass_correlation.compare_to_test_retest`: empirical method comparison between the unconventional ICC(2,1) and the bootstrap week-pair correlation.

### Changed
- PyTorch autoencoder demoted from headline leaderboard to opt-in extension point. `scripts/train_quality_model.py --include-extensions` opts back in.
- `paper/model_card.md` now distinguishes "baselines (the contribution side)" from "extension points (not the contribution)".

## [0.3.2]

### Fixed (round 4: deep file-by-file audit)
- Motion artifact detector: severity and flag could disagree on barely-crossed thresholds; the amplitude-variance metric was unit-sensitive (now range-normalized).
- Sensor dropout detector: docstring claimed NaN handling but the mask only caught zeros (now `~np.isfinite | abs <= tol`).
- `expected_calibration_error` and `reliability_curve`: predictions at exactly `p == 1.0` were silently dropped by digitize off-by-one.
- `perturbation_stability` was non-reproducible (used global RNG state); now takes a `seed` argument.
- `train_baselines` crashed on single-class targets; now returns NaN rows with an explanatory note.
- `drift_slope` propagated NaN through `linregress`; now strips NaN before fitting.
- `per_column_bias` crashed on empty device sets; reference-device collision now raises clearly.
- DotDict `__getattr__` had a side-effect mutation; now read-only.
- `per_window_sqi`, `daily_signal_quality`, `add_derived_columns`, `add_rolling_features`, `confounding_scatter`, `trust_radar` all gained missing-column / empty-input guards.
- API `Optional[float]` for scores that can be NaN; `_none_if_nan` helper at the JSON boundary.
- AIPW `_point` handles empty treatment arms cleanly.

### Added
- 24 regression tests in `tests/test_bug_audit_round4.py`.

## [0.3.1]

### Fixed (round 3: v0.3.0 surface probing)
- Orphanidou SQI: empty / too-short / all-NaN windows crashed inside scipy's `filtfilt`; now guarded.
- `head_to_head` length mismatch crashed inside numpy broadcasting; now truncates with a logged warning.
- Report generator's Orphanidou section crashed with bare `KeyError` on malformed CSV; now falls back to a clear "not yet computed" message.
- `synthetic_signal_generator` module-level constants moved above the function that uses them.

### Added
- 10 regression tests in `tests/test_bug_audit_round3.py`.

## [0.3.0]

### Added
- `src/signals/orphanidou_sqi.py`: faithful implementation of Orphanidou et al. (IEEE JBHI 2015) template-matching SQI as a published-baseline comparison.
- `src/reliability/test_retest.py` (rewritten): proper bootstrap week-pair test-retest reliability with cluster bootstrap CIs.
- `src/data/generator_stress_test.py`: parameter sweep over the synthetic generator to confirm the audit responds in the predicted direction when each effect is amplified or removed.
- `paper/paper.md`, `paper/paper.bib`, `CITATION.cff`: JOSS-format paper draft plus citation metadata.
- Audit pipeline now writes `baseline_comparison_orphanidou.csv` and `test_retest_bootstrap.csv`.
- Report generator surfaces both the Orphanidou comparison and the bootstrap test-retest results.

### Changed
- Generator coefficients (`HEAT_HRV_COEF`, `SKIN_TONE_PPG_PENALTY`, `DEVICE_B_HR_OFFSET`, `DEVICE_C_HR_OFFSET`) exposed at module level for reproducible perturbation studies.

### Result on bundled cohort
- Orphanidou agreement: Spearman ρ = 0.782 across 1800 windows.

## [0.2.4]

### Fixed (round 2)
- AIPW with multi-level non-numeric treatments raised a clear `ValueError`; binary string treatments (`["control", "treated"]`) now work.
- Real-data adapter handles source/target column collisions by dropping the pre-existing canonical column with a warning.
- DAG `back_door_adjustment_set` raises on treatment == outcome instead of silently returning the common-cause set.
- `learn_weights` returns NaN with a clear notes string instead of leaking the `-2.0` sentinel value on too-small cohorts.
- Device bias returns NaN when HR is all-NaN, regardless of how many device families are present.

### Added
- 10 regression tests in `tests/test_bug_audit_round2.py`.

## [0.2.3]

### Changed
- Humanization pass 2: removed 12 instances of "deliberately X" / "intentionally Y" as design-choice flags; cut "research-grade" / "production-grade" boosters; rewrote the README opening to a plainer voice; varied sentence rhythm in the abstract.

## [0.2.2]

### Changed
- Humanization pass 1: zero em-dashes anywhere in the codebase (16 in README, 18 across the rest); converted definition bullets to colon form; removed "Research-grade" booster from API description.

## [0.2.1]

### Fixed (round 1: API edge-case sweep)
- All-NaN inputs return `category="insufficient_data"` instead of `"unreliable"` with NaN score.
- Change-point detectors strip NaN before processing.
- Validation flags all-NaN required columns; adapter warns when zero source columns match.
- ICC accepts `nan_policy={"drop", "raise"}`.
- `cohort_scores` raises `ValueError` on missing `participant_id` instead of bare `KeyError`.
- Single-device cohort scored 100 on device_bias (was 75).
- Constant heat_index returned 100 on confounding_risk (was 60).
- `disparity_summary` returns empty schema-correct frame on single-stratum input.
- DAG detects cycles and raises on back-door queries.

### Added
- 11 regression tests in `tests/test_bug_audit_round1.py`.

## [0.2.0]

### Added
- Round 1 of five publication-level upgrades:
  - Bootstrap test-retest reliability module
  - Orphanidou 2015 baseline comparison (initial draft)
  - Generator stress-test module
  - Fairness audit with stratified bootstrap CIs and forest plots
  - Learned trust-score weights (Dirichlet sampling + local grid search on the 6-simplex)

## [0.1.0]

### Added
- Initial release
- Synthetic signal generator (300 participants × 60 days, 1800 short windows, 3 device families, skin-tone proxy, state-dependent missingness)
- Five window-level artifact detectors (motion, dropout, noise spikes, flatline, timestamp irregularity)
- Six-component Digital Biomarker Trust Score with YAML-configurable weights
- AIPW doubly-robust causal inference with bootstrap CIs and a wearable DAG
- Three sklearn baseline models, PyTorch autoencoder, GRU
- FastAPI service, Streamlit dashboard, automated markdown report generator

[0.5.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.5.0
[0.8.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.8.0
[0.7.1]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.7.1
[0.7.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.7.0
[0.6.1]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.6.1
[0.6.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.6.0
[0.5.1]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.5.1
[0.4.4]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.4.4
[0.4.3]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.4.3
[0.4.2]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.4.2
[0.4.1]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.4.1
[0.4.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.4.0
[0.3.2]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.3.2
[0.3.1]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.3.1
[0.3.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.3.0
[0.2.4]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.2.4
[0.2.3]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.2.3
[0.2.2]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.2.2
[0.2.1]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.2.1
[0.2.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.2.0
[0.1.0]: https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/releases/tag/v0.1.0
