"""Adapters that bring real wearable datasets into the canonical schema.

The audit pipeline expects a daily-summary CSV with a fixed column vocabulary
(see src/data/validation.py for the contract). Real wearable releases use
their own column names, units, and date formats. This module provides:

- a `RealDataAdapter` base class that maps source columns onto canonical
  names, validates the result, and writes a schema-compliant CSV;
- three reference adapters (Fitbit-like CSV, Empatica E4-like aggregated CSV,
  generic WFDB-like daily summary) that show the pattern;
- a `recalibrate_detectors` helper that takes a small labeled artifact dataset
  and refits each detector's threshold by optimizing F1 on the labels.

No real dataset is bundled. The adapters are tested against a synthetic
'foreign-schema' fixture that the unit tests construct on the fly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from src.data.validation import REQUIRED_COLUMNS, PHYSIO_RANGES, ValidationResult
from src.utils.logging import get_logger

log = get_logger("real_data_adapter")


# ---------------------------------------------------------------------------
# Base adapter
# ---------------------------------------------------------------------------

@dataclass
class AdapterReport:
    n_rows_in: int
    n_rows_out: int
    n_rows_dropped: int
    dropped_reason_counts: dict[str, int]
    validation: ValidationResult


class RealDataAdapter(ABC):
    """Convert a foreign-schema dataframe into our canonical daily-summary schema.

    Subclasses provide `column_map` (foreign → canonical) and `transform_row`
    if any per-row transformation is needed beyond renaming (unit conversion,
    timezone normalization, etc.). The base class handles validation and
    out-of-range filtering.
    """

    column_map: dict[str, str] = {}
    drop_out_of_range: bool = True

    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source identifier for logging."""

    def transform_row(self, row: pd.Series) -> pd.Series:  # noqa: D401
        """Override if per-row conversion is needed."""
        return row

    def adapt(self, df: pd.DataFrame) -> tuple[pd.DataFrame, AdapterReport]:
        n_in = len(df)
        # How many of our column_map source columns are actually present?
        matched = [k for k in self.column_map if k in df.columns]
        if self.column_map and not matched:
            log.warning(
                "Adapter[%s]: NONE of the expected source columns were found in "
                "the input (%s). All canonical columns will be NaN. Check your "
                "column_map or use GenericDailySummaryAdapter if the schema "
                "already matches.",
                self.source_name(), list(self.column_map.keys())[:5],
            )
        # If a canonical target column already exists in the input AND a source
        # column maps to it, the rename would produce two columns with the same
        # name. That breaks downstream code in subtle ways. Drop the pre-existing
        # canonical column and let the renamed source column take its place.
        # Warn so the user knows.
        df = df.copy()
        collisions = [
            target for source, target in self.column_map.items()
            if source in df.columns and target in df.columns and source != target
        ]
        if collisions:
            log.warning(
                "Adapter[%s]: dropping pre-existing canonical columns %s "
                "because source columns also map to them.",
                self.source_name(), collisions,
            )
            df = df.drop(columns=collisions)
        # Rename
        renamed = df.rename(columns=self.column_map).copy()
        # Apply row transforms
        if self.transform_row is not RealDataAdapter.transform_row:
            renamed = renamed.apply(self.transform_row, axis=1)
        # Fill missing canonical columns with NaN so validation can flag them
        for canon in REQUIRED_COLUMNS:
            if canon not in renamed.columns:
                renamed[canon] = np.nan
        # Range filtering
        dropped_reasons: dict[str, int] = {}
        if self.drop_out_of_range:
            mask = pd.Series(True, index=renamed.index)
            for col, (lo, hi) in PHYSIO_RANGES.items():
                if col in renamed.columns:
                    col_mask = renamed[col].between(lo, hi) | renamed[col].isna()
                    n_bad = int((~col_mask).sum())
                    if n_bad > 0:
                        dropped_reasons[f"{col}_out_of_range"] = n_bad
                    mask &= col_mask
            renamed = renamed[mask].reset_index(drop=True)
        # Validate
        from src.data.validation import validate
        vres = validate(renamed)
        n_out = len(renamed)
        log.info(
            "Adapter[%s]: %d in → %d out (%d dropped). validation=%s",
            self.source_name(), n_in, n_out, n_in - n_out,
            "OK" if vres.ok else "ISSUES",
        )
        return renamed, AdapterReport(
            n_rows_in=n_in, n_rows_out=n_out, n_rows_dropped=n_in - n_out,
            dropped_reason_counts=dropped_reasons, validation=vres,
        )


# ---------------------------------------------------------------------------
# Reference adapters
# ---------------------------------------------------------------------------

class FitbitLikeAdapter(RealDataAdapter):
    """For Fitbit-style daily exports: lowercase snake_case, US units in some columns."""

    column_map = {
        "user_id": "participant_id",
        "summary_date": "date",
        "tracker": "device_type",
        "resting_heart_rate": "resting_hr",
        "rmssd": "hrv_rmssd",
        "sdnn": "hrv_sdnn",
        "steps": "step_count",
        "very_active_minutes": "active_minutes",
        "minutes_asleep": "sleep_duration",   # special: needs conversion to hours
        "sleep_efficiency_pct": "sleep_efficiency",  # special: percent → fraction
        "ambient_temp_f": "temperature_c",  # special: F → C
        "humidity_pct": "humidity",
        "aqi_us": "aqi",
        "wear_minutes": "wearable_minutes",
        "is_missing": "missing_wearable_flag",
    }

    def source_name(self) -> str:
        return "fitbit-like"

    def transform_row(self, row: pd.Series) -> pd.Series:
        if "sleep_duration" in row and pd.notna(row.get("sleep_duration")):
            row["sleep_duration"] = float(row["sleep_duration"]) / 60.0  # min → hr
        if "sleep_efficiency" in row and pd.notna(row.get("sleep_efficiency")):
            v = float(row["sleep_efficiency"])
            if v > 1.5:  # percent → fraction
                row["sleep_efficiency"] = v / 100.0
        if "temperature_c" in row and pd.notna(row.get("temperature_c")):
            row["temperature_c"] = (float(row["temperature_c"]) - 32.0) * 5.0 / 9.0
        if "humidity" in row and pd.notna(row.get("humidity")):
            v = float(row["humidity"])
            if v > 1.5:
                row["humidity"] = v / 100.0
        return row


class EmpaticaLikeAdapter(RealDataAdapter):
    """For Empatica E4 aggregated daily summaries (illustrative)."""

    column_map = {
        "subject": "participant_id",
        "day": "date",
        "device_model": "device_type",
        "hr_rest_bpm": "resting_hr",
        "hrv_rmssd_ms": "hrv_rmssd",
        "hrv_sdnn_ms": "hrv_sdnn",
        "step_total": "step_count",
        "active_min": "active_minutes",
        "sleep_hours": "sleep_duration",
        "sleep_eff_frac": "sleep_efficiency",
        "amb_temp_c": "temperature_c",
        "amb_humidity_frac": "humidity",
        "aqi": "aqi",
        "wear_min": "wearable_minutes",
        "non_wear_flag": "missing_wearable_flag",
    }

    def source_name(self) -> str:
        return "empatica-like"


class GenericDailySummaryAdapter(RealDataAdapter):
    """Pass-through adapter when columns already match (or after a manual rename)."""

    column_map = {}

    def source_name(self) -> str:
        return "generic-daily-summary"


# ---------------------------------------------------------------------------
# Detector recalibration
# ---------------------------------------------------------------------------

@dataclass
class CalibrationResult:
    detector_name: str
    original_threshold: float
    learned_threshold: float
    f1_at_learned: float
    n_labels: int
    notes: str = ""


def _f1_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    if tp + fp == 0 or tp + fn == 0:
        return 0.0
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def recalibrate_detector(
    severity_scorer: Callable[[np.ndarray], float],
    signals: Iterable[np.ndarray],
    labels: np.ndarray,
    candidate_thresholds: np.ndarray | None = None,
    original_threshold: float = 0.5,
    detector_name: str = "detector",
) -> CalibrationResult:
    """Pick the threshold on `severity_scorer` output that maximizes F1 on labels.

    Parameters
    ----------
    severity_scorer
        Callable mapping one signal window → severity in [0, 1].
    signals
        Iterable of signal windows.
    labels
        1D array of 0/1 ground-truth artifact labels, aligned with signals.
    candidate_thresholds
        Thresholds to try. Default: 0.05 … 0.95 step 0.05.
    """
    if candidate_thresholds is None:
        candidate_thresholds = np.arange(0.05, 0.96, 0.05)
    sev = np.array([severity_scorer(s) for s in signals])
    labels = np.asarray(labels).astype(int)
    best_t, best_f1 = float(original_threshold), -1.0
    for t in candidate_thresholds:
        pred = (sev > t).astype(int)
        f = _f1_score(labels, pred)
        if f > best_f1:
            best_f1 = f
            best_t = float(t)
    return CalibrationResult(
        detector_name=detector_name,
        original_threshold=float(original_threshold),
        learned_threshold=best_t,
        f1_at_learned=float(best_f1),
        n_labels=len(labels),
        notes=f"searched {len(candidate_thresholds)} thresholds",
    )


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

def adapt_csv(input_csv: str | Path, adapter: RealDataAdapter,
              output_csv: str | Path) -> AdapterReport:
    """Read a foreign CSV, run the adapter, write the canonical CSV."""
    df = pd.read_csv(input_csv)
    out, rep = adapter.adapt(df)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False)
    log.info("Wrote canonical CSV → %s (%d rows)", output_csv, len(out))
    return rep
