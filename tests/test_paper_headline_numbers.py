"""Regression test that locks the paper's headline consensus-reject figures to
the committed window tables.

The manuscript and Figure 1 report that the three published wrist-PPG quality
methods (Orphanidou, Sukor, Elgendi) consensus-reject 2,935 windows (44.6%) on
WESAD and 8,100 windows (43.1%) on PPG-DaLiA, with the per-method pass rates
shown in Section 3.2. These numbers are recomputed here from the released data
so that any future change to the data or the acceptance logic that would move
the published figures is caught instead of drifting silently.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLES = {
    "WESAD": ROOT / "results" / "real_data" / "wesad_deep" / "window_table.csv",
    "PPG-DaLiA": ROOT / "results" / "real_data" / "ppg_dalia" / "window_table.csv",
}
ACCEPT_COLS = ["orphanidou_acceptable", "sukor_acceptable", "elgendi_acceptable"]

# name -> (n_windows, consensus_reject_count, consensus_reject_pct)
EXPECTED = {
    "WESAD": (6585, 2935, 44.6),
    "PPG-DaLiA": (18781, 8100, 43.1),
}
# name -> per-method acceptance (pass) rate in percent, rounded to one decimal
EXPECTED_PASS_PCT = {
    "WESAD": {"orphanidou_acceptable": 25.6, "sukor_acceptable": 25.5,
              "elgendi_acceptable": 21.5},
    "PPG-DaLiA": {"orphanidou_acceptable": 28.2, "sukor_acceptable": 27.1,
                  "elgendi_acceptable": 22.0},
}


def _load(name):
    return pd.read_csv(TABLES[name])


def test_window_tables_present():
    for name, path in TABLES.items():
        assert path.exists(), f"{name}: missing window table at {path}"


def test_acceptance_columns_have_no_missing_values():
    # The consensus computation treats each column as boolean, so a missing
    # value would silently shift the counts. Guard against it.
    for name in TABLES:
        df = _load(name)
        for col in ACCEPT_COLS:
            assert col in df.columns, f"{name}: missing column {col}"
            assert int(df[col].isna().sum()) == 0, f"{name}: {col} has missing values"


def test_consensus_reject_counts_match_paper():
    for name, (n_expected, reject_expected, pct_expected) in EXPECTED.items():
        df = _load(name)
        assert len(df) == n_expected, f"{name}: window count {len(df)} (expected {n_expected})"
        o = df["orphanidou_acceptable"].astype(bool)
        s = df["sukor_acceptable"].astype(bool)
        e = df["elgendi_acceptable"].astype(bool)
        reject_count = int((~o & ~s & ~e).sum())
        assert reject_count == reject_expected, (
            f"{name}: consensus-reject count {reject_count} (expected {reject_expected})"
        )
        pct = round(100 * reject_count / len(df), 1)
        assert pct == pct_expected, f"{name}: consensus-reject {pct}% (expected {pct_expected}%)"


def test_per_method_pass_rates_match_paper():
    for name, expected in EXPECTED_PASS_PCT.items():
        df = _load(name)
        for col, pct_expected in expected.items():
            pct = round(100 * df[col].astype(bool).mean(), 1)
            assert pct == pct_expected, (
                f"{name}: {col} pass rate {pct}% (expected {pct_expected}%)"
            )


if __name__ == "__main__":
    test_window_tables_present()
    test_acceptance_columns_have_no_missing_values()
    test_consensus_reject_counts_match_paper()
    test_per_method_pass_rates_match_paper()
    print("all paper-headline-number checks passed")
