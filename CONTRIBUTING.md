# Contributing

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

Thanks for considering a contribution. The repository is intended as a methodological starting point for wearable-derived biomarker work; patches that improve correctness, add real-dataset adapters, or improve the auditability of any component are all welcome.

## Quick start

```bash
git clone https://github.com/<your-fork>/biomedical-signal-forensics-lab
cd biomedical-signal-forensics-lab
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_tests_minimal.py
```

If everything works you should see something like `Passed: 162 / Failed: 0 / Skipped: 1`. The skip is the FastAPI test; it needs `pytest` and `fastapi` installed.

To run the full pipeline end-to-end (about two minutes on a laptop CPU):

```bash
python scripts/run_pipeline.py
python scripts/run_signal_audit.py
python scripts/train_quality_model.py
python scripts/generate_report.py
```

Outputs land in `results/tables/`, `results/figures/`, and `results/reports/`.

## Where things live

- `src/data/`: synthetic generator, validation, preprocessing, real-data adapters (Fitbit-like, Empatica-like, WESAD)
- `src/signals/`: ECG / PPG / HRV / sleep / activity processing, signal-quality estimators, Orphanidou 2015 baseline
- `src/artifacts/`: five window-level artifact detectors with severity scores
- `src/reliability/`: DBTS scoring, test-retest, ICC, drift, device bias, fairness audit, learned weights, change-point detection
- `src/confounding/`: environmental and behavioral confounding, DAG, AIPW, missingness dynamics
- `src/evaluation/`: calibration, robustness, cross-cohort generalization, synthetic-to-real harness
- `src/models/`: three sklearn baselines plus optional PyTorch autoencoder and GRU
- `src/reports/`: figure builders and markdown report generator
- `src/api/`: FastAPI service (optional dep)
- `src/dashboard/`: Streamlit dashboard (optional dep)
- `scripts/`: runnable entry points
- `paper/`: paper drafts, model card, data card, ethics, limitations, results
- `docs/`: taxonomy, figure gallery, bug audit logs
- `configs/`: YAML configs for the cohort, signal quality, artifacts, experiments
- `tests/`: pytest test suite plus a sandbox-friendly minimal runner

## Style

A few conventions the repo follows. The CI lint workflow enforces them.

**No em-dashes.** Use periods, colons, or parentheses instead. The em-dash check is a hard CI gate; the project style is to break a long sentence into shorter ones rather than dash-join clauses.

**No vendor or model name-drops** in docstrings, comments, or markdown. The code stands on its own.

**Type hints are encouraged but not required** in new code. The existing modules are mostly typed; adding hints to old code is welcome but doesn't gate the merge.

**Keep functions small.** Most public functions in this repo are under 50 lines. A function that wants to be longer is usually a sign the work belongs in a new module.

**Logging, not print.** Use `from src.utils.logging import get_logger; log = get_logger(__name__)`. The `print` statements in `scripts/` are intentional (they're entry points), but library code should log.

**Disclaimer text is content-required, not stylistic.** The string "Research prototype only. Not medical advice, diagnosis, treatment, or a medical device." appears in user-facing outputs by design and should not be paraphrased away.

## Adding a new artifact detector

The pattern in `src/artifacts/`:

```python
from dataclasses import dataclass
import numpy as np

@dataclass
class ArtifactFinding:
    flag: int           # 0 or 1
    severity: float     # in [0, 1]
    explanation: str    # one short sentence


def detect(signal: np.ndarray, fs: int, ...) -> ArtifactFinding:
    """Document what counts as a positive flag and what units the inputs use."""
    ...
```

Then register the detector in `src/artifacts/artifact_classifier.py` and add a few test cases in `tests/test_artifact_detection.py` covering at least: a clean signal (flag=0), a clearly bad signal (flag=1, high severity), an empty signal (flag=0, no crash), and a signal full of NaN (flag=0, no crash).

## Adding a new real-data adapter

Use `src/data/wesad_adapter.py` as a template. The contract:

- `load_one_subject(path: Path) -> Recording` returns a typed object with the raw arrays and sampling rates.
- `extract_windows(rec, ...) -> (ecg_arr, ppg_arr, meta_df)` cuts non-overlapping windows and tags them by label / state.
- `to_daily_summary(rec) -> pd.DataFrame` produces one row per (participant, session-or-day) with the canonical column schema. Missing columns should be filled with NaN, not faked.
- `adapt_directory(root) -> (daily_df, ecg_arr, ppg_arr, meta_df)` walks a directory tree of subjects and returns the pooled outputs.

Add at least three tests: a happy-path test on a synthetic fixture (so the test runs without the real dataset download), a `FileNotFoundError` test, and a "no usable subjects" test on an empty directory.

## Testing

Two test runners:

- **`python scripts/run_tests_minimal.py`** runs without `pytest` installed. Used by CI's sandbox-compatible job and by the sandbox-bound development workflow. Tests that need `pytest` or optional deps (`fastapi`, `torch`, `streamlit`) skip gracefully.
- **`pytest tests/ --ignore=tests/test_api.py`** is the standard pytest invocation. The API test is excluded by default because it needs FastAPI installed.

Every fix to a bug should come with a regression test that would have failed before the fix. The `tests/test_bug_audit_round*.py` files are precedent.

## Documentation

- Public functions get a docstring with at least a one-line summary and a description of any non-obvious arguments or return values.
- Methodological choices (which estimator, why this threshold, what was left out) belong in `paper/methods.md`, `paper/limitations.md`, or `docs/signal_quality_taxonomy.md`, not buried in code comments.
- Numerical results in any doc should be reproducible from a script in `scripts/`. If a number can't be reproduced, mark it as illustrative.

## When in doubt

Open an issue first. For larger changes (new modules, schema changes, dependency additions), a short design sketch in the issue is more efficient than a surprise PR.
