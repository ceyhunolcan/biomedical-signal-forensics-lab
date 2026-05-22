"""Generate synthetic data, validate, and preprocess.

Usage: python scripts/run_pipeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.synthetic_signal_generator import generate
from src.data.preprocessing import preprocess
from src.data.validation import validate
from src.utils.logging import get_logger

log = get_logger("pipeline")


def main() -> None:
    log.info("Step 1/3: generate synthetic cohort")
    df, _ = generate()
    log.info("Step 2/3: validate")
    result = validate(df)
    log.info("Validation: %s", result.summary())
    log.info("Step 3/3: preprocess")
    proc = preprocess()
    log.info("Pipeline done. Processed rows=%d, cols=%d", len(proc), proc.shape[1])


if __name__ == "__main__":
    main()
