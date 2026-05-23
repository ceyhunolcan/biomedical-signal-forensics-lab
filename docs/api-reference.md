# API reference

The toolkit is organised into the following modules. Click any module
to see its public functions, classes, and constants, auto-generated
from docstrings via
[mkdocstrings](https://mkdocstrings.github.io/).

If you are looking for high-level guidance instead of API specifics,
see [Getting started](getting-started.md) or
[Reproducing the paper](reproducing-paper.md).

## Signals

PPG and ECG preprocessing, along with four signal-quality baselines.

::: biomedical_signal_forensics_lab.signals
    options:
      show_submodules: true
      members_order: source

## Evaluation

WESAD real-data validation, four-way SQI agreement, Bland-Altman,
bootstrap CIs.

::: biomedical_signal_forensics_lab.evaluation
    options:
      show_submodules: true
      members_order: source

## Confounding

Back-door adjustment, AIPW doubly-robust estimation, E-values.

::: biomedical_signal_forensics_lab.confounding
    options:
      show_submodules: true
      members_order: source

## Reliability

ICC, test-retest stability, bootstrap reliability primitives.

::: biomedical_signal_forensics_lab.reliability
    options:
      show_submodules: true
      members_order: source

## Models

Downstream LF/HF biomarker classifier with LOSO cross-validation.

::: biomedical_signal_forensics_lab.models
    options:
      show_submodules: true
      members_order: source

## Reports

Publication-grade figure generation and summary JSON writers.

::: biomedical_signal_forensics_lab.reports
    options:
      show_submodules: true
      members_order: source

---

If a module above does not render, it may be because mkdocstrings could
not import it during the docs build. Common causes:

- The package is not installed in the docs environment. Run
  `pip install -e .` before `mkdocs serve`.
- A module imports a heavy optional dependency that is not in the docs
  environment. Lazy imports inside functions are recommended over
  module-level imports of optional heavy dependencies.
