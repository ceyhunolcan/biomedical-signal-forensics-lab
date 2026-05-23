"""Generator stress-test module tests."""
import pandas as pd

from biomedical_signal_forensics_lab.data.generator_stress_test import (
    stress_test, check_monotonic_response,
)


def test_stress_test_returns_expected_schema():
    """Use a tiny cohort to keep the test fast."""
    table = stress_test(n_participants=20, n_days=14)
    for col in ("effect", "strength", "coefficient", "measurement_name",
                "measurement_value", "n_participants", "n_days"):
        assert col in table.columns
    assert len(table) == 9  # 3 effects × 3 strengths


def test_stress_test_responses_are_monotonic():
    """If the framework is sensitive to the injected effects, the measured
    response should move monotonically with the injected coefficient."""
    table = stress_test(n_participants=30, n_days=21)
    monot = check_monotonic_response(table)
    # All three effects should pass on the default seed and small cohort
    failures = monot[monot["monotonic"] == False]
    assert len(failures) == 0, f"non-monotonic effects: {list(failures['effect'])}"


def test_stress_test_device_offset_matches_injected_value():
    """When we inject a 10 bpm device-B offset, the empirical offset should
    be roughly 10 bpm. Allow ±2 bpm of generator noise."""
    table = stress_test(n_participants=40, n_days=21)
    row = table[(table.effect == "device_b_hr_offset")
                & (table.strength == "high")].iloc[0]
    assert abs(row.measurement_value - 10.0) < 2.0
