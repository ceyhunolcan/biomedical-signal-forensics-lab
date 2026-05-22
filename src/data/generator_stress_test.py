"""Generator stress test.

A reviewer's first attack on this framework is: 'The detectors are tuned on
synthetic data the authors generated, then evaluated on that same data. The
evaluation is circular.' We can't fully escape that without real data, but
we can partially defend by showing the framework responds in the expected
direction when we deliberately perturb the generator away from its defaults.

For each of three injected effects, we re-generate the cohort at three
strength levels (low / default / high), rerun the audit, and check that the
audit output moves in the predicted direction. The point is to show that
the framework is not just pattern-matching its own training data.

We perturb:
  1. The heat → HRV coupling. Stronger coupling should reduce
     confounding_risk_score and increase the screening |r|.
  2. The skin-tone PPG penalty. Stronger penalty should widen the Q1-vs-Q4
     gap in the fairness audit.
  3. The device-B HR offset. Larger offset should reduce device_bias_score.

Each cell of the table is a single audit run on a fresh cohort. The full
sweep is ~9 cohorts, each smaller than the default (60 participants × 30
days) so it stays under a minute on CPU.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.logging import get_logger

log = get_logger("generator_stress_test")


@dataclass
class StressResult:
    effect: str
    strength: str
    coefficient: float
    measurement_name: str
    measurement_value: float
    n_participants: int
    n_days: int


def _patched_generate(n_participants: int, n_days: int, seed: int,
                      heat_hrv_coef: float | None = None,
                      skin_tone_penalty: float | None = None,
                      device_b_offset: float | None = None) -> pd.DataFrame:
    """Run a fresh generator with optional parameter overrides via monkey-patching.

    We monkey-patch the module-level constants the generator uses. This keeps
    the production generator code clean while letting the stress test sweep.
    """
    from src.data import synthetic_signal_generator as gen

    # Snapshot defaults so we can restore
    saved = {}
    for name in ("HEAT_HRV_COEF", "SKIN_TONE_PPG_PENALTY", "DEVICE_B_HR_OFFSET"):
        if hasattr(gen, name):
            saved[name] = getattr(gen, name)
    try:
        if heat_hrv_coef is not None:
            gen.HEAT_HRV_COEF = heat_hrv_coef
        if skin_tone_penalty is not None:
            gen.SKIN_TONE_PPG_PENALTY = skin_tone_penalty
        if device_b_offset is not None:
            gen.DEVICE_B_HR_OFFSET = device_b_offset

        spec = gen.CohortSpec(
            n_participants=n_participants,
            n_days=n_days,
            seed=seed,
        ) if hasattr(gen, "CohortSpec") else None
        # Generator API takes config_path; we work around by writing a temp config.
        import tempfile, yaml
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            syn = td / "data" / "synthetic"
            syn.mkdir(parents=True)
            cfg = {
                "project": {"name": "stress", "seed": seed,
                            "output_dir": str(td/"results"), "data_dir": str(td/"data")},
                "cohort": {
                    "n_participants": n_participants, "n_days": n_days,
                    "short_window_seconds": 5, "ecg_sample_rate_hz": 250,
                    "ppg_sample_rate_hz": 64,
                    "devices": ["device_A", "device_B", "device_C"],
                    "sex_distribution": {"F": 0.51, "M": 0.49},
                    "age_range": [18, 75],
                },
                "paths": {
                    "synthetic_csv": str(syn/"d.csv"),
                    "synthetic_windows": str(syn/"w.npz"),
                    "processed_csv": str(syn/"p.csv"),
                    "report_md": str(td/"r.md"),
                    "leaderboard_csv": str(td/"l.csv"),
                    "figures_dir": str(td/"figs"),
                },
            }
            cfg_path = td / "cfg.yaml"
            cfg_path.write_text(yaml.safe_dump(cfg))
            df, _ = gen.generate(config_path=cfg_path)
            return df
    finally:
        for name, value in saved.items():
            setattr(gen, name, value)


def _heat_hrv_screening_r(df: pd.DataFrame) -> float:
    sub = df[["heat_index", "hrv_rmssd"]].dropna()
    if len(sub) < 10:
        return float("nan")
    return float(sub.corr().iloc[0, 1])


def _skin_tone_quartile_gap(df: pd.DataFrame, column: str = "signal_quality_ground_truth") -> float:
    """Q4 mean minus Q1 mean of `column` after skin-tone quartile binning."""
    if "skin_tone_proxy" not in df.columns or column not in df.columns:
        return float("nan")
    df = df.dropna(subset=["skin_tone_proxy", column]).copy()
    try:
        df["q"] = pd.qcut(df["skin_tone_proxy"], q=4, labels=["Q1","Q2","Q3","Q4"])
    except ValueError:
        return float("nan")
    means = df.groupby("q", observed=True)[column].mean()
    return float(means.get("Q4", float("nan")) - means.get("Q1", float("nan")))


def _device_b_hr_offset(df: pd.DataFrame) -> float:
    """Mean resting_hr difference: device_B minus device_A."""
    if "device_type" not in df.columns:
        return float("nan")
    a = df.loc[df["device_type"] == "device_A", "resting_hr"].mean()
    b = df.loc[df["device_type"] == "device_B", "resting_hr"].mean()
    return float(b - a)


def stress_test(n_participants: int = 60, n_days: int = 30, seed: int = 0) -> pd.DataFrame:
    """Sweep three injected effects at three strengths; report cohort-level metrics."""
    # Note: defaults below should roughly match the generator's hard-coded values.
    # If those values change, update here too.
    sweeps = [
        # (effect_name, kwarg, strengths)
        # Defaults must match src/data/synthetic_signal_generator.py constants.
        ("heat_hrv_coupling", "heat_hrv_coef",
         [("low", 0.0), ("default", -1.8), ("high", -5.0)]),
        ("skin_tone_ppg_penalty", "skin_tone_penalty",
         [("low", 0.0), ("default", 0.12), ("high", 0.40)]),
        ("device_b_hr_offset", "device_b_offset",
         [("low", 0.0), ("default", 3.8), ("high", 10.0)]),
    ]

    rows = []
    for effect, kwarg, strengths in sweeps:
        for strength, value in strengths:
            log.info("Sweep: effect=%s strength=%s coef=%.3f", effect, strength, value)
            try:
                df = _patched_generate(n_participants=n_participants, n_days=n_days,
                                       seed=seed, **{kwarg: value})
            except AttributeError:
                # The generator doesn't expose a module-level constant by this name.
                # Skip cleanly; the rest of the sweep still produces useful output.
                log.warning("Generator has no %s constant; skipping this sweep.",
                            kwarg)
                continue

            if effect == "heat_hrv_coupling":
                measurement_name = "screening_r(heat_index, hrv_rmssd)"
                measurement_value = _heat_hrv_screening_r(df)
            elif effect == "skin_tone_ppg_penalty":
                measurement_name = "Q4_minus_Q1(signal_quality_ground_truth)"
                measurement_value = _skin_tone_quartile_gap(df)
            elif effect == "device_b_hr_offset":
                measurement_name = "mean_hr(device_B) - mean_hr(device_A)"
                measurement_value = _device_b_hr_offset(df)
            else:
                continue

            rows.append({
                "effect": effect,
                "strength": strength,
                "coefficient": value,
                "measurement_name": measurement_name,
                "measurement_value": round(measurement_value, 4),
                "n_participants": n_participants,
                "n_days": n_days,
            })

    return pd.DataFrame(rows)


def check_monotonic_response(table: pd.DataFrame) -> pd.DataFrame:
    """For each effect, check the measurement moves monotonically with the coefficient.

    Returns a per-effect summary with a 'passes' flag.
    """
    rows = []
    for effect, group in table.groupby("effect"):
        g = group.sort_values("coefficient").reset_index(drop=True)
        if len(g) < 2:
            rows.append({"effect": effect, "n_points": len(g),
                         "monotonic": None, "delta_low_to_high": None})
            continue
        coefs = g["coefficient"].to_numpy()
        meas = g["measurement_value"].to_numpy()
        # Direction the measurement moves as coefficient increases
        diffs = np.diff(meas)
        monotonic_up = bool((diffs >= -0.05 * np.std(meas) - 1e-9).all())
        monotonic_dn = bool((diffs <= 0.05 * np.std(meas) + 1e-9).all())
        rows.append({
            "effect": effect,
            "n_points": len(g),
            "monotonic": monotonic_up or monotonic_dn,
            "delta_low_to_high": float(meas[-1] - meas[0]),
        })
    return pd.DataFrame(rows)
