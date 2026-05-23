"""Synthetic signal generator.

Generates a cohort of N participants over D days with:
    - static demographics and device assignment
    - daily wearable summaries (HR, HRV, sleep, activity, environment)
    - short ECG- and PPG-like waveform windows

Correlations are hand-coded to be plausible, not exhaustive. Heat reduces
HRV, motion degrades PPG, low wear-time clusters with stress days, etc.
This is a research substrate: nothing in here should be confused with
real physiology.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from ..utils.config import load_yaml
from ..utils.logging import get_logger
from ..utils.paths import ensure_dir, resolve

log = get_logger("synthetic")


# ---------------------------------------------------------------------------
# Static cohort
# ---------------------------------------------------------------------------

@dataclass
class CohortSpec:
    n_participants: int = 300
    n_days: int = 60
    seed: int = 42


def _build_participants(spec: CohortSpec, devices: list[str]) -> pd.DataFrame:
    rng = np.random.default_rng(spec.seed)
    pids = [f"P{idx:04d}" for idx in range(1, spec.n_participants + 1)]
    sexes = rng.choice(["F", "M"], size=spec.n_participants, p=[0.51, 0.49])
    ages = rng.integers(18, 76, size=spec.n_participants)
    # baseline HR roughly anti-correlated with age noise
    baseline_hr = np.clip(
        70 + (ages - 40) * 0.05 + rng.normal(0, 6, spec.n_participants), 45, 95
    )
    baseline_hrv = np.clip(
        55 - (ages - 30) * 0.4 + rng.normal(0, 9, spec.n_participants), 12, 110
    )
    baseline_activity = np.clip(rng.normal(7500, 2800, spec.n_participants), 800, 22000)
    # device assignment with a small skew so device_C is rarer
    device_type = rng.choice(devices, size=spec.n_participants, p=[0.45, 0.4, 0.15])
    skin_tone_proxy = rng.uniform(0.0, 1.0, spec.n_participants)  # 0 = lightest, 1 = darkest
    climate_sensitivity = rng.beta(2, 5, spec.n_participants)  # how much heat hurts them
    missingness_tendency = rng.beta(2, 8, spec.n_participants)  # baseline non-wear propensity

    return pd.DataFrame(
        {
            "participant_id": pids,
            "age": ages,
            "sex": sexes,
            "baseline_hr": baseline_hr.round(1),
            "baseline_hrv": baseline_hrv.round(1),
            "baseline_activity": baseline_activity.round(0).astype(int),
            "device_type": device_type,
            "skin_tone_proxy": skin_tone_proxy.round(3),
            "climate_sensitivity": climate_sensitivity.round(3),
            "missingness_tendency": missingness_tendency.round(3),
        }
    )


# ---------------------------------------------------------------------------
# Daily summary generator
# ---------------------------------------------------------------------------

def _seasonal_temperature(day_idx: int, rng: np.random.Generator) -> float:
    """A 60-day stretch with a heatwave in the middle."""
    base = 22 + 8 * np.sin(2 * np.pi * day_idx / 60.0)
    return float(base + rng.normal(0, 2))


# Tunable generative coefficients. Exposed at module level so they can be
# monkey-patched by the generator stress-test sweep. Treat the values as
# illustrative; they were chosen to give the audit machinery something
# detectable on the synthetic cohort, not as calibrations of any real device.
HEAT_HRV_COEF = -1.8          # ms HRV per heat-load unit
SKIN_TONE_PPG_PENALTY = 0.12  # max SQI loss at proxy=1
DEVICE_B_HR_OFFSET = 3.8      # bpm
DEVICE_C_HR_OFFSET = -2.1     # bpm


def _device_bias(device_type: str) -> dict:
    """Per-device additive bias on HR and multiplicative on signal quality."""
    return {
        "device_A": {"hr_bias": 0.0,                "sq_mult": 1.00, "ppg_sq_mult": 1.00},
        "device_B": {"hr_bias": DEVICE_B_HR_OFFSET, "sq_mult": 0.92, "ppg_sq_mult": 0.88},
        "device_C": {"hr_bias": DEVICE_C_HR_OFFSET, "sq_mult": 0.85, "ppg_sq_mult": 0.78},
    }[device_type]


def _build_daily(participants: pd.DataFrame, spec: CohortSpec) -> pd.DataFrame:
    rng = np.random.default_rng(spec.seed + 1)
    rows: list[dict] = []
    start_date = pd.Timestamp("2025-01-01")

    for _, p in participants.iterrows():
        bias = _device_bias(p["device_type"])
        # person-level random offsets
        person_noise = rng.normal(0, 1.0)

        for d in range(spec.n_days):
            date = start_date + pd.Timedelta(days=d)
            temperature = _seasonal_temperature(d, rng)
            humidity = float(np.clip(rng.normal(55, 12), 15, 95))
            aqi = float(np.clip(rng.gamma(2.0, 25), 8, 280))
            heat_index = temperature + 0.4 * (humidity - 50) / 10.0

            # daily activity around baseline; weekends slightly higher
            weekend_boost = 1.12 if date.dayofweek >= 5 else 1.0
            steps = max(0, int(rng.normal(p["baseline_activity"] * weekend_boost, 2200)))
            active_minutes = int(np.clip(steps / 120 + rng.normal(0, 8), 0, 240))

            # heat hurts sleep proportional to person sensitivity
            heat_pen = max(0, (heat_index - 26)) * p["climate_sensitivity"]
            aqi_pen = max(0, (aqi - 100)) * 0.002
            sleep_duration = float(np.clip(
                rng.normal(7.4, 0.9) - 0.08 * heat_pen - 0.5 * aqi_pen, 3.0, 11.0
            ))
            sleep_efficiency = float(np.clip(
                rng.normal(0.87, 0.06) - 0.012 * heat_pen - 0.04 * aqi_pen, 0.4, 0.99
            ))

            # HRV suppressed by heat, low sleep, high activity
            hrv_rmssd = float(np.clip(
                p["baseline_hrv"]
                + rng.normal(0, 6)
                + HEAT_HRV_COEF * heat_pen
                - 4 * max(0, 7 - sleep_duration)
                - 0.0006 * max(0, steps - 12000),
                5, 180,
            ))
            hrv_sdnn = float(np.clip(hrv_rmssd * (0.9 + rng.normal(0, 0.08)), 4, 220))

            # Resting HR moved by device, age, and recent activity load
            resting_hr = float(np.clip(
                p["baseline_hr"]
                + bias["hr_bias"]
                + rng.normal(0, 2.5)
                + 0.0002 * max(0, steps - 10000)
                + 0.06 * heat_pen,
                40, 110,
            ))

            stress_proxy = float(np.clip(
                rng.normal(0.35, 0.18)
                + 0.02 * heat_pen
                + 0.04 * max(0, 7 - sleep_duration)
                - 0.000008 * steps,
                0.0, 1.0,
            ))

            # ---- missingness (state-dependent) ----
            # higher tendency on high-stress, poor-sleep, high-heat days
            miss_prob = float(np.clip(
                p["missingness_tendency"]
                + 0.15 * stress_proxy
                + 0.08 * (1 - sleep_efficiency)
                + 0.01 * heat_pen,
                0.0, 0.6,
            ))
            missing_flag = int(rng.random() < miss_prob)
            wearable_minutes = 0 if missing_flag else int(np.clip(
                rng.normal(1100, 180), 200, 1440
            ))

            # ---- signal quality ground truth (latent) ----
            motion_factor = active_minutes / 240.0   # heavy active days -> more motion
            skin_penalty = SKIN_TONE_PPG_PENALTY * p["skin_tone_proxy"]
            sq_gt = float(np.clip(
                0.92 * bias["sq_mult"]
                - 0.3 * motion_factor
                - skin_penalty
                + rng.normal(0, 0.06)
                - 0.4 * missing_flag,
                0.0, 1.0,
            ))
            artifact_burden_gt = float(np.clip(
                0.15 + 0.5 * motion_factor + 0.4 * missing_flag + rng.normal(0, 0.05),
                0.0, 1.0,
            ))
            reliability_gt = float(np.clip(
                0.85 - 0.4 * missing_flag - 0.15 * motion_factor
                - 0.1 * (1 - sleep_efficiency) + rng.normal(0, 0.05),
                0.0, 1.0,
            ))

            rows.append(
                {
                    "participant_id": p["participant_id"],
                    "date": date.date().isoformat(),
                    "resting_hr": round(resting_hr, 1),
                    "hrv_rmssd": round(hrv_rmssd, 1),
                    "hrv_sdnn": round(hrv_sdnn, 1),
                    "step_count": steps,
                    "active_minutes": active_minutes,
                    "sleep_duration": round(sleep_duration, 2),
                    "sleep_efficiency": round(sleep_efficiency, 3),
                    "stress_proxy": round(stress_proxy, 3),
                    "temperature_c": round(temperature, 1),
                    "humidity": round(humidity, 1),
                    "aqi": round(aqi, 1),
                    "heat_index": round(heat_index, 1),
                    "wearable_minutes": wearable_minutes,
                    "missing_wearable_flag": missing_flag,
                    "signal_quality_ground_truth": round(sq_gt, 3),
                    "artifact_burden_ground_truth": round(artifact_burden_gt, 3),
                    "reliability_ground_truth": round(reliability_gt, 3),
                }
            )
            _ = person_noise  # kept for future per-person effects
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Short signal windows
# ---------------------------------------------------------------------------

def _synthesize_ecg(fs: int, seconds: int, hr_bpm: float, noise: float,
                    motion: bool, dropout: bool, rng: np.random.Generator) -> np.ndarray:
    """A toy ECG: periodic 'R-peaks' as Gaussians on a low baseline."""
    n = fs * seconds
    t = np.arange(n) / fs
    rr_interval = 60.0 / max(hr_bpm, 30)
    peak_times = np.arange(rr_interval, seconds, rr_interval)
    sig = np.zeros(n)
    for pt in peak_times:
        sig += np.exp(-((t - pt) ** 2) / (2 * 0.012 ** 2))
    # broad baseline wander
    sig += 0.15 * np.sin(2 * np.pi * 0.3 * t)
    # noise
    sig += noise * rng.standard_normal(n)
    if motion:
        sig += 0.6 * np.sin(2 * np.pi * 3.5 * t) + 0.3 * rng.standard_normal(n)
    if dropout:
        start = rng.integers(0, max(1, n // 2))
        length = rng.integers(fs // 2, fs * 2)
        sig[start:start + length] = 0.0
    return sig.astype(np.float32)


def _synthesize_ppg(fs: int, seconds: int, hr_bpm: float, noise: float,
                    motion: bool, dropout: bool, rng: np.random.Generator) -> np.ndarray:
    n = fs * seconds
    t = np.arange(n) / fs
    freq = hr_bpm / 60.0
    sig = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 2 * freq * t)
    sig += noise * rng.standard_normal(n)
    if motion:
        sig += 1.2 * np.sin(2 * np.pi * 1.7 * t) + 0.4 * rng.standard_normal(n)
    if dropout:
        start = rng.integers(0, max(1, n // 2))
        length = rng.integers(fs // 4, fs)
        sig[start:start + length] = 0.0
    return sig.astype(np.float32)


def _build_windows(daily: pd.DataFrame, cfg) -> dict:
    rng = np.random.default_rng(123)
    ecg_fs = int(cfg.cohort.ecg_sample_rate_hz)
    ppg_fs = int(cfg.cohort.ppg_sample_rate_hz)
    seconds = int(cfg.cohort.short_window_seconds)

    # We don't need one window per row (18k rows × 5s × 250Hz is huge).
    # Sample ~1 in 10 rows so we get ~1800 windows, balanced across participants.
    sample = daily.sample(frac=0.1, random_state=7).reset_index(drop=True)

    ecg_arr = np.zeros((len(sample), ecg_fs * seconds), dtype=np.float32)
    ppg_arr = np.zeros((len(sample), ppg_fs * seconds), dtype=np.float32)
    meta_rows: list[dict] = []

    for i, row in sample.iterrows():
        motion = row["active_minutes"] > 90
        dropout = bool(row["missing_wearable_flag"]) or rng.random() < 0.07
        noise_level = float(np.clip(
            0.05 + 0.4 * (1 - row["signal_quality_ground_truth"]) + rng.normal(0, 0.04),
            0.01, 0.9,
        ))
        ecg_arr[i] = _synthesize_ecg(ecg_fs, seconds, row["resting_hr"], noise_level,
                                     motion, dropout, rng)
        ppg_arr[i] = _synthesize_ppg(ppg_fs, seconds, row["resting_hr"], noise_level,
                                     motion, dropout, rng)
        meta_rows.append(
            {
                "participant_id": row["participant_id"],
                "date": row["date"],
                "sampling_rate_ecg": ecg_fs,
                "sampling_rate_ppg": ppg_fs,
                "noise_level": round(noise_level, 3),
                "motion_artifact_flag": int(motion),
                "dropout_flag": int(dropout),
                "timestamp_irregularity_flag": int(rng.random() < 0.05),
            }
        )

    return {
        "ecg": ecg_arr,
        "ppg": ppg_arr,
        "meta": pd.DataFrame(meta_rows),
    }


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

def generate(config_path: str | Path = "configs/default.yaml") -> Tuple[pd.DataFrame, dict]:
    cfg = load_yaml(config_path)
    spec = CohortSpec(
        n_participants=int(cfg.cohort.n_participants),
        n_days=int(cfg.cohort.n_days),
        seed=int(cfg.project.seed),
    )
    devices = list(cfg.cohort.devices)

    log.info("Generating cohort: %d participants × %d days", spec.n_participants, spec.n_days)
    participants = _build_participants(spec, devices)
    daily = _build_daily(participants, spec)
    full = daily.merge(participants, on="participant_id", how="left")

    log.info("Synthesizing short signal windows (sampled subset)")
    windows = _build_windows(full, cfg)

    # write
    ensure_dir(Path(cfg.paths.synthetic_csv).parent)
    full.to_csv(resolve(cfg.paths.synthetic_csv), index=False)
    np.savez_compressed(
        resolve(cfg.paths.synthetic_windows),
        ecg=windows["ecg"],
        ppg=windows["ppg"],
    )
    windows["meta"].to_csv(
        resolve(Path(cfg.paths.synthetic_windows).with_suffix(".meta.csv")),
        index=False,
    )
    log.info("Wrote %s (%d rows)", cfg.paths.synthetic_csv, len(full))
    return full, windows


if __name__ == "__main__":
    generate()
