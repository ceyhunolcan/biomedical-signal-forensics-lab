"""Causal confounding analysis: DAG, g-computation, doubly-robust estimation.

The default `environmental_confounding.py` reports Pearson correlations. That's a
screening signal: useful, but a reviewer is right to want more before any
adjusted-effect claim. This module provides three things:

1. A minimal DAG representation (no networkx dependency) with enough structure
   to identify a valid adjustment set under the back-door criterion.
2. G-computation (standardization): fit an outcome model conditional on the
   treatment and adjustment set, then average over the empirical covariate
   distribution to get an adjusted marginal effect. Includes bootstrap CIs.
3. Doubly-robust AIPW (augmented inverse-probability weighting): combines a
   propensity model and an outcome model so that the estimate is consistent
   if either model is correct. Includes bootstrap CIs.

All of this is "first-order" causal inference. We do not handle time-varying
confounding or instrumental variables. The point is to give a defensible
adjusted effect alongside the screening correlation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------

@dataclass
class DAG:
    """A directed acyclic graph encoded as a dict of node → list of parents.

    Parents-of-X means "variables that directly cause X". This convention makes
    the back-door identification logic cleaner. Use `add_edge(parent, child)`
    if you prefer to think in arrows.
    """
    parents: dict[str, list[str]] = field(default_factory=dict)

    def nodes(self) -> set[str]:
        out: set[str] = set(self.parents.keys())
        for ps in self.parents.values():
            out.update(ps)
        return out

    def add_node(self, name: str) -> None:
        self.parents.setdefault(name, [])

    def add_edge(self, parent: str, child: str) -> None:
        self.add_node(parent)
        self.add_node(child)
        if parent not in self.parents[child]:
            self.parents[child].append(parent)

    def has_cycle(self) -> bool:
        """True if the graph has a cycle (i.e., is not actually a DAG)."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self.nodes()}

        # Build child adjacency for the DFS
        children: dict[str, list[str]] = {n: [] for n in self.nodes()}
        for child, parents in self.parents.items():
            for p in parents:
                children.setdefault(p, []).append(child)

        def visit(node: str) -> bool:
            color[node] = GRAY
            for nxt in children.get(node, []):
                if color[nxt] == GRAY:
                    return True
                if color[nxt] == WHITE and visit(nxt):
                    return True
            color[node] = BLACK
            return False

        for n in list(color):
            if color[n] == WHITE and visit(n):
                return True
        return False

    def _assert_acyclic(self) -> None:
        if self.has_cycle():
            raise ValueError(
                "Graph contains a cycle and is therefore not a DAG. "
                "Identification under the back-door criterion is undefined."
            )

    def ancestors(self, node: str) -> set[str]:
        seen: set[str] = set()
        stack = list(self.parents.get(node, []))
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.parents.get(n, []))
        return seen

    def back_door_adjustment_set(self, treatment: str, outcome: str) -> list[str]:
        """Return a valid adjustment set under a sufficient (but not always minimal)
        back-door criterion: take the ancestors of treatment that are also
        ancestors of outcome, excluding descendants of treatment.

        This is the 'all-common-causes' rule. It is conservative but always
        valid in a DAG with no unmeasured confounders among the listed nodes.

        Raises ValueError if the graph contains a cycle or if treatment == outcome.
        """
        self._assert_acyclic()
        if treatment == outcome:
            raise ValueError(
                f"treatment and outcome are the same node ({treatment!r}); "
                "back-door identification is undefined"
            )
        if treatment not in self.nodes() or outcome not in self.nodes():
            raise KeyError(f"{treatment!r} or {outcome!r} not in DAG")
        anc_t = self.ancestors(treatment) | {treatment}
        anc_y = self.ancestors(outcome) | {outcome}
        desc_t = self._descendants(treatment)
        common_causes = (anc_t & anc_y) - {treatment, outcome} - desc_t
        return sorted(common_causes)

    def _descendants(self, node: str) -> set[str]:
        # Invert: children-of-x = anyone whose parents list contains x
        children: dict[str, list[str]] = {n: [] for n in self.nodes()}
        for child, parents in self.parents.items():
            for p in parents:
                children.setdefault(p, []).append(child)
        seen: set[str] = set()
        stack = list(children.get(node, []))
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(children.get(n, []))
        return seen


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CausalEstimate:
    method: str
    treatment: str
    outcome: str
    adjustment_set: list[str]
    point_estimate: float
    ci_low: float
    ci_high: float
    n: int
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "treatment": self.treatment,
            "outcome": self.outcome,
            "adjustment_set": ",".join(self.adjustment_set),
            "point_estimate": self.point_estimate,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "n": self.n,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# G-computation
# ---------------------------------------------------------------------------

def _binarize(series: pd.Series) -> pd.Series:
    """Coerce a treatment column into a 0/1 binary indicator.

    Rules:
    - If it's already binary (≤2 unique non-null values), map the smaller to 0
      and the larger to 1. Handles strings, booleans, ints, floats.
    - For numeric multi-level: median-split.
    - For string/categorical multi-level: raise ValueError. We don't pick a
      reference level for the user; that's a study-design decision.
    """
    s = series.dropna()
    n_unique = s.nunique()
    if n_unique <= 1:
        # Constant column: callers will detect this via the subsequent
        # `nunique() < 2` check and return NaN.
        return series.astype(int, errors="ignore")
    if n_unique == 2:
        levels = sorted(s.unique())
        mapping = {levels[0]: 0, levels[1]: 1}
        return series.map(mapping).astype(float)
    # > 2 levels
    if pd.api.types.is_numeric_dtype(series):
        return (series > series.median()).astype(int)
    raise ValueError(
        f"Treatment column has {n_unique} non-numeric levels "
        f"({list(s.unique())[:5]}{'…' if n_unique > 5 else ''}). "
        "Pre-binarize against a chosen reference level before calling."
    )


def g_computation(df: pd.DataFrame, treatment: str, outcome: str,
                  adjustment_set: list[str],
                  n_bootstrap: int = 200, seed: int = 0,
                  learner: str = "linear") -> CausalEstimate:
    """Adjusted marginal effect E[Y | do(T=1)] − E[Y | do(T=0)] by standardization."""
    keep_cols = [treatment, outcome] + adjustment_set
    d = df[keep_cols].dropna().copy()
    d[treatment] = _binarize(d[treatment])
    if d[treatment].nunique() < 2:
        return CausalEstimate("g_computation", treatment, outcome, adjustment_set,
                              float("nan"), float("nan"), float("nan"), len(d),
                              notes="treatment had only one observed level")

    def _point(_d: pd.DataFrame) -> float:
        X_cols = [treatment] + adjustment_set
        X = _d[X_cols].to_numpy()
        y = _d[outcome].to_numpy()
        model = (LinearRegression() if learner == "linear"
                 else GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=0))
        model.fit(X, y)
        d1 = _d.copy(); d1[treatment] = 1
        d0 = _d.copy(); d0[treatment] = 0
        y1 = model.predict(d1[X_cols].to_numpy()).mean()
        y0 = model.predict(d0[X_cols].to_numpy()).mean()
        return float(y1 - y0)

    point = _point(d)
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, len(d), len(d))
        try:
            boot.append(_point(d.iloc[idx].reset_index(drop=True)))
        except Exception:  # noqa: BLE001
            continue
    if boot:
        lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    else:
        lo, hi = float("nan"), float("nan")
    return CausalEstimate("g_computation", treatment, outcome, adjustment_set,
                          point, lo, hi, len(d),
                          notes=f"learner={learner}, n_boot={len(boot)}")


# ---------------------------------------------------------------------------
# Doubly robust AIPW
# ---------------------------------------------------------------------------

def aipw(df: pd.DataFrame, treatment: str, outcome: str,
         adjustment_set: list[str],
         n_bootstrap: int = 200, seed: int = 0,
         learner: str = "linear",
         clip: tuple[float, float] = (0.02, 0.98)) -> CausalEstimate:
    """Augmented inverse-propensity weighted estimator.

    Consistent if either the outcome model or the propensity model is correct.
    Continuous treatments are median-binarized first; results are interpreted
    as the effect of being above vs below the cohort median.
    """
    keep_cols = [treatment, outcome] + adjustment_set
    d = df[keep_cols].dropna().copy()
    d[treatment] = _binarize(d[treatment])
    if d[treatment].nunique() < 2:
        return CausalEstimate("aipw", treatment, outcome, adjustment_set,
                              float("nan"), float("nan"), float("nan"), len(d),
                              notes="treatment had only one observed level")
    if not adjustment_set:
        # No covariates: estimator is the simple difference of means.
        # Still bootstrap for a CI so downstream code doesn't have to special-case.
        rng = np.random.default_rng(seed)
        boot = []
        diff = float(d.loc[d[treatment] == 1, outcome].mean()
                     - d.loc[d[treatment] == 0, outcome].mean())
        for _ in range(n_bootstrap):
            idx = rng.integers(0, len(d), len(d))
            bd = d.iloc[idx]
            if bd[treatment].nunique() < 2:
                continue
            boot.append(float(bd.loc[bd[treatment] == 1, outcome].mean()
                              - bd.loc[bd[treatment] == 0, outcome].mean()))
        lo = float(np.percentile(boot, 2.5)) if boot else float("nan")
        hi = float(np.percentile(boot, 97.5)) if boot else float("nan")
        return CausalEstimate("aipw", treatment, outcome, adjustment_set,
                              diff, lo, hi, len(d),
                              notes=f"empty adjustment set: difference of means, n_boot={len(boot)}")

    def _point(_d: pd.DataFrame) -> float:
        Xc = _d[adjustment_set].to_numpy()
        T = _d[treatment].to_numpy()
        Y = _d[outcome].to_numpy()

        # Need at least a few observations in each treatment arm for the
        # outcome models to fit. With fewer than 2 in either arm the
        # estimator is undefined.
        n_treated = int((T == 1).sum())
        n_control = int((T == 0).sum())
        if n_treated < 2 or n_control < 2:
            return float("nan")

        # propensity
        if learner == "linear":
            ps_model = LogisticRegression(max_iter=1000)
        else:
            ps_model = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=0)
        ps_model.fit(Xc, T)
        e = np.clip(ps_model.predict_proba(Xc)[:, 1], clip[0], clip[1])

        # outcome models (one per treatment level)
        if learner == "linear":
            mu_model = LinearRegression
            kwargs = {}
        else:
            mu_model = GradientBoostingRegressor
            kwargs = {"n_estimators": 100, "max_depth": 3, "random_state": 0}
        m1 = mu_model(**kwargs).fit(Xc[T == 1], Y[T == 1]).predict(Xc)
        m0 = mu_model(**kwargs).fit(Xc[T == 0], Y[T == 0]).predict(Xc)

        psi1 = m1 + T * (Y - m1) / e
        psi0 = m0 + (1 - T) * (Y - m0) / (1 - e)
        return float(psi1.mean() - psi0.mean())

    try:
        point = _point(d)
    except Exception as exc:  # noqa: BLE001
        return CausalEstimate("aipw", treatment, outcome, adjustment_set,
                              float("nan"), float("nan"), float("nan"), len(d),
                              notes=f"point estimate failed: {exc}")
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, len(d), len(d))
        try:
            boot.append(_point(d.iloc[idx].reset_index(drop=True)))
        except Exception:  # noqa: BLE001
            continue
    if boot:
        lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    else:
        lo, hi = float("nan"), float("nan")
    return CausalEstimate("aipw", treatment, outcome, adjustment_set,
                          point, lo, hi, len(d),
                          notes=f"learner={learner}, n_boot={len(boot)}, ps_clip={clip}")


# ---------------------------------------------------------------------------
# Default DAG for the wearable cohort
# ---------------------------------------------------------------------------

def default_wearable_dag() -> DAG:
    """Encodes the assumed causal structure of the synthetic cohort:

      age, sex          → baseline_hr, baseline_hrv
      heat_index        → sleep_efficiency, hrv_rmssd
      stress_proxy      → sleep_efficiency, hrv_rmssd, missing
      activity          → resting_hr, hrv_rmssd, ppg_motion
      device_type       → resting_hr, sqi
      skin_tone         → ppg_sqi
      sleep_efficiency  → hrv_rmssd  (mediator)

    The graph is small on purpose. Anyone applying this to a real cohort should
    write down their own DAG; this one is a starting point and a worked example.
    """
    g = DAG()
    for parent, child in [
        ("age", "baseline_hr"), ("age", "baseline_hrv"),
        ("sex", "baseline_hr"),
        ("heat_index", "sleep_efficiency"),
        ("heat_index", "hrv_rmssd"),
        ("stress_proxy", "sleep_efficiency"),
        ("stress_proxy", "hrv_rmssd"),
        ("stress_proxy", "missing_wearable_flag"),
        ("active_minutes", "resting_hr"),
        ("active_minutes", "hrv_rmssd"),
        ("active_minutes", "ppg_motion"),
        ("device_type", "resting_hr"),
        ("device_type", "signal_quality"),
        ("skin_tone", "signal_quality"),
        ("baseline_hr", "resting_hr"),
        ("baseline_hrv", "hrv_rmssd"),
        ("sleep_efficiency", "hrv_rmssd"),
        ("aqi", "sleep_efficiency"),
    ]:
        g.add_edge(parent, child)
    return g


def screening_vs_adjusted_table(df: pd.DataFrame,
                                pairs: Iterable[tuple[str, str]],
                                dag: DAG | None = None,
                                learner: str = "linear",
                                default_covariates: list[str] | None = None) -> pd.DataFrame:
    """For each (confounder, outcome) pair, report screening r AND AIPW adjusted effect.

    If the DAG yields an empty back-door set (e.g., the treatment is a root
    node), we fall back to `default_covariates` to give a useful adjusted
    estimate. This is a deliberate convenience: anyone with a real DAG should
    pass it in.
    """
    rows = []
    if dag is None:
        dag = default_wearable_dag()
    if default_covariates is None:
        default_covariates = ["stress_proxy", "active_minutes", "sleep_efficiency",
                              "aqi", "temperature_c"]
    for t, y in pairs:
        if t not in df.columns or y not in df.columns:
            continue
        sub = df[[t, y]].dropna()
        if len(sub) < 10:
            continue
        r = float(sub.corr().iloc[0, 1])
        try:
            adj = [c for c in dag.back_door_adjustment_set(t, y) if c in df.columns]
        except KeyError:
            adj = []
        if not adj:
            adj = [c for c in default_covariates if c in df.columns and c != t and c != y]
        est = aipw(df, t, y, adj, n_bootstrap=100, learner=learner)
        rows.append({
            "treatment": t, "outcome": y,
            "screening_r": round(r, 4),
            "adjustment_set": ",".join(adj),
            "aipw_estimate": round(est.point_estimate, 4) if est.point_estimate == est.point_estimate else None,
            "ci_low": round(est.ci_low, 4) if est.ci_low == est.ci_low else None,
            "ci_high": round(est.ci_high, 4) if est.ci_high == est.ci_high else None,
            "n": est.n,
        })
    return pd.DataFrame(rows)
