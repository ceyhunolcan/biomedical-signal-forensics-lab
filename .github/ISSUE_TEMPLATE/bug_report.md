---
name: Bug report
about: Something in the audit pipeline is producing wrong or unexpected output
title: ''
labels: bug
assignees: ''
---

**What you expected**

A short description of what you thought would happen.

**What actually happened**

What you got instead. Include the exact error message if there is one.

**How to reproduce**

Minimal code or command that reproduces the issue. If it depends on a specific data file, include enough of the schema to regenerate it (or link to the public dataset).

```python
# example
from src.reliability.biomarker_trust_score import DigitalBiomarkerTrustScore
...
```

**Environment**

- OS:
- Python version:
- Package version (`python -c "import src; print(src.__version__)"`):
- Whether you're running with the optional deps (torch / streamlit / fastapi):

**Anything else worth knowing**

For example: the cohort size, whether the input passed `validate()`, whether you've recalibrated the detectors against your data.
