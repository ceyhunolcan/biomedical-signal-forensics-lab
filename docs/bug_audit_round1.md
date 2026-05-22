# Bug Audit, Round 1: Findings and Fixes

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

This document captures the systematic edge-case sweep performed on v0.2 of the codebase. The methodology was adversarial: feed each public API the kinds of inputs a real user is likely to produce (empty frames, all-NaN columns, single-stratum cohorts, cyclic graphs, very short signals) and see what happens. The good news is that the structurally serious behaviors (physiological ranges, ICC numerical correctness, AIPW recovery of known effects, change-point detection on textbook step changes) were already right. The bad news is that the framework was silently returning misleading or partial answers on several common edge cases. This document inventories what was found and what was changed.

## Issues found

| # | Severity | Module | Symptom |
|---|---|---|---|
| 1 | high | `biomarker_trust_score` | All-NaN inputs returned `category="unreliable"` with `overall=NaN`. A user could read that as "your data is bad" when in fact the score was undefined. |
| 2 | high | `change_point` | `binary_segmentation` and `bocpd` did not handle NaN values in the input series; one silently returned `[]`, the other emitted change-points with `delta=NaN`. |
| 3 | high | `real_data_adapter` + `validation` | An adapter applied to a totally wrong-schema dataframe filled every canonical column with NaN and reported `validation=OK`. Validation only checked column presence and range violations; all-NaN columns slipped through. |
| 4 | medium | `intraclass_correlation` | NaN in the input matrix returned NaN with no explanation. The function's docstring said NaN was "not allowed" but didn't raise. |
| 5 | medium | `biomarker_trust_score.cohort_scores` | Crashed with a bare `KeyError: 'participant_id'` when the column was missing, while `score()` accepted the same input. Inconsistent contract. |
| 6 | medium | `biomarker_trust_score._device_bias` | A cohort with only one device family scored 75 on device bias. Should be 100 (no bias possible). |
| 7 | medium | `biomarker_trust_score._confounding_risk` | Constant heat_index returned a fixed score of 60. Should be 100 (no measurable confounding). |
| 8 | low | `weight_optimization.weekly_reproducibility_target` | Empty result returned a `(0, 0)` DataFrame instead of an empty frame with the right columns. Forces downstream callers to special-case. |
| 9 | low | `change_point.binary_segmentation` | Reported 3 spurious change-points on a slow linear drift (60 → 70 over 60 samples). Known limitation of mean-shift detectors; not a bug per se but undocumented. |
| 10 | none | `biomarker_trust_score` | Worst-possible quality and burden still produces overall ≈ 48 ("low") rather than "unreliable" (< 40). This is not a bug. It's how a weighted average works. But it is worth documenting. The framework will always show a floor effect because temporal stability, missingness, device bias, and confounding all contribute independently. |
| 11 | medium | `fairness_audit.disparity_summary` | Crashed with `KeyError: 'disparity'` when called on a single-stratum table. Should return an empty frame with the right schema. |
| 12 | medium | `causal_inference.DAG.back_door_adjustment_set` | Silently returned `[]` when the graph contained a cycle. A cycle means the back-door criterion is undefined, not "the answer is the empty set." |

## What changed

The fixes are scoped narrowly and tested with eleven new regression tests under `tests/test_bug_audit_round1.py`.

### Trust score robustness
- Each component method now returns `NaN` rather than a fixed-prior fallback (50, 60, 75) when its inputs are genuinely insufficient. The fixed-prior values were anchoring scores even when nothing meaningful was known.
- The overall score is a weighted mean over the components that are actually finite, with weights renormalized over the finite subset.
- New parameter `min_valid_components` (default 3): if fewer than this many components are finite, the overall score is NaN. We do not return a number we don't trust.
- Categories: NaN overall now maps to `category="insufficient_data"`, distinct from `"unreliable"`.
- `_device_bias` returns 100 when the input has only one device family.
- `_confounding_risk` returns 100 when one of the two variables is constant (the correlation is not measurable, so there is no detectable confounding).
- `cohort_scores` raises a clear `ValueError` when `participant_id` is missing.
- The `_explain` output lists which components were not computed, so the explanation no longer reads as if every component contributed.

### Change-point detectors
- `bocpd` and `binary_segmentation` strip NaN before processing. The caller no longer has to clean the series itself.
- `binary_segmentation` accepts an optional `detrend=True` flag that subtracts a linear trend before segmentation. This addresses the documented weakness of mean-shift detectors on slow drifts. The change-points reported by the detrended call reflect step changes that survive after the drift is removed.

### Validation and adapters
- `ValidationResult` gains an `all_nan_columns` field. `validate()` populates it.
- `validate(df).ok` is now False when any required column is entirely NaN, not just when it's missing or out of range.
- `RealDataAdapter.adapt` now logs a warning when the adapter's `column_map` matches zero source columns. This catches the "wrong adapter, wrong schema" case.

### ICC
- `icc_2_1` accepts a `nan_policy` argument. `"drop"` (default) silently drops any subject row containing a NaN. `"raise"` reproduces the strict behavior the old docstring claimed.

### Fairness audit
- `disparity_summary` returns an empty DataFrame with the schema `[component, min, max, disparity, min_stratum, max_stratum]` when there's only one stratum or no comparable components. No more KeyError.

### Causal inference DAG
- New methods `has_cycle()` and `_assert_acyclic()`. The latter is called by `back_door_adjustment_set`, which now raises `ValueError` on a cyclic graph instead of returning `[]`.

### Weight optimization
- `weekly_reproducibility_target` returns an empty DataFrame with the proper `[participant_id, reproducibility]` columns instead of `(0, 0)`.

## Cohort-level consequences

After the fixes, the bundled synthetic cohort produces:

- Mean overall trust score went from **69.3 → 74.1**. The shift is real, not a numerical artifact: within-participant device_bias is now correctly scored as 100 (a single participant only ever wears one device family), and confounding_risk is no longer artificially capped at 60 on participants whose heat_index variance is tiny.
- Category distribution: 31 high / 266 moderate / 3 low / 0 unreliable / 0 insufficient_data.
- Holdout Spearman ρ for learned weights vs. weekly HRV reproducibility went from **0.586 → 0.668**. The optimizer found cleaner signal once the components stopped lying.
- Cross-device fairness disparities are unchanged in magnitude (device_C still 13 points below device_A on signal quality). Within-participant scoring and cross-cohort fairness are correctly separated now.

## What was left alone

- The detector thresholds in `configs/artifact_detection.yaml` were hand-tuned on the synthetic generator and are not "wrong" in any general sense. The recalibration tool is the right way to adapt them to a different dataset.
- The default DBTS weights remain at the prior. The optimizer is the right way to adapt them to a specific downstream task; the prior is documented as a prior.
- The simple ECG/PPG waveform model in the synthetic generator stays simple. Replacing it with a higher-fidelity simulator is a future-work item, not a bug.
- Floor effect on the overall score (item 10) is a property of weighted averaging, not a bug. Documented in the model card.
