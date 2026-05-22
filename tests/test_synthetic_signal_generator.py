"""Synthetic data generator should produce a plausible cohort with the columns we promise."""
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.data.synthetic_signal_generator import generate


def _make_tiny_config(tmp_path: Path) -> Path:
    """Write a small-cohort config under tmp_path and return its path."""
    syn = tmp_path / "data" / "synthetic"
    proc = tmp_path / "data" / "processed"
    figs = tmp_path / "results" / "figures"
    syn.mkdir(parents=True, exist_ok=True)
    proc.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    cfg = {
        "project": {"name": "test", "seed": 7, "output_dir": str(tmp_path / "results"),
                    "data_dir": str(tmp_path / "data")},
        "cohort": {
            "n_participants": 8, "n_days": 5,
            "short_window_seconds": 5, "ecg_sample_rate_hz": 250, "ppg_sample_rate_hz": 64,
            "devices": ["device_A", "device_B", "device_C"],
            "sex_distribution": {"F": 0.51, "M": 0.49},
            "age_range": [18, 75],
        },
        "paths": {
            "synthetic_csv": str(syn / "synthetic_signal_dataset.csv"),
            "synthetic_windows": str(syn / "synthetic_windows.npz"),
            "processed_csv": str(proc / "processed.csv"),
            "report_md": str(tmp_path / "results" / "report.md"),
            "leaderboard_csv": str(tmp_path / "results" / "leaderboard.csv"),
            "figures_dir": str(figs),
        },
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    return cfg_path


def test_generator_writes_files(tmp_path):
    cfg_path = _make_tiny_config(tmp_path)
    df, windows = generate(config_path=cfg_path)
    assert Path(tmp_path / "data" / "synthetic" / "synthetic_signal_dataset.csv").exists()
    assert Path(tmp_path / "data" / "synthetic" / "synthetic_windows.npz").exists()
    assert isinstance(df, pd.DataFrame) and len(df) > 0


def test_dataset_has_expected_columns(tmp_path):
    cfg_path = _make_tiny_config(tmp_path)
    df, _ = generate(config_path=cfg_path)
    must_have = {
        "participant_id", "date", "device_type", "resting_hr", "hrv_rmssd",
        "sleep_duration", "wearable_minutes", "missing_wearable_flag",
        "signal_quality_ground_truth", "artifact_burden_ground_truth",
        "reliability_ground_truth", "temperature_c", "aqi",
    }
    missing = must_have - set(df.columns)
    assert not missing, f"missing columns: {missing}"


def test_physiological_ranges_are_sane(tmp_path):
    cfg_path = _make_tiny_config(tmp_path)
    df, _ = generate(config_path=cfg_path)
    valid = df.dropna(subset=["resting_hr", "hrv_rmssd", "sleep_duration"])
    assert valid["resting_hr"].between(30, 130).all()
    assert valid["hrv_rmssd"].between(2, 200).all()
    assert valid["sleep_duration"].between(0, 14).all()
    assert valid["sleep_efficiency"].dropna().between(0, 1).all()


def test_ground_truth_in_unit_interval(tmp_path):
    cfg_path = _make_tiny_config(tmp_path)
    df, _ = generate(config_path=cfg_path)
    for col in ("signal_quality_ground_truth", "artifact_burden_ground_truth", "reliability_ground_truth"):
        assert df[col].between(0, 1).all()


def test_windows_have_signal_arrays(tmp_path):
    cfg_path = _make_tiny_config(tmp_path)
    _, windows = generate(config_path=cfg_path)
    assert "ecg" in windows and "ppg" in windows
    ecg = windows["ecg"]
    ppg = windows["ppg"]
    assert ecg.ndim == 2 and ppg.ndim == 2
    assert ecg.shape[0] == ppg.shape[0]
