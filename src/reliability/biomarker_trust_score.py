"""Digital Biomarker Trust Score (DBTS).

Six sub-scores → weighted composite in [0, 100] with a categorical label.
All weights and thresholds are loaded from configs/reliability.yaml so the
score is auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import numpy as np
import pandas as pd

from ..utils.config import load_yaml


@dataclass
class TrustComponents:
    signal_quality_score: float
    artifact_burden_score: float
    temporal_stability_score: float
    missingness_risk_score: float
    device_bias_score: float
    confounding_risk_score: float


@dataclass
class TrustReport:
    components: TrustComponents
    overall_trust_score: float
    category: str
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self.components)
        out["overall_trust_score"] = self.overall_trust_score
        out["category"] = self.category
        out["explanation"] = self.explanation
        return out


def _categorize(score: float, thresholds: dict[str, float]) -> str:
    if score != score:  # NaN
        return "insufficient_data"
    if score >= thresholds["high"]:
        return "high"
    if score >= thresholds["moderate"]:
        return "moderate"
    if score >= thresholds["low"]:
        return "low"
    return "unreliable"


class DigitalBiomarkerTrustScore:
    """Compute the trust score and its sub-components from a participant frame.

    Inputs are kept simple on purpose: a per-participant dataframe with the
    daily columns plus any computed artifact / signal quality columns. We
    derive each sub-score with a transparent rule and combine via the
    configured weights.
    """

    def __init__(self, config_path: str = "configs/reliability.yaml") -> None:
        self.cfg = load_yaml(config_path)
        self.weights: dict[str, float] = dict(self.cfg.trust_score.weights)
        self.thresholds: dict[str, float] = dict(self.cfg.trust_score.category_thresholds)

    # ---- sub-score helpers ------------------------------------------------
    @staticmethod
    def _signal_quality(df: pd.DataFrame) -> float:
        col = "signal_quality_ground_truth"
        if col in df.columns and df[col].notna().any():
            return float(np.clip(df[col].mean() * 100, 0, 100))
        # fallback: derive from wear coverage
        if "wearable_minutes" not in df.columns or df["wearable_minutes"].notna().sum() == 0:
            return float("nan")
        cov = (df["wearable_minutes"].fillna(0) / 1440.0).mean()
        return float(np.clip(cov * 100, 0, 100))

    @staticmethod
    def _artifact_burden(df: pd.DataFrame) -> float:
        col = "artifact_burden_ground_truth"
        if col in df.columns and df[col].notna().any():
            return float(np.clip((1 - df[col].mean()) * 100, 0, 100))
        return float("nan")  # no fallback - we genuinely don't know

    @staticmethod
    def _temporal_stability(df: pd.DataFrame) -> float:
        if "hrv_rmssd" not in df.columns or df["hrv_rmssd"].notna().sum() < 5:
            return float("nan")
        v = df["hrv_rmssd"].dropna().to_numpy()
        mean = float(np.mean(v))
        std = float(np.std(v))
        if mean <= 0:
            return 0.0
        cov = std / mean
        return float(np.clip(100 * (1 - min(cov, 1.0)), 0, 100))

    @staticmethod
    def _missingness_risk(df: pd.DataFrame) -> float:
        if "missing_wearable_flag" not in df.columns or df["missing_wearable_flag"].notna().sum() == 0:
            return float("nan")
        miss_rate = float(df["missing_wearable_flag"].mean())
        # also penalize consecutive missingness
        flags = df.sort_values("date")["missing_wearable_flag"].fillna(0).to_numpy()
        max_run = 0
        run = 0
        for f in flags:
            run = run + 1 if f else 0
            max_run = max(max_run, run)
        run_pen = min(max_run / 7.0, 1.0)
        return float(np.clip(100 * (1 - 0.7 * miss_rate - 0.3 * run_pen), 0, 100))

    @staticmethod
    def _device_bias(df: pd.DataFrame, cohort_means: dict[str, float] | None = None) -> float:
        if "device_type" not in df.columns:
            return float("nan")
        # If only one device family appears in the cohort, device bias is
        # undefined and we report perfect score rather than penalizing.
        n_devices = df["device_type"].dropna().nunique()
        if n_devices <= 1:
            return 100.0
        # Need HR to compute a bias estimate at all.
        if "resting_hr" not in df.columns or df["resting_hr"].notna().sum() == 0:
            return float("nan")
        # Without cohort means we can't compute a deviation, but a participant-
        # level frame with multiple devices does carry some information; return
        # NaN rather than a fixed-prior 75 so the overall score correctly
        # excludes this component.
        if cohort_means is None or "resting_hr" not in cohort_means:
            return float("nan")
        rh = df["resting_hr"].mean()
        baseline = cohort_means["resting_hr"]
        delta = abs(rh - baseline)
        return float(np.clip(100 * (1 - min(delta / 10.0, 1.0)), 0, 100))

    @staticmethod
    def _confounding_risk(df: pd.DataFrame) -> float:
        if "heat_index" not in df.columns or "hrv_rmssd" not in df.columns:
            return float("nan")
        sub = df[["heat_index", "hrv_rmssd"]].dropna()
        if len(sub) < 5:
            return float("nan")
        heat = sub["heat_index"].to_numpy()
        hrv = sub["hrv_rmssd"].to_numpy()
        if np.std(heat) < 1e-6 or np.std(hrv) < 1e-6:
            # No variation in one of the variables → no confounding can be
            # measured. Treat as 'no detectable confounding' rather than
            # a fixed-priors number.
            return 100.0
        corr = float(np.corrcoef(heat, hrv)[0, 1])
        if corr != corr:  # safety
            return 100.0
        return float(np.clip(100 * (1 - abs(corr)), 0, 100))

    # ---- public API -------------------------------------------------------
    def score(self, df: pd.DataFrame,
              cohort_means: dict[str, float] | None = None,
              min_valid_components: int = 3) -> TrustReport:
        comp = TrustComponents(
            signal_quality_score=self._signal_quality(df),
            artifact_burden_score=self._artifact_burden(df),
            temporal_stability_score=self._temporal_stability(df),
            missingness_risk_score=self._missingness_risk(df),
            device_bias_score=self._device_bias(df, cohort_means),
            confounding_risk_score=self._confounding_risk(df),
        )
        comp_dict = asdict(comp)
        # Weighted mean, ignoring NaN components and renormalizing the
        # weights of the components that are present. If too few components
        # are valid, the overall score is NaN. We don't return a number we
        # don't trust.
        valid = {k: v for k, v in comp_dict.items() if v == v}
        if len(valid) < min_valid_components:
            overall = float("nan")
        else:
            total_w = sum(self.weights.get(k, 0.0) for k in valid)
            if total_w > 0:
                overall = sum(v * self.weights.get(k, 0.0) for k, v in valid.items()) / total_w
            else:
                overall = float("nan")
        category = _categorize(overall, self.thresholds)
        explanation = self._explain(comp_dict, category)
        overall_rounded = float(round(overall, 2)) if overall == overall else float("nan")
        return TrustReport(comp, overall_rounded, category, explanation)

    @staticmethod
    def _explain(comp: dict[str, float], category: str) -> str:
        # Ignore NaN components when reporting strongest / weakest
        finite = {k: v for k, v in comp.items() if v == v}
        if not finite:
            return ("No usable inputs to estimate trust score. "
                    "Research prototype only. Not medical advice.")
        worst = min(finite.items(), key=lambda kv: kv[1])
        best = max(finite.items(), key=lambda kv: kv[1])
        nan_components = [k for k, v in comp.items() if v != v]
        nan_note = (f" Components with insufficient data: {', '.join(nan_components)}."
                    if nan_components else "")
        return (
            f"Overall category: {category}. "
            f"Strongest component: {best[0]} ({best[1]:.1f}). "
            f"Weakest component: {worst[0]} ({worst[1]:.1f}).{nan_note} "
            "Research prototype only. Not medical advice."
        )

    def cohort_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        if "participant_id" not in df.columns:
            raise ValueError(
                "cohort_scores requires a 'participant_id' column. "
                "Use score() for single-participant or unidentified data."
            )
        if "resting_hr" in df.columns and df["resting_hr"].notna().any():
            cohort_means = {"resting_hr": float(df["resting_hr"].mean())}
        else:
            cohort_means = None
        rows = []
        for pid, g in df.groupby("participant_id"):
            rep = self.score(g, cohort_means)
            row = rep.to_dict()
            row["participant_id"] = pid
            rows.append(row)
        return pd.DataFrame(rows)
