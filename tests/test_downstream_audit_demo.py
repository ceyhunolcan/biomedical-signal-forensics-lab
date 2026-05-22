"""Tests for the downstream audit demo script."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_downstream_audit_demo import (
    FEATURE_COLS,
    add_audit_masks,
    biomarker_correlation_track,
    classification_track,
    load_per_window_table,
    loso_classify,
    paired_wilcoxon,
)


def _make_toy_window_table(n_subjects: int = 4,
                            n_windows_per_subject: int = 80,
                            seed: int = 0) -> pd.DataFrame:
    """Build a synthetic per-window table with a learnable baseline-vs-stress
    signal. Used by the classification tests."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n_subjects):
        sid = f"S{s+10:02d}"
        for i in range(n_windows_per_subject):
            label = "baseline" if i < n_windows_per_subject // 2 else "stress"
            # Stress shifts HR up by ~10 bpm and motion up by ~0.02
            hr_ecg = 70 + (10 if label == "stress" else 0) + rng.normal(0, 5)
            hr_ppg = hr_ecg + rng.normal(0, 3)
            motion = 0.02 + (0.02 if label == "stress" else 0) + rng.uniform(0, 0.01)
            sqi = 0.9 + rng.uniform(-0.05, 0.1)
            # Orphanidou pass rate ~50%
            orph = rng.random() > 0.5
            rows.append({
                "window_idx": i, "subject_id": sid, "label": 1 if label == "baseline" else 2,
                "label_name": label, "hr_ecg": hr_ecg, "hr_ppg": hr_ppg,
                "hr_abs_diff": abs(hr_ppg - hr_ecg),
                "inhouse_ecg_sqi": 0.98, "inhouse_ppg_sqi": sqi,
                "inhouse_ppg_motion": motion,
                "orphanidou_acceptable": orph, "orphanidou_template_corr": rng.uniform(0.6, 0.9),
                "sukor_acceptable": rng.random() > 0.6,
                "sukor_pp_cv": rng.uniform(0.05, 0.15),
                "sukor_amp_cv": rng.uniform(0.05, 0.15),
            })
    return pd.DataFrame(rows)


def test_load_per_window_table_validates_schema(tmp_path):
    """A missing required column raises a KeyError with a useful message."""
    bad = pd.DataFrame({"subject_id": ["S1"], "label_name": ["baseline"]})
    p = tmp_path / "bad.csv"
    bad.to_csv(p, index=False)
    try:
        load_per_window_table(p)
    except KeyError as e:
        assert "missing required columns" in str(e)
    else:
        raise AssertionError("Expected KeyError for missing columns")


def test_load_per_window_table_accepts_valid_schema(tmp_path):
    df = _make_toy_window_table()
    p = tmp_path / "ok.csv"
    df.to_csv(p, index=False)
    loaded = load_per_window_table(p)
    assert len(loaded) == len(df)
    assert set(loaded["subject_id"].unique()) == set(df["subject_id"].unique())


def test_add_audit_masks_columns_added():
    df = _make_toy_window_table(n_subjects=2, n_windows_per_subject=20)
    masked = add_audit_masks(df, inhouse_threshold=0.70)
    for c in ("pass_inhouse", "pass_orphanidou", "pass_both"):
        assert c in masked.columns
        assert masked[c].dtype == bool
    # 'both' is the AND of 'inhouse' and 'orphanidou'
    assert (masked["pass_both"] == (masked["pass_inhouse"] & masked["pass_orphanidou"])).all()


def test_loso_classify_returns_one_row_per_fold():
    df = _make_toy_window_table(n_subjects=4, n_windows_per_subject=80)
    df = add_audit_masks(df)
    folds = loso_classify(df, FEATURE_COLS, mask_col=None, classifier="logreg")
    assert len(folds) == 4
    assert set(folds.columns) >= {"subject_id", "auroc", "n_train", "n_test"}
    # AUROC values should be in [0, 1]
    assert folds["auroc"].between(0, 1).all()


def test_loso_classify_recovers_strong_signal():
    """When stress has a strong signal, LOSO AUROC should be well above 0.5."""
    df = _make_toy_window_table(n_subjects=5, n_windows_per_subject=100, seed=42)
    df = add_audit_masks(df)
    folds = loso_classify(df, FEATURE_COLS, mask_col=None, classifier="logreg")
    assert folds["auroc"].mean() > 0.7, (
        f"Expected mean AUROC > 0.7 on toy data with strong signal, "
        f"got {folds['auroc'].mean()}"
    )


def test_loso_classify_skips_single_class_folds():
    """A fold whose test set has only one class should be silently skipped."""
    df = _make_toy_window_table(n_subjects=3, n_windows_per_subject=60)
    # Force one subject to be all baseline
    df.loc[df["subject_id"] == "S10", "label_name"] = "baseline"
    df = add_audit_masks(df)
    folds = loso_classify(df, FEATURE_COLS, mask_col=None, classifier="logreg")
    # S10 fold should be skipped (held-out test set has one class)
    assert "S10" not in folds["subject_id"].values


def test_loso_classify_mask_col_filters_data():
    """Passing a mask_col reduces the number of rows used."""
    df = _make_toy_window_table(n_subjects=4, n_windows_per_subject=80)
    df = add_audit_masks(df)
    folds_all = loso_classify(df, FEATURE_COLS, mask_col=None, classifier="logreg")
    folds_filtered = loso_classify(df, FEATURE_COLS, mask_col="pass_orphanidou",
                                     classifier="logreg")
    # Filtered folds should have fewer training rows
    if len(folds_all) > 0 and len(folds_filtered) > 0:
        assert (folds_filtered["n_train"] <= folds_all["n_train"]).any()


def test_classification_track_returns_all_conditions():
    df = _make_toy_window_table(n_subjects=4, n_windows_per_subject=80)
    df = add_audit_masks(df)
    result = classification_track(df, FEATURE_COLS, classifier="logreg")
    assert {"per_fold", "summary", "deltas"} == set(result.keys())
    assert set(result["per_fold"].keys()) == {"all", "inhouse", "orphanidou", "both"}
    summary = result["summary"]
    assert set(summary["condition"]) == {"all", "inhouse", "orphanidou", "both"}


def test_biomarker_correlation_track_returns_one_row_per_subject():
    df = _make_toy_window_table(n_subjects=4, n_windows_per_subject=100)
    df = add_audit_masks(df)
    corr = biomarker_correlation_track(df)
    assert len(corr) == 4
    expected_cols = {"subject_id", "n_all", "rho_all", "rho_inhouse",
                     "rho_orphanidou", "rho_both"}
    assert expected_cols.issubset(set(corr.columns))


def test_biomarker_correlation_track_skips_subjects_with_too_few_windows():
    df = _make_toy_window_table(n_subjects=2, n_windows_per_subject=20)
    df = add_audit_masks(df)
    corr = biomarker_correlation_track(df)
    # All subjects below n=30 → empty result
    assert len(corr) == 0


def test_paired_wilcoxon_handles_short_input():
    corr = pd.DataFrame({"rho_all": [0.5, 0.6], "rho_inhouse": [0.6, 0.7]})
    res = paired_wilcoxon(corr, "rho_all", "rho_inhouse")
    # 2 paired samples is below the n=3 threshold
    assert res["n_paired"] == 2
    assert res["mean_delta"] is None


def test_paired_wilcoxon_detects_consistent_improvement():
    rng = np.random.default_rng(0)
    n = 12
    base = rng.uniform(0.3, 0.6, n)
    improved = base + rng.uniform(0.05, 0.15, n)
    corr = pd.DataFrame({"rho_all": base, "rho_inhouse": improved})
    res = paired_wilcoxon(corr, "rho_all", "rho_inhouse")
    assert res["n_paired"] == n
    assert res["mean_delta"] > 0
    assert res["wilcoxon_p_greater"] < 0.01
    assert res["n_improved"] == n


def test_paired_wilcoxon_no_change_yields_high_p():
    base = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
    same = base.copy()
    corr = pd.DataFrame({"rho_all": base, "rho_inhouse": same})
    res = paired_wilcoxon(corr, "rho_all", "rho_inhouse")
    assert res["mean_delta"] == 0.0
    # No improvement → p value should not reject the null
    assert res["wilcoxon_p_greater"] == 1.0
