"""Causal-inference module tests."""
import numpy as np
import pandas as pd

from src.confounding.causal_inference import (
    DAG, default_wearable_dag, g_computation, aipw, screening_vs_adjusted_table,
)


def test_dag_back_door_returns_common_causes():
    g = DAG()
    # X ← C → Y plus X → Y
    g.add_edge("C", "X")
    g.add_edge("C", "Y")
    g.add_edge("X", "Y")
    adj = g.back_door_adjustment_set("X", "Y")
    assert "C" in adj


def test_dag_excludes_descendants_of_treatment():
    g = DAG()
    g.add_edge("X", "M")  # M is descendant of X
    g.add_edge("M", "Y")
    g.add_edge("X", "Y")
    adj = g.back_door_adjustment_set("X", "Y")
    # M is a descendant of X, must not be in adjustment set
    assert "M" not in adj


def test_default_wearable_dag_has_expected_nodes():
    g = default_wearable_dag()
    for n in ("heat_index", "hrv_rmssd", "stress_proxy", "device_type"):
        assert n in g.nodes()


def _confounded_fixture(n=500, seed=0):
    """X ← C → Y, X → Y with known effect size 2.0 (binarized: roughly 2.0)."""
    rng = np.random.default_rng(seed)
    C = rng.normal(0, 1, n)
    X = 0.6 * C + rng.normal(0, 1, n)
    Y = 2.0 * (X > X.mean()).astype(float) + 1.5 * C + rng.normal(0, 1, n)
    return pd.DataFrame({"X": X, "Y": Y, "C": C})


def test_g_computation_recovers_adjusted_effect():
    df = _confounded_fixture(n=400)
    est = g_computation(df, treatment="X", outcome="Y", adjustment_set=["C"],
                        n_bootstrap=50)
    # Effect of X (binarized) on Y is ~2.0 after adjusting for C
    assert abs(est.point_estimate - 2.0) < 0.5
    assert est.ci_low < est.point_estimate < est.ci_high


def test_aipw_recovers_adjusted_effect():
    df = _confounded_fixture(n=500)
    est = aipw(df, treatment="X", outcome="Y", adjustment_set=["C"],
               n_bootstrap=50)
    assert abs(est.point_estimate - 2.0) < 0.6
    assert est.ci_low < est.point_estimate < est.ci_high


def test_aipw_handles_empty_adjustment_set():
    df = _confounded_fixture(n=200)
    est = aipw(df, treatment="X", outcome="Y", adjustment_set=[],
               n_bootstrap=20)
    # No adjustment → biased estimate, but the function should not crash
    assert np.isfinite(est.point_estimate)


def test_screening_vs_adjusted_table_returns_frame():
    rng = np.random.default_rng(0)
    n = 300
    df = pd.DataFrame({
        "heat_index": rng.normal(20, 5, n),
        "hrv_rmssd": rng.normal(45, 8, n),
        "stress_proxy": rng.uniform(0, 1, n),
        "active_minutes": rng.integers(0, 100, n),
        "aqi": rng.normal(50, 10, n),
    })
    out = screening_vs_adjusted_table(df, pairs=[("heat_index", "hrv_rmssd")])
    assert len(out) == 1
    assert "aipw_estimate" in out.columns
    assert "screening_r" in out.columns
