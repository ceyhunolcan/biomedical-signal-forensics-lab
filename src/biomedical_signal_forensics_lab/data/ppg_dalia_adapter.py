"""PPG-DaLiA adapter.

PPG-DaLiA (Reiss et al. 2019, https://archive.ics.uci.edu/dataset/495/ppg+dalia)
is a 15-subject public wearable dataset that we use as the second real-data
validation target after WESAD. It uses the same hardware as WESAD (Empatica E4
wrist + RespiBAN chest) but a different protocol: 8 ambulatory activities
(sitting, stairs, table-soccer, cycling, car-driving, lunch-break, walking,
working) instead of WESAD's psychological-state paradigm.

If the cross-method SQI disagreement finding from WESAD replicates here, the
finding is about wrist PPG itself rather than about the WESAD stress paradigm.

This module turns a downloaded PPG-DaLiA directory into the same canonical
schema as wesad_adapter (daily_df + ecg_arr + ppg_arr + meta), so the existing
analysis functions in evaluation.deep_real_analysis can run unchanged.

Layout expected:
    ppg_dalia_dir/
        S1/S1.pkl
        S2/S2.pkl
        ...
        S15/S15.pkl

PPG-DaLiA pickles were created in Python 2; pickle.load needs encoding='latin1'.
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .wesad_adapter import WESADRecording, extract_windows

log = logging.getLogger("ppg_dalia_adapter")

# PPG-DaLiA activity codes (per the dataset description in the UCI release)
PPG_DALIA_ACTIVITIES = {
    0: "transient",
    1: "sitting",
    2: "stairs",
    3: "table_soccer",
    4: "cycling",
    5: "car_driving",
    6: "lunch_break",
    7: "walking",
    8: "working",
}

# Activities to keep (drop transient).
PPG_DALIA_VALID_STATES = tuple(k for k in PPG_DALIA_ACTIVITIES if k != 0)

# Sample rates (identical to WESAD for chest and wrist BVP)
PPG_DALIA_CHEST_FS = 700
PPG_DALIA_WRIST_PPG_FS = 64
PPG_DALIA_WRIST_ACC_FS = 32
PPG_DALIA_ACTIVITY_FS = 4


def _upsample_labels(activity_4hz: np.ndarray, target_n: int,
                     target_fs: int = PPG_DALIA_CHEST_FS,
                     source_fs: int = PPG_DALIA_ACTIVITY_FS) -> np.ndarray:
    """Upsample 4 Hz PPG-DaLiA activity labels to chest_fs (default 700 Hz).

    extract_windows in wesad_adapter assumes labels at chest_fs; PPG-DaLiA
    activity labels arrive at 4 Hz, so each activity sample covers 0.25 s and
    needs to be repeated 175 times to align with 700 Hz chest ECG.
    """
    factor = target_fs // source_fs
    upsampled = np.repeat(activity_4hz.astype(int), factor)
    if len(upsampled) < target_n:
        pad_value = int(upsampled[-1]) if len(upsampled) > 0 else 0
        upsampled = np.concatenate(
            [upsampled, np.full(target_n - len(upsampled), pad_value, dtype=int)]
        )
    else:
        upsampled = upsampled[:target_n]
    return upsampled


def load_ppg_dalia_pickle(pkl_path: Path) -> WESADRecording:
    """Load a PPG-DaLiA subject pickle as a WESADRecording-compatible record.

    The WESADRecording dataclass is reused because PPG-DaLiA has the same
    canonical fields (chest ECG at 700 Hz, wrist PPG at 64 Hz, wrist ACC at
    32 Hz, integer state labels at chest_fs). Only the label semantics differ;
    those are translated by `_remap_label_names` after window extraction.
    """
    pkl_path = Path(pkl_path)
    if not pkl_path.exists():
        raise FileNotFoundError(f"PPG-DaLiA pickle not found: {pkl_path}")
    with pkl_path.open("rb") as f:
        data = pickle.load(f, encoding="latin1")

    subject_id = pkl_path.stem  # e.g. S1.pkl -> "S1"

    chest_ecg = np.asarray(data["signal"]["chest"]["ECG"]).flatten()
    wrist_ppg = np.asarray(data["signal"]["wrist"]["BVP"]).flatten()
    wrist_acc = np.asarray(data["signal"]["wrist"]["ACC"])
    if wrist_acc.ndim == 1:
        wrist_acc = wrist_acc.reshape(-1, 3)

    activity_4hz = np.asarray(data["activity"]).flatten()
    labels_700hz = _upsample_labels(activity_4hz, target_n=len(chest_ecg))

    return WESADRecording(
        subject_id=subject_id,
        chest_ecg=chest_ecg,
        wrist_ppg=wrist_ppg,
        wrist_acc=wrist_acc,
        labels=labels_700hz,
        chest_fs=PPG_DALIA_CHEST_FS,
        wrist_ppg_fs=PPG_DALIA_WRIST_PPG_FS,
        wrist_acc_fs=PPG_DALIA_WRIST_ACC_FS,
    )


def to_daily_summary(rec: WESADRecording) -> pd.DataFrame:
    """One-row-per-subject summary for PPG-DaLiA.

    PPG-DaLiA is single-recording-per-subject, similar to WESAD's single-day
    treatment. The summary reports the per-activity duration distribution
    so cross-subject activity balance can be inspected.
    """
    activity_codes, activity_counts = np.unique(rec.labels, return_counts=True)
    activity_seconds = {
        f"seconds_{PPG_DALIA_ACTIVITIES.get(int(code), f'code_{int(code)}')}":
            float(count / rec.chest_fs)
        for code, count in zip(activity_codes, activity_counts)
    }
    row = {
        "subject_id": rec.subject_id,
        "n_chest_samples": int(len(rec.chest_ecg)),
        "n_wrist_ppg_samples": int(len(rec.wrist_ppg)),
        "total_seconds": float(len(rec.chest_ecg) / rec.chest_fs),
        **activity_seconds,
    }
    return pd.DataFrame([row])


def _remap_label_names(meta: pd.DataFrame) -> pd.DataFrame:
    """Replace WESAD label_name values with PPG-DaLiA activity names.

    extract_windows in wesad_adapter sets label_name via WESAD_LABELS, which
    has the wrong semantics for PPG-DaLiA codes (e.g., code 2 means 'stress'
    in WESAD but 'stairs' in PPG-DaLiA). We overwrite after extraction.
    """
    if "label" in meta.columns:
        meta = meta.copy()
        meta["label_name"] = (
            meta["label"].map(PPG_DALIA_ACTIVITIES).fillna("unknown")
        )
    return meta


def adapt_directory(ppg_dalia_dir: Path
                    ) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, pd.DataFrame]:
    """Walk a PPG-DaLiA directory of `S*` subdirs, return cohort daily + windows + meta.

    Returns
    -------
    daily_df : DataFrame with one row per subject (15 in PPG-DaLiA)
    ecg_windows : (n_windows, ecg_window_len) array, all subjects pooled
    ppg_windows : (n_windows, ppg_window_len) array, all subjects pooled
    window_meta : DataFrame with one row per window. Same schema as the
        WESAD adapter (window_idx, subject_id, label, label_name, start_seconds,
        end_seconds); label_name carries PPG-DaLiA activity names.
    """
    ppg_dalia_dir = Path(ppg_dalia_dir)
    if not ppg_dalia_dir.exists():
        raise FileNotFoundError(f"PPG-DaLiA directory not found: {ppg_dalia_dir}")
    subject_dirs = sorted([d for d in ppg_dalia_dir.iterdir()
                           if d.is_dir() and d.name.startswith("S")])
    if not subject_dirs:
        raise FileNotFoundError(
            f"No S* subdirectories found in {ppg_dalia_dir}. Expected layout: "
            "ppg_dalia_dir/S1/S1.pkl, ppg_dalia_dir/S2/S2.pkl, ..."
        )

    daily_rows: list[pd.DataFrame] = []
    ecg_chunks: list[np.ndarray] = []
    ppg_chunks: list[np.ndarray] = []
    meta_chunks: list[pd.DataFrame] = []

    for sd in subject_dirs:
        pkl = sd / f"{sd.name}.pkl"
        if not pkl.exists():
            log.warning("PPG-DaLiA: %s missing, skipping.", pkl)
            continue
        log.info("PPG-DaLiA: loading %s ...", pkl.name)
        rec = load_ppg_dalia_pickle(pkl)
        daily_rows.append(to_daily_summary(rec))
        # Reuse the WESAD extract_windows; pass all PPG-DaLiA activity codes
        ecg, ppg, meta = extract_windows(rec, states=PPG_DALIA_VALID_STATES)
        if len(meta) > 0:
            meta = _remap_label_names(meta)
            ecg_chunks.append(ecg)
            ppg_chunks.append(ppg)
            meta_chunks.append(meta)

    if not daily_rows:
        raise RuntimeError(f"No usable PPG-DaLiA subjects found in {ppg_dalia_dir}")

    daily_df = pd.concat(daily_rows, ignore_index=True)

    if ecg_chunks:
        ecg_arr = np.vstack(ecg_chunks)
        ppg_arr = np.vstack(ppg_chunks)
        window_meta = pd.concat(meta_chunks, ignore_index=True)
        # Reset window_idx globally so it's unique across subjects
        window_meta["window_idx"] = np.arange(len(window_meta))
    else:
        ecg_arr = np.empty((0, int(5.0 * PPG_DALIA_CHEST_FS)))
        ppg_arr = np.empty((0, int(5.0 * PPG_DALIA_WRIST_PPG_FS)))
        window_meta = pd.DataFrame()

    return daily_df, ecg_arr, ppg_arr, window_meta
