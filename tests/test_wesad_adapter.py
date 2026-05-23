"""WESAD adapter tests.

These tests use a synthetic WESAD-shaped fixture, so they run end-to-end in
the sandbox without requiring the real dataset. Real-data validation happens
when someone runs `scripts/run_real_data_pilot.py` against a downloaded
WESAD copy.
"""
import pickle
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.data.wesad_adapter import (
    adapt_directory, extract_windows, load_wesad_pickle, to_daily_summary,
    WESAD_LABELS, WESADRecording,
)


def _make_synthetic_wesad_subject(sid: str, seconds: float = 30.0, seed: int = 0,
                                  hr_bpm: float = 75.0) -> dict:
    """Build a WESAD-shaped pickle payload for one subject.

    Replicates the nested structure WESAD uses: dict with keys
    'subject', 'signal' (chest + wrist), 'label'.
    """
    rng = np.random.default_rng(seed)
    chest_fs = 700
    wrist_ppg_fs = 64
    wrist_acc_fs = 32
    n_chest = int(seconds * chest_fs)
    n_ppg = int(seconds * wrist_ppg_fs)
    n_acc = int(seconds * wrist_acc_fs)

    # Build a Gaussian-spike ECG at the requested heart rate
    t_chest = np.arange(n_chest) / chest_fs
    period_s = 60.0 / hr_bpm
    ecg = sum(np.exp(-((t_chest - k * period_s) ** 2) / (2 * 0.012 ** 2))
              for k in range(int(seconds / period_s) + 2))
    ecg += 0.05 * rng.standard_normal(n_chest)

    # PPG: sine plus harmonic at the same HR
    t_ppg = np.arange(n_ppg) / wrist_ppg_fs
    ppg = (np.sin(2 * np.pi * (hr_bpm / 60.0) * t_ppg)
           + 0.3 * np.sin(2 * np.pi * 2 * (hr_bpm / 60.0) * t_ppg)
           + 0.05 * rng.standard_normal(n_ppg))

    acc = rng.normal(0, 0.5, (n_acc, 3))

    # Labels: alternate baseline (1) and stress (2)
    half = n_chest // 2
    labels = np.concatenate([
        np.ones(half, dtype=int),
        np.full(n_chest - half, 2, dtype=int),
    ])

    return {
        "subject": sid,
        "signal": {
            "chest": {"ECG": ecg.reshape(-1, 1)},
            "wrist": {"BVP": ppg.reshape(-1, 1), "ACC": acc},
        },
        "label": labels,
    }


def _build_fixture_dir(td: Path, subjects: list[str] = None) -> Path:
    """Write a synthetic WESAD-shaped directory tree under td."""
    if subjects is None:
        subjects = ["S2", "S3"]
    for sid in subjects:
        sd = td / sid
        sd.mkdir(parents=True, exist_ok=True)
        with open(sd / f"{sid}.pkl", "wb") as f:
            pickle.dump(_make_synthetic_wesad_subject(sid, seed=hash(sid) % 1000), f)
    return td


def test_load_wesad_pickle_returns_recording():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _build_fixture_dir(td, ["S2"])
        rec = load_wesad_pickle(td / "S2" / "S2.pkl")
        assert isinstance(rec, WESADRecording)
        assert rec.subject_id == "S2"
        assert rec.chest_fs == 700
        assert rec.wrist_ppg_fs == 64
        assert rec.chest_ecg.ndim == 1
        assert rec.wrist_ppg.ndim == 1


def test_load_wesad_pickle_raises_on_missing_path():
    try:
        load_wesad_pickle(Path("/nonexistent/path.pkl"))
    except FileNotFoundError:
        return
    raise AssertionError("Did not raise FileNotFoundError")


def test_extract_windows_returns_one_per_5_seconds():
    """30-second recording, 5-second non-overlapping windows: expect 6 windows."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _build_fixture_dir(td, ["S2"])
        rec = load_wesad_pickle(td / "S2" / "S2.pkl")
        ecg, ppg, meta = extract_windows(rec, window_seconds=5.0)
        assert len(meta) == 6  # 30 s / 5 s per window
        assert ecg.shape == (6, 5 * 700)
        assert ppg.shape == (6, 5 * 64)
        # The labels stay within their half: first half baseline, second stress
        labels = set(meta["label_name"])
        assert labels == {"baseline", "stress"}


def test_extract_windows_drops_state_zero():
    """Transient (label 0) windows must be dropped."""
    rec = WESADRecording(
        subject_id="S0",
        chest_ecg=np.random.default_rng(0).normal(0, 1, 700 * 30).astype(float),
        wrist_ppg=np.random.default_rng(1).normal(0, 1, 64 * 30).astype(float),
        wrist_acc=np.zeros((32 * 30, 3)),
        labels=np.zeros(700 * 30, dtype=int),  # all transient
    )
    ecg, ppg, meta = extract_windows(rec)
    assert len(meta) == 0


def test_to_daily_summary_recovers_injected_hr():
    """The adapter's HR estimate should be close to the injected 75 bpm."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _build_fixture_dir(td, ["S2"])
        rec = load_wesad_pickle(td / "S2" / "S2.pkl")
        daily = to_daily_summary(rec)
        assert len(daily) == 1
        # Allow a wide tolerance: synthetic ECG + simple R-peak detector
        hr = daily["resting_hr"].iloc[0]
        assert 60 <= hr <= 100, f"recovered HR {hr} outside plausible range"


def test_to_daily_summary_has_canonical_schema():
    """The adapter must produce the framework's canonical column set."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _build_fixture_dir(td, ["S2"])
        rec = load_wesad_pickle(td / "S2" / "S2.pkl")
        daily = to_daily_summary(rec)
        required = {
            "participant_id", "date", "device_type", "resting_hr",
            "hrv_rmssd", "wearable_minutes", "missing_wearable_flag",
            "signal_quality_ground_truth",
        }
        assert required.issubset(set(daily.columns))


def test_adapt_directory_two_subjects():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _build_fixture_dir(td, ["S2", "S3"])
        daily, ecg, ppg, meta = adapt_directory(td)
        assert len(daily) == 2
        assert ecg.shape[0] == 12  # 2 subjects × 6 windows each
        assert ppg.shape[0] == 12
        assert len(meta) == 12
        # window_idx must be unique across the pooled set
        assert meta["window_idx"].nunique() == 12


def test_adapt_directory_raises_on_missing_path():
    try:
        adapt_directory(Path("/nonexistent/wesad"))
    except FileNotFoundError:
        return
    raise AssertionError("Did not raise FileNotFoundError")


def test_adapt_directory_raises_on_empty_dir():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # Directory exists but has no S* subdirectories
        try:
            adapt_directory(td)
        except FileNotFoundError as e:
            assert "S*" in str(e) or "subdirector" in str(e)
            return
        raise AssertionError("Did not raise on empty directory")


def test_wesad_label_dict_has_known_states():
    """Sanity-check the label encoding constants."""
    assert WESAD_LABELS[1] == "baseline"
    assert WESAD_LABELS[2] == "stress"
    assert WESAD_LABELS[3] == "amusement"
