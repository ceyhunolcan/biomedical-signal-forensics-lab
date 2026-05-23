"""Each artifact detector should fire on a clearly degraded signal and stay quiet on a clean one."""
import numpy as np

from biomedical_signal_forensics_lab.artifacts.motion_artifacts import detect as detect_motion
from biomedical_signal_forensics_lab.artifacts.sensor_dropout import detect as detect_dropout
from biomedical_signal_forensics_lab.artifacts.signal_noise import detect_noise_spikes, detect_flatline
from biomedical_signal_forensics_lab.artifacts.timestamp_irregularity import detect as detect_timing
from biomedical_signal_forensics_lab.artifacts.artifact_classifier import evaluate_window


def test_motion_fires_on_noisy_signal():
    rng = np.random.default_rng(0)
    clean = np.sin(np.linspace(0, 20 * np.pi, 320))
    dirty = clean + 2.0 * rng.standard_normal(clean.size)
    quiet = detect_motion(clean, fs=64)
    loud = detect_motion(dirty, fs=64)
    assert loud.severity >= quiet.severity


def test_dropout_detector_finds_zero_runs():
    sig = np.ones(500)
    sig[100:200] = 0.0  # 100-sample dropout, above default threshold 32
    finding = detect_dropout(sig)
    assert finding.flag == 1
    assert finding.severity > 0


def test_dropout_quiet_when_signal_present():
    sig = 0.5 + 0.1 * np.sin(np.linspace(0, 6 * np.pi, 500))
    finding = detect_dropout(sig)
    assert finding.flag == 0


def test_noise_spike_detection():
    rng = np.random.default_rng(1)
    sig = 0.05 * rng.standard_normal(1000)
    sig[200] = 20.0
    sig[700] = -18.0
    finding = detect_noise_spikes(sig)
    assert finding.flag == 1


def test_flatline_detection():
    sig = np.concatenate([
        np.sin(np.linspace(0, 6 * np.pi, 200)),
        np.zeros(200),
        np.sin(np.linspace(0, 6 * np.pi, 200)),
    ])
    finding = detect_flatline(sig, min_flat_samples=64)
    assert finding.flag == 1


def test_timestamp_irregularity_on_jittery_grid():
    rng = np.random.default_rng(2)
    fs = 64
    expected_ms = 1000.0 / fs
    clean_ts = np.cumsum(np.full(200, expected_ms))
    jitter_ts = np.cumsum(expected_ms + 6.0 * rng.standard_normal(200))
    quiet = detect_timing(clean_ts, expected_interval_ms=expected_ms)
    loud = detect_timing(jitter_ts, expected_interval_ms=expected_ms)
    assert loud.severity > quiet.severity


def test_window_classifier_returns_named_report():
    rng = np.random.default_rng(3)
    sig = 0.1 * rng.standard_normal(320)
    report = evaluate_window(signal=sig, fs=64)
    assert hasattr(report, "artifact_burden")
    assert 0.0 <= report.artifact_burden <= 1.0
    assert hasattr(report, "any_artifact")
