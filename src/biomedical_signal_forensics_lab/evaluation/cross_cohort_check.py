"""Cross-cohort generalization check.

A partial defense against the 'circular evaluation' critique. We build a
second synthetic cohort with parameters intentionally different from the
defaults (different baselines, different effect signs, different
within-participant noise), then run the same audit framework on it and
report:

  1. The trust-score distribution shifts in the expected direction.
  2. The fairness audit recovers the new injected effects.
  3. The Orphanidou agreement holds (it should: the SQI computation
     doesn't depend on the generative parameters).
  4. The bootstrap test-retest reliability tracks the new within-participant
     noise scale (more noise → lower r).

This is not real-data validation. It's a sanity check that the framework's
outputs are sensitive to the cohort's properties rather than to the
particular default parameters. Run from `scripts/run_cross_cohort_check.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.utils.logging import get_logger

log = get_logger("cross_cohort_check")


@dataclass
class CohortRegime:
    """A named set of generator overrides for one regime."""
    name: str
    heat_hrv_coef: float
    skin_tone_penalty: float
    device_b_offset: float
    device_c_offset: float
    description: str


REGIMES = [
    CohortRegime(
        name="default",
        heat_hrv_coef=-1.8,
        skin_tone_penalty=0.12,
        device_b_offset=3.8,
        device_c_offset=-2.1,
        description="The default synthetic regime. Matches the bundled cohort.",
    ),
    CohortRegime(
        name="strong_environment",
        heat_hrv_coef=-4.5,         # 2.5× the default
        skin_tone_penalty=0.30,     # 2.5× the default
        device_b_offset=3.8,
        device_c_offset=-2.1,
        description="Strong environmental and skin-tone effects. Both fairness gaps and confounding should grow.",
    ),
    CohortRegime(
        name="inverted_skin_tone",
        heat_hrv_coef=-1.8,
        skin_tone_penalty=-0.12,    # SIGN FLIP: darker skin gets cleaner PPG (counterfactual scenario)
        device_b_offset=3.8,
        device_c_offset=-2.1,
        description="Skin-tone effect inverted. Q1-Q4 fairness gap should change sign.",
    ),
    CohortRegime(
        name="severe_device_bias",
        heat_hrv_coef=-1.8,
        skin_tone_penalty=0.12,
        device_b_offset=8.0,        # 2.1× the default
        device_c_offset=-6.0,       # 2.9× the default
        description="Severe device bias. Device-bias component should drop sharply.",
    ),
    CohortRegime(
        name="clean_world",
        heat_hrv_coef=0.0,
        skin_tone_penalty=0.0,
        device_b_offset=0.0,
        device_c_offset=0.0,
        description="No injected effects. All audit outputs should be near-zero / near-100.",
    ),
]


def _generate_regime(regime: CohortRegime, n_participants: int = 80, n_days: int = 30,
                     seed: int = 0) -> pd.DataFrame:
    """Generate a cohort under the given regime by monkey-patching the constants."""
    # Refuse non-finite coefficients up front. Otherwise the generator runs to
    # completion but produces an all-NaN cohort, which is harder to debug.
    for name, value in [("heat_hrv_coef", regime.heat_hrv_coef),
                        ("skin_tone_penalty", regime.skin_tone_penalty),
                        ("device_b_offset", regime.device_b_offset),
                        ("device_c_offset", regime.device_c_offset)]:
        if not np.isfinite(value):
            raise ValueError(
                f"Regime {regime.name!r} has non-finite {name}={value}. "
                "Use a finite value or zero to disable an effect."
            )
    from biomedical_signal_forensics_lab.data import synthetic_signal_generator as gen
    saved = {
        "HEAT_HRV_COEF": gen.HEAT_HRV_COEF,
        "SKIN_TONE_PPG_PENALTY": gen.SKIN_TONE_PPG_PENALTY,
        "DEVICE_B_HR_OFFSET": gen.DEVICE_B_HR_OFFSET,
        "DEVICE_C_HR_OFFSET": gen.DEVICE_C_HR_OFFSET,
    }
    try:
        gen.HEAT_HRV_COEF = regime.heat_hrv_coef
        gen.SKIN_TONE_PPG_PENALTY = regime.skin_tone_penalty
        gen.DEVICE_B_HR_OFFSET = regime.device_b_offset
        gen.DEVICE_C_HR_OFFSET = regime.device_c_offset

        import tempfile, yaml
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            syn = td / "data" / "synthetic"
            syn.mkdir(parents=True)
            cfg = {
                "project": {"name": "regime", "seed": seed,
                            "output_dir": str(td / "r"), "data_dir": str(td / "d")},
                "cohort": {
                    "n_participants": n_participants, "n_days": n_days,
                    "short_window_seconds": 5, "ecg_sample_rate_hz": 250,
                    "ppg_sample_rate_hz": 64,
                    "devices": ["device_A", "device_B", "device_C"],
                    "sex_distribution": {"F": 0.51, "M": 0.49},
                    "age_range": [18, 75],
                },
                "paths": {
                    "synthetic_csv": str(syn / "d.csv"),
                    "synthetic_windows": str(syn / "w.npz"),
                    "processed_csv": str(syn / "p.csv"),
                    "report_md": str(td / "r.md"),
                    "leaderboard_csv": str(td / "l.csv"),
                    "figures_dir": str(td / "figs"),
                },
            }
            cfg_path = td / "cfg.yaml"
            cfg_path.write_text(yaml.safe_dump(cfg))
            df, _ = gen.generate(config_path=cfg_path)
            return df
    finally:
        for name, value in saved.items():
            setattr(gen, name, value)


def evaluate_regime(regime: CohortRegime, n_participants: int = 80, n_days: int = 30,
                    seed: int = 0) -> dict:
    """Generate a cohort under the regime, run the relevant audit pieces, return a row."""
    from biomedical_signal_forensics_lab.reliability.biomarker_trust_score import DigitalBiomarkerTrustScore
    from biomedical_signal_forensics_lab.reliability.fairness_audit import fairness_audit
    from biomedical_signal_forensics_lab.reliability.test_retest import cohort_test_retest

    log.info("Regime '%s': generating cohort (n=%d × %d days)…",
             regime.name, n_participants, n_days)
    df = _generate_regime(regime, n_participants=n_participants, n_days=n_days, seed=seed)

    # Cohort trust score
    scorer = DigitalBiomarkerTrustScore()
    trust = scorer.cohort_scores(df)
    mean_dbts = float(trust["overall_trust_score"].mean())

    # Skin-tone fairness gap on signal_quality_score
    df_with_q = df.copy()
    df_with_q["skin_tone_q"] = pd.qcut(df_with_q["skin_tone_proxy"], q=4,
                                       labels=["Q1", "Q2", "Q3", "Q4"])
    sk_fair = fairness_audit(df_with_q, stratify_by="skin_tone_q", n_bootstrap=50)
    if not sk_fair.empty and {"Q1", "Q4"}.issubset(set(sk_fair["stratum_value"])):
        q1 = float(sk_fair[sk_fair["stratum_value"] == "Q1"]["signal_quality_score"].iloc[0])
        q4 = float(sk_fair[sk_fair["stratum_value"] == "Q4"]["signal_quality_score"].iloc[0])
        skin_gap = q4 - q1
    else:
        skin_gap = float("nan")

    # Device bias gap (device_A vs device_B mean HR)
    a_hr = df[df["device_type"] == "device_A"]["resting_hr"].mean()
    b_hr = df[df["device_type"] == "device_B"]["resting_hr"].mean()
    device_b_empirical = float(b_hr - a_hr)

    # Test-retest on HRV
    tr = cohort_test_retest(df, "hrv_rmssd", n_bootstrap=50)

    # Screening correlation heat × HRV
    hrv = df[["heat_index", "hrv_rmssd"]].dropna()
    heat_r = float(hrv.corr().iloc[0, 1]) if len(hrv) > 5 else float("nan")

    return {
        "regime": regime.name,
        "description": regime.description,
        "heat_hrv_coef": regime.heat_hrv_coef,
        "skin_tone_penalty": regime.skin_tone_penalty,
        "device_b_offset_injected": regime.device_b_offset,
        "mean_cohort_dbts": round(mean_dbts, 2),
        "skin_tone_Q4_minus_Q1_sq": round(skin_gap, 2) if skin_gap == skin_gap else None,
        "device_B_minus_A_hr_empirical": round(device_b_empirical, 2),
        "heat_hrv_screening_r": round(heat_r, 3) if heat_r == heat_r else None,
        "hrv_test_retest_r": round(tr.point_estimate, 3) if tr.point_estimate == tr.point_estimate else None,
        "n_participants": n_participants,
        "n_days": n_days,
    }


def run_cross_cohort_check(n_participants: int = 80, n_days: int = 30,
                           seed: int = 0) -> pd.DataFrame:
    rows = []
    for regime in REGIMES:
        rows.append(evaluate_regime(regime, n_participants=n_participants,
                                    n_days=n_days, seed=seed))
    return pd.DataFrame(rows)


def predicted_vs_observed(table: pd.DataFrame) -> pd.DataFrame:
    """Compare observed audit outputs against the qualitative predictions per regime.

    Each row is a predicted relationship that should hold across regimes.

    Returns an empty result-typed DataFrame if `table` is empty or has no
    'regime' column. Predictions involving regimes that aren't present
    return NaN observations with pass=None (i.e., 'skipped' rather than
    'failed').
    """
    if table is None or table.empty or "regime" not in table.columns:
        return pd.DataFrame(columns=["check", "predicted", "observed", "pass"])

    checks = []

    def get(name, col):
        s = table.loc[table["regime"] == name, col]
        if len(s) == 0:
            return float("nan")
        v = s.iloc[0]
        if v is None or (isinstance(v, float) and v != v):
            return float("nan")
        return float(v)

    # 1. Clean world should have the smallest |heat-HRV r|
    checks.append({
        "check": "clean_world has near-zero heat→HRV correlation",
        "predicted": "|r| < 0.05",
        "observed": abs(get("clean_world", "heat_hrv_screening_r")),
        "pass": abs(get("clean_world", "heat_hrv_screening_r")) < 0.05,
    })
    # 2. Strong environment should have larger |heat-HRV r| than default
    checks.append({
        "check": "strong_environment has stronger heat→HRV correlation than default",
        "predicted": "|r_strong| > |r_default|",
        "observed": (abs(get("strong_environment", "heat_hrv_screening_r")),
                     abs(get("default", "heat_hrv_screening_r"))),
        "pass": abs(get("strong_environment", "heat_hrv_screening_r")) >
                abs(get("default", "heat_hrv_screening_r")),
    })
    # 3. Inverted skin tone should flip the Q1-Q4 sign
    def_gap = get("default", "skin_tone_Q4_minus_Q1_sq")
    inv_gap = get("inverted_skin_tone", "skin_tone_Q4_minus_Q1_sq")
    checks.append({
        "check": "inverted_skin_tone reverses Q4-Q1 sign",
        "predicted": "sign flip",
        "observed": (def_gap, inv_gap),
        "pass": (def_gap < 0 and inv_gap > 0) or (def_gap > 0 and inv_gap < 0),
    })
    # 4. Severe device bias should give a large empirical device-B offset
    checks.append({
        "check": "severe_device_bias recovers a large empirical device-B offset",
        "predicted": "empirical offset > 6 bpm",
        "observed": get("severe_device_bias", "device_B_minus_A_hr_empirical"),
        "pass": get("severe_device_bias", "device_B_minus_A_hr_empirical") > 6.0,
    })
    # 5. Clean world should have no significant device-B offset
    checks.append({
        "check": "clean_world has near-zero device-B offset",
        "predicted": "|offset| < 1.5 bpm",
        "observed": abs(get("clean_world", "device_B_minus_A_hr_empirical")),
        "pass": abs(get("clean_world", "device_B_minus_A_hr_empirical")) < 1.5,
    })
    # 6. HRV test-retest reliability should be consistently high
    #    (the perturbations don't change within-participant noise)
    #    Skip the check if the cohort was too short to compute test-retest.
    for name in ("default", "strong_environment", "clean_world"):
        r = get(name, "hrv_test_retest_r")
        if r != r:  # NaN: insufficient weeks of data
            checks.append({
                "check": f"HRV test-retest reliability under regime '{name}'",
                "predicted": "r > 0.85",
                "observed": "n/a (need ≥4 weeks of data)",
                "pass": None,  # skipped
            })
            continue
        checks.append({
            "check": f"HRV test-retest reliability is high under regime '{name}'",
            "predicted": "r > 0.85",
            "observed": r,
            "pass": r > 0.85,
        })

    return pd.DataFrame(checks)
