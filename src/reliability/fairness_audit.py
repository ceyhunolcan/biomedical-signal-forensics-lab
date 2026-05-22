"""Stratified fairness audit.

For any categorical column (device_type, sex, age band, a skin-tone proxy
quartile), compute the full DBTS panel within each level and emit:

- a tidy per-stratum table with all six components and the overall score;
- a per-component disparity table (max minus min across strata);
- a 'forest-plot-ready' frame with bootstrapped confidence intervals.

The plot itself is in `src/reports/figure_builder.py::fairness_forest_plot`.

This module deliberately stays domain-agnostic. It does not know what
"fair" means; it surfaces the disparities so a human can decide what to
do about them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from src.reliability.biomarker_trust_score import DigitalBiomarkerTrustScore
from src.utils.logging import get_logger

log = get_logger("fairness_audit")


@dataclass
class StratumScore:
    stratum_column: str
    stratum_value: str
    n_participants: int
    n_days: int
    overall_trust_score: float
    components: dict[str, float]
    ci_low: float
    ci_high: float


def _bootstrap_overall(df: pd.DataFrame, scorer: DigitalBiomarkerTrustScore,
                       n_boot: int = 100, seed: int = 0) -> tuple[float, float]:
    """Cluster bootstrap by participant_id for valid CIs on the overall score."""
    if "participant_id" not in df.columns:
        return float("nan"), float("nan")
    pids = df["participant_id"].unique()
    if len(pids) < 3:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(n_boot):
        sampled = rng.choice(pids, size=len(pids), replace=True)
        boot_df = pd.concat([df[df["participant_id"] == p] for p in sampled])
        try:
            scores.append(scorer.score(boot_df).overall_trust_score)
        except Exception:  # noqa: BLE001
            continue
    if not scores:
        return float("nan"), float("nan")
    return float(np.percentile(scores, 2.5)), float(np.percentile(scores, 97.5))


def _bin_quartile(s: pd.Series) -> pd.Series:
    """Quartile-bin a numeric column. Returns labels 'Q1'..'Q4'."""
    try:
        return pd.qcut(s, q=4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
    except ValueError:
        # not enough unique values for 4 bins → fall back to rank-based 2 bins
        med = s.median()
        return pd.Series(np.where(s > med, "high", "low"), index=s.index)


def fairness_audit(df: pd.DataFrame, stratify_by: str,
                   bin_strategy: str = "auto",
                   n_bootstrap: int = 100,
                   scorer: DigitalBiomarkerTrustScore | None = None) -> pd.DataFrame:
    """Run DBTS for every level of `stratify_by`.

    Parameters
    ----------
    df
        Daily-summary frame, schema-compliant.
    stratify_by
        Column to stratify on. If numeric, will be quartile-binned (or
        median-split when there aren't enough unique values).
    bin_strategy
        'auto' (default), 'quartile', or 'none'. 'none' requires the column
        to be categorical or low-cardinality already.
    n_bootstrap
        Bootstrap resamples for the per-stratum CI. Set to 0 to skip.
    scorer
        Optional pre-built scorer (uses default config if None).
    """
    if stratify_by not in df.columns:
        raise KeyError(f"{stratify_by!r} not in dataframe")
    scorer = scorer or DigitalBiomarkerTrustScore()

    # Build the stratifier
    series = df[stratify_by]
    if pd.api.types.is_numeric_dtype(series) and bin_strategy in ("auto", "quartile"):
        strata = _bin_quartile(series)
        stratifier = strata.values
        stratify_col_label = f"{stratify_by}_quartile"
    else:
        stratifier = series.astype(str).values
        stratify_col_label = stratify_by

    df2 = df.copy()
    df2["_stratum"] = stratifier

    rows = []
    for level, sub in df2.groupby("_stratum"):
        if len(sub) < 10:
            continue
        try:
            score = scorer.score(sub)
        except Exception as exc:  # noqa: BLE001
            log.warning("scoring failed for stratum %s: %s", level, exc)
            continue
        ci_lo, ci_hi = (float("nan"), float("nan"))
        if n_bootstrap > 0:
            ci_lo, ci_hi = _bootstrap_overall(sub, scorer, n_boot=n_bootstrap)
        components = {
            "signal_quality_score": score.components.signal_quality_score,
            "artifact_burden_score": score.components.artifact_burden_score,
            "temporal_stability_score": score.components.temporal_stability_score,
            "missingness_risk_score": score.components.missingness_risk_score,
            "device_bias_score": score.components.device_bias_score,
            "confounding_risk_score": score.components.confounding_risk_score,
        }
        rows.append({
            "stratum_column": stratify_col_label,
            "stratum_value": str(level),
            "n_participants": int(sub["participant_id"].nunique())
                if "participant_id" in sub.columns else len(sub),
            "n_days": int(len(sub)),
            "overall_trust_score": round(score.overall_trust_score, 2),
            "ci_low": round(ci_lo, 2) if ci_lo == ci_lo else None,
            "ci_high": round(ci_hi, 2) if ci_hi == ci_hi else None,
            "category": score.category,
            **{k: round(v, 2) for k, v in components.items()},
        })
    out = pd.DataFrame(rows).sort_values("stratum_value").reset_index(drop=True)
    return out


def disparity_summary(stratum_table: pd.DataFrame) -> pd.DataFrame:
    """Max minus min across strata, per component. Quick read of who's worst off."""
    component_cols = [
        "overall_trust_score", "signal_quality_score", "artifact_burden_score",
        "temporal_stability_score", "missingness_risk_score",
        "device_bias_score", "confounding_risk_score",
    ]
    # Schema we always return so downstream code doesn't have to special-case
    out_cols = ["component", "min", "max", "disparity", "min_stratum", "max_stratum"]
    if stratum_table is None or stratum_table.empty or len(stratum_table) < 2:
        return pd.DataFrame(columns=out_cols)
    rows = []
    for c in component_cols:
        if c not in stratum_table.columns:
            continue
        vals = stratum_table[c].dropna()
        if len(vals) < 2:
            continue
        rows.append({
            "component": c,
            "min": float(vals.min()),
            "max": float(vals.max()),
            "disparity": float(vals.max() - vals.min()),
            "min_stratum": stratum_table.loc[stratum_table[c].idxmin(), "stratum_value"],
            "max_stratum": stratum_table.loc[stratum_table[c].idxmax(), "stratum_value"],
        })
    if not rows:
        return pd.DataFrame(columns=out_cols)
    return pd.DataFrame(rows).sort_values("disparity", ascending=False).reset_index(drop=True)


def multi_stratify(df: pd.DataFrame, stratify_columns: Iterable[str],
                   **kwargs) -> dict[str, pd.DataFrame]:
    """Run the audit across multiple stratifiers; return a dict keyed by column."""
    out = {}
    for col in stratify_columns:
        try:
            out[col] = fairness_audit(df, stratify_by=col, **kwargs)
        except Exception as exc:  # noqa: BLE001
            log.warning("fairness audit failed for %s: %s", col, exc)
    return out
