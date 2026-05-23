"""Real-data adapter tests using synthetic foreign-schema fixtures."""
import numpy as np
import pandas as pd

from biomedical_signal_forensics_lab.data.real_data_adapter import (
    FitbitLikeAdapter, EmpaticaLikeAdapter, GenericDailySummaryAdapter,
    recalibrate_detector,
)


def _fitbit_fixture(n=30):
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "user_id": [f"FB{i:03d}" for i in range(n)],
        "summary_date": pd.date_range("2024-03-01", periods=n).strftime("%Y-%m-%d"),
        "tracker": rng.choice(["Charge5", "Versa3"], size=n),
        "resting_heart_rate": rng.normal(64, 6, n),
        "rmssd": rng.normal(40, 8, n),
        "sdnn": rng.normal(55, 10, n),
        "steps": rng.integers(2000, 18000, n),
        "very_active_minutes": rng.integers(0, 90, n),
        "minutes_asleep": rng.normal(420, 60, n),         # minutes → hours
        "sleep_efficiency_pct": rng.normal(85, 5, n),      # percent → fraction
        "ambient_temp_f": rng.normal(72, 8, n),            # F → C
        "humidity_pct": rng.normal(55, 12, n),
        "aqi_us": rng.integers(20, 120, n),
        "wear_minutes": rng.integers(800, 1440, n),
        "is_missing": (rng.random(n) < 0.1).astype(int),
    })


def test_fitbit_adapter_produces_canonical_columns():
    df = _fitbit_fixture()
    out, rep = FitbitLikeAdapter().adapt(df)
    assert "participant_id" in out.columns
    assert "resting_hr" in out.columns
    assert "hrv_rmssd" in out.columns
    assert rep.n_rows_out > 0
    # sleep duration should be in hours now (≈ 6–8), not minutes
    assert out["sleep_duration"].between(0, 14).all()
    # sleep efficiency should be in [0, 1]
    assert out["sleep_efficiency"].between(0, 1).all()
    # temperature should be plausible Celsius
    assert out["temperature_c"].between(-20, 50).all()


def test_fitbit_adapter_drops_out_of_range():
    df = _fitbit_fixture()
    df.loc[0, "resting_heart_rate"] = 250  # implausible
    out, rep = FitbitLikeAdapter().adapt(df)
    assert rep.n_rows_dropped >= 1
    assert "resting_hr_out_of_range" in rep.dropped_reason_counts


def test_empatica_adapter_renames_columns():
    rng = np.random.default_rng(1)
    n = 20
    df = pd.DataFrame({
        "subject": [f"E{i:03d}" for i in range(n)],
        "day": pd.date_range("2024-04-01", periods=n).strftime("%Y-%m-%d"),
        "device_model": ["E4"] * n,
        "hr_rest_bpm": rng.normal(62, 4, n),
        "hrv_rmssd_ms": rng.normal(45, 8, n),
        "hrv_sdnn_ms": rng.normal(60, 10, n),
        "step_total": rng.integers(3000, 14000, n),
        "active_min": rng.integers(0, 100, n),
        "sleep_hours": rng.normal(7.5, 0.8, n),
        "sleep_eff_frac": rng.uniform(0.7, 0.95, n),
        "amb_temp_c": rng.normal(22, 3, n),
        "amb_humidity_frac": rng.uniform(0.3, 0.7, n),
        "aqi": rng.integers(20, 100, n),
        "wear_min": rng.integers(800, 1440, n),
        "non_wear_flag": np.zeros(n, dtype=int),
    })
    out, rep = EmpaticaLikeAdapter().adapt(df)
    assert "participant_id" in out.columns
    assert "hrv_rmssd" in out.columns
    assert rep.n_rows_out == n


def test_generic_adapter_pass_through():
    df = pd.DataFrame({
        "participant_id": ["X1", "X2"],
        "date": ["2024-01-01", "2024-01-02"],
        "resting_hr": [60.0, 65.0],
        "hrv_rmssd": [40.0, 38.0],
    })
    out, _ = GenericDailySummaryAdapter().adapt(df)
    assert (out["participant_id"] == ["X1", "X2"]).all()


def test_recalibrate_detector_finds_better_threshold():
    rng = np.random.default_rng(42)
    # Build labeled "signals" whose mean magnitude predicts the label cleanly
    signals = []
    labels = []
    for _ in range(100):
        is_artifact = rng.random() < 0.5
        scale = 0.05 if not is_artifact else 0.6
        signals.append(rng.normal(0, scale, 256))
        labels.append(int(is_artifact))
    labels = np.array(labels)

    def severity(sig):
        return float(np.clip(np.std(sig) / 0.5, 0, 1))

    res = recalibrate_detector(severity, signals, labels,
                               original_threshold=0.5,
                               detector_name="toy_motion")
    assert res.f1_at_learned > 0.7
    assert res.detector_name == "toy_motion"
    assert 0 < res.learned_threshold < 1
    assert res.n_labels == 100
