"""Cross-cohort generalization check.

Generates five synthetic cohorts under different parameter regimes, runs the
audit framework on each, and reports whether the framework's outputs move
as predicted. A partial defense against the 'circular evaluation' critique
in the absence of real data.

Usage:
    python scripts/run_cross_cohort_check.py
    python scripts/run_cross_cohort_check.py --n-participants 80 --n-days 35
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.evaluation.cross_cohort_check import (
    run_cross_cohort_check, predicted_vs_observed,
)
from src.utils.logging import get_logger
from src.utils.paths import ensure_dir, resolve

log = get_logger("cross_cohort")


def main(n_participants: int = 60, n_days: int = 35) -> None:
    out_dir = ensure_dir(resolve("results/tables"))
    log.info("Running cross-cohort generalization check across %d regimes…",
             5)  # REGIMES has 5 entries
    table = run_cross_cohort_check(n_participants=n_participants, n_days=n_days)
    table.to_csv(out_dir / "cross_cohort_regimes.csv", index=False)
    log.info("Per-regime audit outputs:\n%s", table[
        ["regime", "heat_hrv_screening_r", "skin_tone_Q4_minus_Q1_sq",
         "device_B_minus_A_hr_empirical", "hrv_test_retest_r"]
    ].to_string(index=False))

    preds = predicted_vs_observed(table)
    preds.to_csv(out_dir / "cross_cohort_predictions.csv", index=False)
    passes = (preds["pass"] == True).sum()
    scored = preds["pass"].notna().sum()
    log.info("Predicted vs observed: %d / %d pass.", passes, scored)
    log.info("\n%s", preds.to_string(index=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n-participants", type=int, default=60)
    p.add_argument("--n-days", type=int, default=35)
    args = p.parse_args()
    main(n_participants=args.n_participants, n_days=args.n_days)
