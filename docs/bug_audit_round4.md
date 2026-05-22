# Bug Audit, Round 4: Deep File-by-File Read

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

This round was a file-by-file read of every Python source file under `src/` and `scripts/`, looking for issues that wouldn't surface from black-box input probing alone. The earlier three rounds caught what failed at the API surface; this one caught logic bugs that produced wrong (but plausible) outputs, missing-column crashes, non-reproducibility, and incorrect docstrings.

## Issues found

| # | Severity | Module | Symptom |
|---|---|---|---|
| A | medium | `artifacts/motion_artifacts` | Returned `flag=1, severity=0` when one threshold just barely crossed. Contradiction between flag and severity. |
| B | medium | `artifacts/motion_artifacts` | `amp_var = var(sig) / mean(abs(sig))` has units of signal magnitude, not dimensionless. The 0.5 threshold assumed unit-scale signals; broke silently on mV-scale ECG. |
| C | medium | `artifacts/sensor_dropout` | Docstring claimed "long runs of zeros / NaNs" but `np.abs(signal) <= tol` returns False for NaN. NaN-filled signals scored 0 dropout. |
| D | medium | `evaluation/metrics.expected_calibration_error` | Samples with `y_prob == 1.0` were silently dropped (digitize put them in bin n+1, loop only iterated to n-1). Empty input returned 0.0 instead of NaN. |
| E | high | `evaluation/robustness.perturbation_stability` | Used `np.random.normal` from global state. Results not reproducible across runs. |
| F | medium | `evaluation/calibration.reliability_curve` | Same digitize-overflow bug as ECE. |
| G | high | `models/anomaly_detector.train_baselines` | Crashed with unhelpful sklearn errors on single-class targets (e.g., all-high-quality data). Also missing target column raised bare KeyError. |
| H | medium | `reliability/temporal_stability.drift_slope` | NaN values silently propagated through `linregress`, returning NaN slope/p instead of fitting on the finite portion. |
| I | low | `reliability/device_bias.bias_severity` | Docstring said "max abs mean_diff / sd" but code divided by hardcoded 10.0. Docstring was lying. |
| J | medium | `reliability/device_bias.per_column_bias` | IndexError when no devices present; silent acceptance of an unknown `reference` device. |
| K | low | `utils/config.DotDict.__getattr__` | Side-effect mutation: accessing an attribute could replace the underlying dict value with a DotDict wrapper. Dead code given that `_wrap` already converts everything recursively. |
| L | low | `signals/signal_quality.per_window_sqi` | Empty input returned a DataFrame with no columns, forcing downstream code to handle the schema. |
| M | medium | `signals/signal_quality.daily_signal_quality` | Crashed with KeyError if `wearable_minutes` or `active_minutes` was missing. |
| N | medium | `api/main` and `api/schemas` | `overall_trust_score` typed as float, but the scorer can return NaN. JSON doesn't represent NaN; client-side parsing would fail. |
| O | cosmetic | `api/main` | API description still said "Research-grade" booster after we removed those elsewhere. |
| P | medium | `data/preprocessing.add_derived_columns` | Crashed on KeyError if any of `wearable_minutes`, `active_minutes`, `heat_index`, `sleep_duration` was missing. |
| Q | medium | `reports/figure_builder.trust_radar` | IndexError on `values[0]` when components dict was empty. |
| R | low | `reports/figure_builder.trust_distribution` | Worked on empty/NaN scores but emitted matplotlib warnings. Acceptable; not changed. |
| S | medium | `reports/figure_builder.confounding_scatter` | `sub.sample(...)` crashed with ValueError when all rows had NaN in either column. |
| T | none | `reports/trust_report.render` | `:.2f` formats NaN as "nan". Ugly but not a bug. Not changed. |
| U | high | `scripts/train_quality_model._baseline_metrics` | Same single-class issue as Bug G but in the script's local copy of the training logic. |
| V | medium | `confounding/causal_inference.aipw._point` | Bootstrap point estimate could crash when a subset had zero rows in one treatment arm. The loop caught it; the initial `_point(d)` call didn't. |

## Fixes

Each fix is scoped to the affected module. Headline changes:

**Motion artifact detector** (Bugs A, B). Rewrote the severity formula to be self-consistent: severity > 0 if and only if at least one rule fires. Range-normalized the amplitude-variance metric (divide by squared 95th-percentile absolute value) so the threshold is dimensionless. Docstring now explains both choices. Added NaN-input handling.

**Sensor dropout detector** (Bug C). Mask now includes `~np.isfinite(arr)`, matching the docstring.

**Calibration utilities** (Bugs D, F). `np.digitize` results are now `clip`ped to `[0, n_bins-1]` so a probability of exactly 1.0 falls into the last bin rather than spilling off the end. Empty input returns NaN.

**Robustness scorer** (Bug E). Takes a `seed` argument and uses a local `np.random.default_rng`. Same seed produces identical results.

**Baseline trainers** (Bugs G, U). Both the library function and the script's local copy now detect single-class targets, return three rows of NaN with a clear `notes` string explaining why, and skip the model fits entirely. `_prepare` raises a clear `KeyError` if the target column is missing.

**Drift slope** (Bug H). Strips NaN from input before regression. Returns NaN slope when fewer than 5 finite samples remain.

**Device bias** (Bugs I, J). Empty input returns the right schema; unknown reference raises `KeyError` with the list of valid devices; docstring rewritten to match the code (heuristic, not a standardized effect size, with documented scale).

**DotDict** (Bug K). `__getattr__` is now side-effect free. The recursion in `_wrap` already converts all nested dicts to DotDict at load time, so the lazy upgrade in `__getattr__` was dead code.

**Signal quality helpers** (Bugs L, M). `per_window_sqi` returns an empty DataFrame with the correct schema. `daily_signal_quality` skips missing source columns and returns all-NaN when both are absent.

**API schemas** (Bugs N, O). Score fields are typed as `Optional[float]` to permit None when the underlying value is NaN. New `_none_if_nan` helper applied in both endpoints. API description prose tightened.

**Preprocessing** (Bug P). Both `add_derived_columns` and `add_rolling_features` skip missing source columns silently.

**Figure builders** (Bugs Q, S). `trust_radar` returns an "empty" figure with a text label for empty components dicts. `confounding_scatter` checks for missing columns and all-NaN data before sampling.

**AIPW** (Bug V). `_point` now returns NaN cleanly when either treatment arm has fewer than 2 observations. The outer call to `_point(d)` is wrapped in try/except so the point estimate fails gracefully without aborting the bootstrap.

## Regression tests

24 new tests in `tests/test_bug_audit_round4.py`. Tests target the specific failure modes above (motion consistency, NaN dropout, ECE at p=1.0, ECE empty, perturbation reproducibility, reliability curve at p=1.0, single-class targets, drift slope NaN-stripping, bias_severity empty, per_column_bias bad reference, per_window_sqi empty schema, daily_signal_quality missing columns, preprocessing missing columns, figure builders with empty/all-NaN/missing inputs, AIPW under imbalanced bootstrap resamples).

## Cohort numbers, unchanged

After all fixes the bundled pipeline reproduces the same headline numbers as v0.3.1: mean DBTS 74.11, Orphanidou Spearman 0.782, holdout ρ 0.668. The fixes target failure modes on out-of-distribution inputs; the default cohort never hit any of these branches.

## Across four rounds

- Round 1 (28 cases probed): 11 bugs found and fixed, 11 regression tests
- Round 2 (14 cases probed): 5 bugs found and fixed, 10 regression tests
- Round 3 (16 cases probed): 4 bugs found and fixed, 10 regression tests
- Round 4 (file-by-file): 22 issues found, 17 fixed (5 were no-op cosmetic or already-acceptable behavior), 24 regression tests

Total: **37 distinct bugs fixed across 4 rounds, 55 regression tests in `test_bug_audit_round{1..4}.py`**. The cohort-level outputs (mean DBTS, fairness gaps, AIPW estimates, learned-weights holdout ρ) have remained stable from v0.2.0 onward, confirming that no fix changed the framework's behavior on the canonical input. Every fix targeted misbehavior on inputs the canonical pipeline doesn't produce.

## What's still not deeply audited

- The PyTorch autoencoder (`models/quality_autoencoder.py`) and GRU (`models/sequence_model.py`) are torch-dependent and untested in the sandbox.
- The Streamlit dashboard (`dashboard/app.py`) is streamlit-dependent and the prose is correct but the runtime interaction patterns are not tested.
- The FastAPI endpoints (`api/main.py`) require fastapi+pydantic+pytest, so `tests/test_api.py` is skipped. Logic was inspected by hand.
- Real-data adapters (`real_data_adapter.py`) work but have not been tested on actual Fitbit/Empatica exports.
