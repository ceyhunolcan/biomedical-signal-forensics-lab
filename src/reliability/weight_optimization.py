"""Learn trust-score weights from data, tied to a downstream reproducibility task.

The default DBTS weights are a defensible prior. They are not learned. Anyone
who actually cares about a specific downstream task (week-over-week stability
of an HRV-based stress estimate, say) can do better by searching the weight
simplex for the weighting that maximizes correlation between DBTS and that
task's stability.

We provide:

- `weekly_reproducibility_target`: a function that produces a per-participant
  reproducibility score for a chosen metric. Default metric: HRV RMSSD,
  default measure: 1 − relative absolute difference between adjacent weeks.
- `learn_weights`: grid + random search over the 6-component simplex,
  maximizing Spearman ρ between DBTS overall and the per-participant target.
- `sensitivity_table`: how much do conclusions move when the weights change?
  Reports overall-score correlation between top-k weight settings and the
  rank stability of the participant ordering they induce.

Methodology:
- Search is on the simplex with a Dirichlet-uniform sample plus a refining
  local grid around the best point. Both phases are exposed so the search
  budget is auditable.
- The target is computed on a held-out half of the participants; weight
  fitting and validation never see the same participants.
- We never claim the learned weights generalize to a different task. The
  point is to report the dependence and let the user decide.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.reliability.biomarker_trust_score import (
    DigitalBiomarkerTrustScore, TrustComponents,
)
from src.utils.logging import get_logger

log = get_logger("weight_optimization")


COMPONENT_KEYS = (
    "signal_quality_score",
    "artifact_burden_score",
    "temporal_stability_score",
    "missingness_risk_score",
    "device_bias_score",
    "confounding_risk_score",
)

DEFAULT_WEIGHTS = {
    "signal_quality_score": 0.25,
    "artifact_burden_score": 0.20,
    "temporal_stability_score": 0.20,
    "missingness_risk_score": 0.15,
    "device_bias_score": 0.10,
    "confounding_risk_score": 0.10,
}


# ---------------------------------------------------------------------------
# Downstream reproducibility target
# ---------------------------------------------------------------------------

def weekly_reproducibility_target(df: pd.DataFrame, metric: str = "hrv_rmssd") -> pd.DataFrame:
    """Per-participant week-over-week reproducibility of `metric`.

    Score is 1 minus the median relative absolute difference between adjacent
    7-day means. Higher = more reproducible. Range roughly [0, 1].
    """
    if "participant_id" not in df.columns or metric not in df.columns:
        return pd.DataFrame(columns=["participant_id", "reproducibility"])
    df2 = df.copy()
    df2["date"] = pd.to_datetime(df2["date"])
    df2 = df2.sort_values(["participant_id", "date"])
    rows = []
    for pid, g in df2.groupby("participant_id"):
        g = g.dropna(subset=[metric])
        if len(g) < 14:
            continue
        g = g.set_index("date").resample("7D")[metric].mean().dropna()
        if len(g) < 2:
            continue
        vals = g.to_numpy()
        diffs = np.abs(np.diff(vals)) / (np.abs(vals[:-1]) + 1e-6)
        score = float(np.clip(1.0 - np.median(diffs), 0.0, 1.0))
        rows.append({"participant_id": pid, "reproducibility": score})
    if not rows:
        return pd.DataFrame(columns=["participant_id", "reproducibility"])
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Compute participant-level DBTS components once, score with arbitrary weights
# ---------------------------------------------------------------------------

def participant_components(df: pd.DataFrame,
                           scorer: DigitalBiomarkerTrustScore | None = None) -> pd.DataFrame:
    """Run the DBTS once per participant and return the six component scores."""
    scorer = scorer or DigitalBiomarkerTrustScore()
    out = scorer.cohort_scores(df)  # long-format participant-level frame
    keep = ["participant_id"] + list(COMPONENT_KEYS)
    return out[keep].copy()


def overall_from_components(components_df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Compute the overall score under a given weighting."""
    w = np.array([weights[k] for k in COMPONENT_KEYS], dtype=float)
    w = w / (w.sum() + 1e-12)
    vals = components_df[list(COMPONENT_KEYS)].to_numpy()
    return pd.Series(vals @ w, index=components_df.index, name="overall_trust_score")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@dataclass
class LearnedWeights:
    weights: dict[str, float]
    spearman_train: float
    spearman_holdout: float
    n_train: int
    n_holdout: int
    n_evaluated: int
    notes: str = ""


def _objective(weights: dict[str, float],
               components: pd.DataFrame, target: pd.DataFrame) -> float:
    overall = overall_from_components(components, weights)
    merged = components.assign(overall=overall).merge(target, on="participant_id", how="inner")
    if len(merged) < 5:
        return float("nan")
    rho, _ = spearmanr(merged["overall"], merged["reproducibility"])
    return float(rho) if rho == rho else float("nan")


def _sample_dirichlet(rng: np.random.Generator, n: int, k: int, alpha: float = 1.0) -> np.ndarray:
    return rng.dirichlet(alpha * np.ones(k), size=n)


def _local_grid(center: np.ndarray, step: float = 0.05, n_per_dim: int = 3) -> np.ndarray:
    """Build a small grid of perturbations around `center` on the simplex."""
    k = len(center)
    perturbations = np.linspace(-step, step, n_per_dim)
    out = []
    for dim in range(k):
        for d in perturbations:
            if abs(d) < 1e-12:
                continue
            cand = center.copy()
            cand[dim] = max(0.0, cand[dim] + d)
            s = cand.sum()
            if s > 0:
                cand = cand / s
                out.append(cand)
    return np.array(out) if out else np.empty((0, k))


def learn_weights(df: pd.DataFrame,
                  target_metric: str = "hrv_rmssd",
                  n_random: int = 400,
                  n_refine: int = 6,
                  holdout_fraction: float = 0.3,
                  seed: int = 0,
                  min_train_participants: int = 5) -> LearnedWeights:
    """Search the 6-simplex for weights that maximize Spearman ρ vs reproducibility.

    Returns LearnedWeights with NaN ρ values (and default weights) if the cohort
    has fewer than `min_train_participants` participants with a computable
    reproducibility target, or if the bootstrap never produces a finite Spearman.
    """
    if "participant_id" not in df.columns:
        raise KeyError("participant_id column required")
    components = participant_components(df)
    target = weekly_reproducibility_target(df, metric=target_metric)
    rng = np.random.default_rng(seed)

    # participant-level holdout
    pids = list(components["participant_id"].unique())
    rng.shuffle(pids)
    n_h = int(round(len(pids) * holdout_fraction))
    holdout = set(pids[:n_h])
    train = set(pids[n_h:])
    comp_tr = components[components["participant_id"].isin(train)].reset_index(drop=True)
    comp_ho = components[components["participant_id"].isin(holdout)].reset_index(drop=True)
    targ_tr = target[target["participant_id"].isin(train)].reset_index(drop=True)
    targ_ho = target[target["participant_id"].isin(holdout)].reset_index(drop=True)

    # Guard against cohorts that are too small for a meaningful search.
    # `_objective` requires at least 5 participants with a target value.
    n_train_with_target = int(comp_tr.merge(targ_tr, on="participant_id", how="inner").shape[0])
    if n_train_with_target < min_train_participants:
        log.warning(
            "Cohort too small for weight learning: only %d training participants "
            "have a computable %s reproducibility target (need ≥%d). Returning "
            "default weights with NaN scores.",
            n_train_with_target, target_metric, min_train_participants,
        )
        return LearnedWeights(
            weights=dict(DEFAULT_WEIGHTS),
            spearman_train=float("nan"),
            spearman_holdout=float("nan"),
            n_train=int(len(comp_tr)),
            n_holdout=int(len(comp_ho)),
            n_evaluated=0,
            notes=f"target={target_metric}, cohort too small (n_train_target={n_train_with_target})",
        )

    # Sentinel: -2.0 is below any valid Spearman in [-1, 1]. If no candidate
    # ever scores above it, the search produced nothing useful.
    SENTINEL = -2.0
    best = (SENTINEL, np.array(list(DEFAULT_WEIGHTS.values())))
    n_eval = 0

    # phase 1: random Dirichlet sampling
    samples = _sample_dirichlet(rng, n=n_random, k=len(COMPONENT_KEYS))
    for w in samples:
        wd = dict(zip(COMPONENT_KEYS, w))
        score = _objective(wd, comp_tr, targ_tr)
        n_eval += 1
        if score == score and score > best[0]:  # not NaN, beats current best
            best = (score, w)

    # phase 2: refining local grid around the best point
    for _ in range(n_refine):
        grid = _local_grid(best[1], step=0.04, n_per_dim=3)
        improved = False
        for w in grid:
            wd = dict(zip(COMPONENT_KEYS, w))
            score = _objective(wd, comp_tr, targ_tr)
            n_eval += 1
            if score == score and score > best[0]:
                best = (score, w)
                improved = True
        if not improved:
            break

    # If the sentinel was never beaten, every objective evaluation was NaN
    # (typical when there are too few overlapping participants). Don't return
    # the sentinel as a "score".
    if best[0] <= SENTINEL + 1e-9:
        log.warning(
            "Weight search found no finite objective value over %d evaluations. "
            "Returning default weights with NaN scores.", n_eval,
        )
        return LearnedWeights(
            weights=dict(DEFAULT_WEIGHTS),
            spearman_train=float("nan"),
            spearman_holdout=float("nan"),
            n_train=int(len(comp_tr)),
            n_holdout=int(len(comp_ho)),
            n_evaluated=int(n_eval),
            notes=f"target={target_metric}, no finite objective",
        )

    final_weights = dict(zip(COMPONENT_KEYS, best[1]))
    ho_score = _objective(final_weights, comp_ho, targ_ho)
    log.info(
        "Learned weights: ρ_train=%.3f, ρ_holdout=%.3f, n_eval=%d, n_train=%d, n_holdout=%d",
        best[0], ho_score, n_eval, len(comp_tr), len(comp_ho),
    )
    return LearnedWeights(
        weights={k: round(float(v), 4) for k, v in final_weights.items()},
        spearman_train=round(float(best[0]), 4),
        spearman_holdout=round(float(ho_score), 4) if ho_score == ho_score else float("nan"),
        n_train=int(len(comp_tr)),
        n_holdout=int(len(comp_ho)),
        n_evaluated=int(n_eval),
        notes=f"target={target_metric}, holdout_frac={holdout_fraction}",
    )


# ---------------------------------------------------------------------------
# Sensitivity
# ---------------------------------------------------------------------------

def sensitivity_table(df: pd.DataFrame,
                      learned: LearnedWeights,
                      perturbations: list[float] | None = None) -> pd.DataFrame:
    """How sensitive is the participant ranking to small weight changes?

    For each perturbation magnitude p, draw Dirichlet noise of scale p around
    the learned weights, recompute the overall score, and report the Spearman
    rank correlation with the original ordering.
    """
    if perturbations is None:
        perturbations = [0.02, 0.05, 0.10, 0.20]
    components = participant_components(df)
    base_w = np.array([learned.weights[k] for k in COMPONENT_KEYS])
    base_overall = overall_from_components(components, learned.weights)
    rng = np.random.default_rng(0)
    rows = []
    for p in perturbations:
        rhos = []
        for _ in range(50):
            noise = rng.dirichlet(np.ones(len(COMPONENT_KEYS))) - 1.0 / len(COMPONENT_KEYS)
            perturbed = np.clip(base_w + p * noise, 0.001, None)
            perturbed = perturbed / perturbed.sum()
            wd = dict(zip(COMPONENT_KEYS, perturbed))
            new_overall = overall_from_components(components, wd)
            rho, _ = spearmanr(base_overall, new_overall)
            if rho == rho:
                rhos.append(float(rho))
        rows.append({
            "perturbation_magnitude": p,
            "median_rank_correlation": float(np.median(rhos)) if rhos else float("nan"),
            "min_rank_correlation": float(np.min(rhos)) if rhos else float("nan"),
            "n_resamples": len(rhos),
        })
    return pd.DataFrame(rows)
