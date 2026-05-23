"""WESAD adapter.

WESAD (Schmidt et al. 2018, https://archive.ics.uci.edu/dataset/465/wesad) is
a small public wearable dataset that we use as the first real-data validation
target. It has 15 participants, ~60 minutes per participant, three labeled
states (baseline, stress, amusement), and synchronous ECG + PPG + EDA from
both a chest device (RespiBAN) and a wrist device (Empatica E4).

This module turns a downloaded WESAD directory into the canonical daily-summary
schema this framework expects, plus the short ECG/PPG window arrays. Once you
have a copy of the WESAD `.pkl` files, point this adapter at the directory and
run `scripts/run_real_data_pilot.py --dataset wesad --path /your/path/to/wesad`.

WESAD does not have multi-day longitudinal data. We treat each ~60-minute
recording as a single 'participant-day' for compatibility with the framework's
daily schema. Test-retest reliability and weekly reproducibility metrics will
not be informative on this dataset; we report them as NaN with a clear note.
What WESAD *is* good for:

- Per-window ECG and PPG signal-quality validation against the framework's
  in-house SQI and the Orphanidou (2015) baseline.
- Cross-device comparison between RespiBAN (chest, gold standard for ECG)
  and Empatica E4 (wrist, the realistic clinical device).
- Artifact-burden estimates under labeled states (baseline / stress /
  amusement). Stress segments should produce higher artifact burden if
  the framework is doing what it claims.

For a multi-day longitudinal validation, MIMIC-PERform or AppleWatch-MIMIC
are more appropriate. Adapters for those datasets are not yet implemented.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger("wesad_adapter")


@dataclass
class WESADRecording:
    """Parsed single-participant WESAD recording.

    The original pickle has a nested dict with keys
    {'subject', 'signal': {'chest': {...}, 'wrist': {...}}, 'label': array}.
    Chest has ECG, EDA, EMG, Resp, Temp at 700 Hz. Wrist E4 has BVP at 64 Hz,
    EDA at 4 Hz, TEMP at 4 Hz, ACC at 32 Hz.
    """
    subject_id: str
    chest_ecg: np.ndarray      # (n_samples,) at 700 Hz
    wrist_ppg: np.ndarray      # (n_samples,) at 64 Hz, called BVP in WESAD
    wrist_acc: np.ndarray      # (n_samples, 3) at 32 Hz
    labels: np.ndarray         # (n_samples,) at 700 Hz, integer states
    chest_fs: int = 700
    wrist_ppg_fs: int = 64
    wrist_acc_fs: int = 32


# WESAD label encoding from the dataset README
WESAD_LABELS = {
    0: "transient",
    1: "baseline",
    2: "stress",
    3: "amusement",
    4: "meditation",
    5: "ignore_5",
    6: "ignore_6",
    7: "ignore_7",
}


def load_wesad_pickle(path: Path) -> WESADRecording:
    """Load a single `S*.pkl` file from a WESAD subject directory."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"WESAD pickle not found at {path}")
    with open(path, "rb") as f:
        # WESAD pickles were created with Python 2; encoding='latin1' is the
        # documented workaround.
        data = pickle.load(f, encoding="latin1")

    subject = data.get("subject", path.stem)
    signal = data["signal"]
    label = data["label"]

    chest = signal["chest"]
    wrist = signal["wrist"]

    # Some keys come back as 2D (n_samples, 1) and some as 1D
    chest_ecg = np.asarray(chest["ECG"]).squeeze()
    wrist_ppg = np.asarray(wrist["BVP"]).squeeze()
    wrist_acc = np.asarray(wrist["ACC"])

    return WESADRecording(
        subject_id=str(subject),
        chest_ecg=chest_ecg.astype(float),
        wrist_ppg=wrist_ppg.astype(float),
        wrist_acc=wrist_acc.astype(float),
        labels=np.asarray(label).astype(int),
    )


def extract_windows(rec: WESADRecording, window_seconds: float = 5.0,
                    stride_seconds: float = 5.0,
                    states: tuple[int, ...] = (1, 2, 3)
                    ) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Cut non-overlapping windows of `window_seconds` and tag each by state.

    Returns
    -------
    ecg_windows : (n_windows, ecg_window_len) at 700 Hz
    ppg_windows : (n_windows, ppg_window_len) at 64 Hz
    meta : DataFrame with columns:
        window_idx, subject_id, label, label_name, start_seconds, end_seconds

    Only windows whose label is in `states` are returned (default: baseline,
    stress, amusement). Transient and ignore segments are dropped.
    """
    ecg_window = int(window_seconds * rec.chest_fs)
    ppg_window = int(window_seconds * rec.wrist_ppg_fs)
    ecg_stride = int(stride_seconds * rec.chest_fs)
    ppg_stride = int(stride_seconds * rec.wrist_ppg_fs)
    label_stride = ecg_stride  # labels are at chest fs

    ecg_list, ppg_list, meta_rows = [], [], []
    idx = 0
    n_chest = min(len(rec.chest_ecg), len(rec.labels))
    n_wrist = len(rec.wrist_ppg)

    for chest_start in range(0, n_chest - ecg_window + 1, ecg_stride):
        chest_end = chest_start + ecg_window
        seg_labels = rec.labels[chest_start:chest_end]
        # Require the entire window to share a label and to be a state we want
        if seg_labels.size == 0:
            continue
        primary_label = int(seg_labels[0])
        if primary_label not in states:
            continue
        if not (seg_labels == primary_label).all():
            continue
        # Matching wrist window: scale by the sampling rate ratio
        wrist_start = int(chest_start * rec.wrist_ppg_fs / rec.chest_fs)
        wrist_end = wrist_start + ppg_window
        if wrist_end > n_wrist:
            continue

        ecg_list.append(rec.chest_ecg[chest_start:chest_end])
        ppg_list.append(rec.wrist_ppg[wrist_start:wrist_end])
        meta_rows.append({
            "window_idx": idx,
            "subject_id": rec.subject_id,
            "label": primary_label,
            "label_name": WESAD_LABELS.get(primary_label, "unknown"),
            "start_seconds": chest_start / rec.chest_fs,
            "end_seconds": chest_end / rec.chest_fs,
        })
        idx += 1

    if not ecg_list:
        log.warning("WESAD: no windows extracted for subject %s.", rec.subject_id)
        return np.empty((0, ecg_window)), np.empty((0, ppg_window)), pd.DataFrame()

    return (np.stack(ecg_list), np.stack(ppg_list),
            pd.DataFrame(meta_rows))


def to_daily_summary(rec: WESADRecording) -> pd.DataFrame:
    """Aggregate one WESAD recording into a single 'participant-day' row.

    The framework's downstream code expects daily summaries. WESAD is a
    single ~60-minute session per subject, so we collapse the whole session
    into one row with derived per-state aggregates as separate columns.

    Returns one row with the framework's canonical column schema, filled
    where WESAD provides data and NaN where it does not.
    """
    # Compute heart rate from chest ECG: simple R-peak detection on the
    # baseline segment to avoid contamination by stress / amusement effects.
    baseline_mask = rec.labels == 1
    if baseline_mask.any():
        # Use the framework's own R-peak detector for consistency with the
        # synthetic pipeline.
        from biomedical_signal_forensics_lab.signals.ecg_processing import detect_r_peaks, bandpass
        ecg_baseline = rec.chest_ecg[baseline_mask]
        if len(ecg_baseline) > rec.chest_fs * 5:
            filt = bandpass(ecg_baseline, rec.chest_fs)
            peaks = detect_r_peaks(filt, rec.chest_fs)
            if len(peaks) > 5:
                rr_intervals_s = np.diff(peaks) / rec.chest_fs
                # Two-stage RR cleaning, following standard HRV practice
                # (Task Force 1996, Malik 1996, Berntson 1990).
                #
                # Stage 1: drop physiologically implausible intervals.
                # RR in [0.4, 1.5] seconds corresponds to HR in [40, 150] bpm.
                plausible = (rr_intervals_s >= 0.4) & (rr_intervals_s <= 1.5)
                rr_clean = rr_intervals_s[plausible]
                # Stage 2: drop intervals that differ from the running median
                # by more than 25%. This catches doubled intervals (missed
                # beats) and halved intervals (extra detections), which the
                # plausibility filter alone can't catch when the bad intervals
                # are themselves in the physiological range.
                if len(rr_clean) > 10:
                    running_median = np.median(rr_clean)
                    ratio = np.abs(rr_clean - running_median) / running_median
                    rr_clean = rr_clean[ratio < 0.25]
                if len(rr_clean) > 5:
                    resting_hr = float(60.0 / rr_clean.mean())
                    successive_diff_ms = np.diff(rr_clean * 1000)
                    hrv_rmssd = float(np.sqrt(np.mean(successive_diff_ms ** 2)))
                else:
                    resting_hr = float("nan")
                    hrv_rmssd = float("nan")
            else:
                resting_hr = float("nan")
                hrv_rmssd = float("nan")
        else:
            resting_hr = float("nan")
            hrv_rmssd = float("nan")
    else:
        resting_hr = float("nan")
        hrv_rmssd = float("nan")

    # Active minutes proxy: count seconds where wrist accelerometer magnitude
    # exceeds 1.5 SD above the recording mean.
    if rec.wrist_acc.size > 0:
        acc_mag = np.linalg.norm(rec.wrist_acc, axis=1)
        active_threshold = float(acc_mag.mean() + 1.5 * acc_mag.std())
        active_samples = int((acc_mag > active_threshold).sum())
        active_seconds = active_samples / rec.wrist_acc_fs
        active_minutes = active_seconds / 60.0
    else:
        active_minutes = float("nan")

    # Session length in seconds, converted to a 'wear minutes' approximation.
    session_seconds = len(rec.chest_ecg) / rec.chest_fs
    wearable_minutes = float(session_seconds / 60.0)

    # Stress proxy: fraction of session labeled as stress.
    stress_frac = float((rec.labels == 2).mean()) if len(rec.labels) else float("nan")

    row = {
        "participant_id": rec.subject_id,
        "date": pd.Timestamp("2024-01-01"),  # WESAD has no date; placeholder
        "device_type": "WESAD_RespiBAN_E4",
        "resting_hr": resting_hr,
        "hrv_rmssd": hrv_rmssd,
        "hrv_sdnn": float("nan"),
        "step_count": float("nan"),
        "active_minutes": active_minutes,
        "sleep_duration": float("nan"),
        "sleep_efficiency": float("nan"),
        "stress_proxy": stress_frac,
        "temperature_c": float("nan"),
        "humidity": float("nan"),
        "aqi": float("nan"),
        "heat_index": float("nan"),
        "wearable_minutes": wearable_minutes,
        "missing_wearable_flag": 0,
        # Ground-truth quality columns: WESAD does not provide these; we leave
        # them NaN so the framework's score() correctly reports
        # 'insufficient_data' for SQ and AB.
        "signal_quality_ground_truth": float("nan"),
        "artifact_burden_ground_truth": float("nan"),
        "reliability_ground_truth": float("nan"),
        "skin_tone_proxy": float("nan"),  # not in WESAD
    }
    return pd.DataFrame([row])


def adapt_directory(wesad_dir: Path) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, pd.DataFrame]:
    """Walk a WESAD directory of `S*` subdirs, return cohort daily + windows + meta.

    Expected layout:
        wesad_dir/
            S2/S2.pkl
            S3/S3.pkl
            S4/S4.pkl
            ...
            S17/S17.pkl

    Returns
    -------
    daily_df : DataFrame with one row per subject (16 subjects in WESAD)
    ecg_windows : (n_windows, ecg_window_len) array, all subjects pooled
    ppg_windows : (n_windows, ppg_window_len) array, all subjects pooled
    window_meta : DataFrame with one row per window
    """
    wesad_dir = Path(wesad_dir)
    if not wesad_dir.exists():
        raise FileNotFoundError(f"WESAD directory not found: {wesad_dir}")
    subject_dirs = sorted([d for d in wesad_dir.iterdir()
                           if d.is_dir() and d.name.startswith("S")])
    if not subject_dirs:
        raise FileNotFoundError(
            f"No S* subdirectories found in {wesad_dir}. Expected layout: "
            "wesad_dir/S2/S2.pkl, wesad_dir/S3/S3.pkl, ..."
        )

    daily_rows = []
    ecg_chunks = []
    ppg_chunks = []
    meta_chunks = []

    for sd in subject_dirs:
        pkl = sd / f"{sd.name}.pkl"
        if not pkl.exists():
            log.warning("WESAD: %s missing, skipping.", pkl)
            continue
        log.info("WESAD: loading %s …", pkl.name)
        rec = load_wesad_pickle(pkl)
        daily_rows.append(to_daily_summary(rec))
        ecg, ppg, meta = extract_windows(rec)
        if len(meta) > 0:
            ecg_chunks.append(ecg)
            ppg_chunks.append(ppg)
            meta_chunks.append(meta)

    if not daily_rows:
        raise RuntimeError(f"No usable WESAD subjects found in {wesad_dir}")

    daily_df = pd.concat(daily_rows, ignore_index=True)
    # The synthetic generator produces one row per (participant, day). WESAD
    # has one row per participant. Fine for cross-sectional analyses; the
    # daily-summary schema is compatible.

    if ecg_chunks:
        ecg_arr = np.concatenate(ecg_chunks, axis=0)
        ppg_arr = np.concatenate(ppg_chunks, axis=0)
        meta_df = pd.concat(meta_chunks, ignore_index=True)
        # Rewrite window_idx so it is unique across the pooled set
        meta_df["window_idx"] = np.arange(len(meta_df))
    else:
        ecg_arr = np.empty((0, 0))
        ppg_arr = np.empty((0, 0))
        meta_df = pd.DataFrame()

    log.info("WESAD: %d subjects, %d total windows extracted",
             len(daily_df), len(meta_df))
    return daily_df, ecg_arr, ppg_arr, meta_df
