"""Downstream audit demo: does the framework's signal-quality audit improve
downstream model performance?

Two tracks:

  (A) Classification. Baseline-vs-stress per-window classifier on wrist PPG
      features (HR, motion, SQI). Leave-one-subject-out cross-validation
      (LOSO; the only valid protocol on WESAD given how few subjects there
      are). Train under four data-filter conditions, all with identical
      hyperparameters:
          - all_windows: no audit
          - inhouse: keep windows where in-house SQI passes its default 0.70
          - orphanidou: keep windows where Orphanidou 2015 passes
          - both: keep windows where both in-house AND Orphanidou pass

      Report per-fold AUROC, macro-average, and the paired delta vs all.

  (B) Biomarker correlation. Per-subject Spearman correlation between wrist
      PPG-derived HR and chest ECG-derived HR. Two conditions: all windows,
      audit-passing only. Report per-subject ρ, paired Wilcoxon across
      subjects.

The script is self-contained: it loads WESAD, extracts windows, computes the
audit columns, runs the classifier, runs the correlation analysis, writes
CSVs and a 4-panel figure. ~40 seconds on a modern laptop CPU at n=15.

Outputs land under results/downstream_demo/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from src.utils.logging import get_logger
from src.utils.paths import ensure_dir

log = get_logger("downstream_audit_demo")

# --------------------------------------------------------------------------
# 1. Feature extraction from the existing per-window table
# --------------------------------------------------------------------------

FEATURE_COLS = [
    "hr_ppg",          # wrist-PPG-derived HR
    "inhouse_ppg_motion",  # motion artifact score
    "inhouse_ppg_sqi", # in-house PPG SQI
]


def load_per_window_table(path: Path) -> pd.DataFrame:
    """Load the per-window table from run_deep_real_analysis.py output.

    Required columns: subject_id, label_name, hr_ppg, hr_ecg, ppg_motion,
    inhouse_ppg_sqi, orphanidou_acceptable.
    """
    df = pd.read_csv(path)
    needed = {"subject_id", "label_name", "hr_ppg", "hr_ecg",
              "inhouse_ppg_motion", "inhouse_ppg_sqi", "orphanidou_acceptable"}
    missing = needed - set(df.columns)
    if missing:
        raise KeyError(
            f"per-window table missing required columns: {sorted(missing)}. "
            "Run scripts/run_deep_real_analysis.py first."
        )
    return df


def add_audit_masks(df: pd.DataFrame,
                    inhouse_threshold: float = 0.70) -> pd.DataFrame:
    """Add boolean audit-pass columns for each variant."""
    df = df.copy()
    df["pass_inhouse"] = df["inhouse_ppg_sqi"] >= inhouse_threshold
    df["pass_orphanidou"] = df["orphanidou_acceptable"].astype(bool)
    df["pass_both"] = df["pass_inhouse"] & df["pass_orphanidou"]
    return df


# --------------------------------------------------------------------------
# 2. Classification track (LOSO baseline vs stress)
# --------------------------------------------------------------------------

def loso_classify(df: pd.DataFrame,
                  feature_cols: list[str],
                  mask_col: str | None,
                  classifier: str = "logreg",
                  seed: int = 42,
                  ) -> pd.DataFrame:
    """Run leave-one-subject-out classification of baseline vs stress.

    Args:
        df: per-window table containing subject_id, label_name, features,
            and (if mask_col is not None) a boolean column to filter on.
        feature_cols: which columns to feed the classifier.
        mask_col: if given, restrict training AND evaluation to rows where
            this boolean column is True. If None, use all rows.
        classifier: 'logreg' or 'rf'.
        seed: RNG seed for the classifier.

    Returns:
        Per-fold dataframe with columns: subject_id, n_train, n_test, auroc,
        n_train_pos, n_train_neg, n_test_pos, n_test_neg.
    """
    sub = df[df["label_name"].isin(["baseline", "stress"])].copy()
    sub["y"] = (sub["label_name"] == "stress").astype(int)
    if mask_col is not None:
        sub = sub[sub[mask_col]].reset_index(drop=True)

    sub = sub.dropna(subset=feature_cols + ["y"]).reset_index(drop=True)

    rows = []
    for sid in sorted(sub["subject_id"].unique()):
        train = sub[sub["subject_id"] != sid]
        test = sub[sub["subject_id"] == sid]
        # Skip folds where either split has only one class
        if train["y"].nunique() < 2 or test["y"].nunique() < 2:
            continue
        if len(test) < 10:
            continue
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(train[feature_cols].values)
        X_te = scaler.transform(test[feature_cols].values)
        y_tr = train["y"].to_numpy()
        y_te = test["y"].to_numpy()
        if classifier == "rf":
            clf = RandomForestClassifier(
                n_estimators=200, max_depth=8, random_state=seed, n_jobs=1)
        else:
            clf = LogisticRegression(max_iter=2000, random_state=seed)
        clf.fit(X_tr, y_tr)
        scores = clf.predict_proba(X_te)[:, 1]
        auc = float(roc_auc_score(y_te, scores))
        rows.append({
            "subject_id": sid,
            "n_train": int(len(train)),
            "n_test": int(len(test)),
            "n_train_pos": int(y_tr.sum()),
            "n_train_neg": int(len(y_tr) - y_tr.sum()),
            "n_test_pos": int(y_te.sum()),
            "n_test_neg": int(len(y_te) - y_te.sum()),
            "auroc": auc,
        })
    return pd.DataFrame(rows)


def classification_track(df: pd.DataFrame,
                         feature_cols: list[str],
                         classifier: str = "logreg",
                         ) -> dict:
    """Run all four audit conditions and aggregate."""
    conditions = {
        "all": None,
        "inhouse": "pass_inhouse",
        "orphanidou": "pass_orphanidou",
        "both": "pass_both",
    }
    per_fold = {}
    for name, mask in conditions.items():
        per_fold[name] = loso_classify(df, feature_cols, mask, classifier)
        if len(per_fold[name]) == 0:
            log.warning("No valid folds for condition %s", name)
    summary_rows = []
    for name, fold_df in per_fold.items():
        if len(fold_df) == 0:
            summary_rows.append({
                "condition": name, "n_subjects": 0,
                "mean_auroc": float("nan"),
                "median_auroc": float("nan"),
                "auroc_ci_low": float("nan"),
                "auroc_ci_high": float("nan"),
            })
            continue
        aucs = fold_df["auroc"].to_numpy()
        # Subject-cluster bootstrap CI on the macro-mean AUROC
        rng = np.random.default_rng(42)
        bs = []
        for _ in range(500):
            idx = rng.integers(0, len(aucs), size=len(aucs))
            bs.append(aucs[idx].mean())
        summary_rows.append({
            "condition": name,
            "n_subjects": int(len(fold_df)),
            "mean_auroc": float(aucs.mean()),
            "median_auroc": float(np.median(aucs)),
            "auroc_ci_low": float(np.percentile(bs, 2.5)),
            "auroc_ci_high": float(np.percentile(bs, 97.5)),
        })
    # Paired deltas vs 'all'
    baseline_per_subj = per_fold["all"].set_index("subject_id")["auroc"]
    delta_rows = []
    for name, fold_df in per_fold.items():
        if name == "all" or len(fold_df) == 0:
            continue
        cond_per_subj = fold_df.set_index("subject_id")["auroc"]
        common = baseline_per_subj.index.intersection(cond_per_subj.index)
        if len(common) < 3:
            continue
        delta = cond_per_subj.loc[common] - baseline_per_subj.loc[common]
        # Paired Wilcoxon signed-rank
        if (delta == 0).all():
            p_val = 1.0
        else:
            try:
                _, p_val = stats.wilcoxon(delta, alternative="greater")
            except ValueError:
                p_val = float("nan")
        delta_rows.append({
            "condition": name,
            "n_paired": int(len(common)),
            "mean_delta_auroc": float(delta.mean()),
            "median_delta_auroc": float(delta.median()),
            "wilcoxon_p_greater": float(p_val),
            "n_subjects_improved": int((delta > 0).sum()),
            "n_subjects_worse": int((delta < 0).sum()),
        })
    return {
        "per_fold": per_fold,
        "summary": pd.DataFrame(summary_rows),
        "deltas": pd.DataFrame(delta_rows),
    }


# --------------------------------------------------------------------------
# 3. Biomarker-correlation track
# --------------------------------------------------------------------------

def biomarker_correlation_track(df: pd.DataFrame) -> pd.DataFrame:
    """Per-subject Spearman correlation between wrist-PPG HR and chest-ECG HR,
    under no-audit vs in-house-audit vs Orphanidou-audit conditions."""
    rows = []
    for sid in sorted(df["subject_id"].unique()):
        sub = df[df["subject_id"] == sid].copy()
        sub = sub.dropna(subset=["hr_ppg", "hr_ecg"])
        if len(sub) < 30:
            continue
        # All windows
        rho_all, p_all = stats.spearmanr(sub["hr_ppg"], sub["hr_ecg"])
        # In-house audit
        sub_in = sub[sub["pass_inhouse"]]
        if len(sub_in) >= 30:
            rho_in, p_in = stats.spearmanr(sub_in["hr_ppg"], sub_in["hr_ecg"])
        else:
            rho_in, p_in = float("nan"), float("nan")
        # Orphanidou audit
        sub_orph = sub[sub["pass_orphanidou"]]
        if len(sub_orph) >= 30:
            rho_orph, p_orph = stats.spearmanr(sub_orph["hr_ppg"], sub_orph["hr_ecg"])
        else:
            rho_orph, p_orph = float("nan"), float("nan")
        # Both
        sub_both = sub[sub["pass_both"]]
        if len(sub_both) >= 30:
            rho_both, p_both = stats.spearmanr(sub_both["hr_ppg"], sub_both["hr_ecg"])
        else:
            rho_both, p_both = float("nan"), float("nan")
        rows.append({
            "subject_id": sid,
            "n_all": int(len(sub)),
            "n_inhouse_pass": int(len(sub_in)),
            "n_orphanidou_pass": int(len(sub_orph)),
            "n_both_pass": int(len(sub_both)),
            "rho_all": float(rho_all),
            "rho_inhouse": float(rho_in) if rho_in == rho_in else None,
            "rho_orphanidou": float(rho_orph) if rho_orph == rho_orph else None,
            "rho_both": float(rho_both) if rho_both == rho_both else None,
        })
    return pd.DataFrame(rows)


def paired_wilcoxon(corr_df: pd.DataFrame, baseline: str, condition: str) -> dict:
    """Paired Wilcoxon signed-rank test on per-subject ρ improvement."""
    sub = corr_df.dropna(subset=[baseline, condition])
    if len(sub) < 3:
        return {"n_paired": int(len(sub)), "mean_delta": None,
                "median_delta": None, "wilcoxon_p_greater": None}
    delta = sub[condition].to_numpy() - sub[baseline].to_numpy()
    if (delta == 0).all():
        p = 1.0
    else:
        try:
            _, p = stats.wilcoxon(delta, alternative="greater")
        except ValueError:
            p = float("nan")
    return {
        "n_paired": int(len(sub)),
        "mean_delta": float(delta.mean()),
        "median_delta": float(np.median(delta)),
        "n_improved": int((delta > 0).sum()),
        "n_worse": int((delta < 0).sum()),
        "wilcoxon_p_greater": float(p),
    }


# --------------------------------------------------------------------------
# 4. Figure
# --------------------------------------------------------------------------

def make_figure(class_result: dict,
                corr_df: pd.DataFrame,
                out_path: Path,
                ) -> None:
    """Build the four-panel downstream demo figure."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from src.utils.plotting import apply_style
    apply_style()

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    # Panel A: LOSO AUROC distributions per condition
    ax = axes[0, 0]
    conds = ["all", "inhouse", "orphanidou", "both"]
    box_data = []
    labels = []
    for c in conds:
        fold = class_result["per_fold"].get(c)
        if fold is None or len(fold) == 0:
            continue
        box_data.append(fold["auroc"].values)
        labels.append(f"{c}\n(n={len(fold)})")
    if box_data:
        bp = ax.boxplot(box_data, labels=labels, patch_artist=True,
                        showfliers=False, widths=0.5)
        for patch, color in zip(bp["boxes"], ["#888888", "#1f4eaf", "#aa4444", "#226622"]):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
        # Overlay individual subjects as scatter
        for i, data in enumerate(box_data, start=1):
            xs = np.random.normal(i, 0.04, size=len(data))
            ax.scatter(xs, data, s=14, alpha=0.6, color="black", zorder=5)
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.4)
    ax.set_ylabel("LOSO held-out AUROC")
    ax.set_title("A. Baseline-vs-stress classification by audit condition")
    ax.set_ylim(0.3, 1.05)

    # Panel B: Per-subject paired delta vs 'all'
    ax = axes[0, 1]
    baseline_per_subj = class_result["per_fold"]["all"].set_index("subject_id")["auroc"]
    width = 0.25
    colors = {"inhouse": "#1f4eaf", "orphanidou": "#aa4444", "both": "#226622"}
    for i, cond in enumerate(["inhouse", "orphanidou", "both"]):
        fold = class_result["per_fold"].get(cond)
        if fold is None or len(fold) == 0:
            continue
        cond_per_subj = fold.set_index("subject_id")["auroc"]
        common = baseline_per_subj.index.intersection(cond_per_subj.index)
        delta = cond_per_subj.loc[common] - baseline_per_subj.loc[common]
        x = np.arange(len(common)) + (i - 1) * width
        ax.bar(x, delta.values, width=width, color=colors[cond], alpha=0.75, label=cond)
    ax.axhline(0, color="black", linewidth=0.8)
    n_subj = len(class_result["per_fold"]["all"])
    ax.set_xticks(np.arange(n_subj))
    ax.set_xticklabels(class_result["per_fold"]["all"]["subject_id"].values,
                       rotation=45, fontsize=8)
    ax.set_ylabel("Δ AUROC vs no-audit condition")
    ax.set_title("B. Per-subject paired Δ AUROC")
    ax.legend(fontsize=8)

    # Panel C: Biomarker correlation improvement (paired by subject)
    ax = axes[1, 0]
    if len(corr_df) > 0:
        x_pos = np.arange(len(corr_df))
        ax.plot(x_pos, corr_df["rho_all"].values, "o-", color="#888888",
                label="all windows", linewidth=1, alpha=0.7)
        if corr_df["rho_inhouse"].notna().any():
            ax.plot(x_pos, corr_df["rho_inhouse"].values, "s--", color="#1f4eaf",
                    label="in-house pass", linewidth=1, alpha=0.7)
        if corr_df["rho_orphanidou"].notna().any():
            ax.plot(x_pos, corr_df["rho_orphanidou"].values, "^:", color="#aa4444",
                    label="Orphanidou pass", linewidth=1, alpha=0.7)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(corr_df["subject_id"].values, rotation=45, fontsize=8)
    ax.set_ylabel("Spearman ρ (PPG HR vs ECG HR)")
    ax.set_title("C. Per-subject biomarker correlation")
    ax.axhline(0, color="gray", linestyle="--", alpha=0.4)
    ax.legend(fontsize=8, loc="lower right")

    # Panel D: Retention vs improvement trade-off
    ax = axes[1, 1]
    if len(corr_df) > 0 and corr_df["rho_orphanidou"].notna().any():
        for _, row in corr_df.iterrows():
            if pd.notna(row["rho_orphanidou"]):
                retention = row["n_orphanidou_pass"] / row["n_all"]
                improvement = row["rho_orphanidou"] - row["rho_all"]
                ax.scatter(retention, improvement, s=80, color="#aa4444",
                          edgecolors="black", alpha=0.7)
                ax.annotate(row["subject_id"], (retention, improvement),
                           xytext=(5, 5), textcoords="offset points",
                           fontsize=7)
    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(1.0, color="gray", linestyle="--", alpha=0.3)
    ax.set_xlabel("Fraction of windows retained (Orphanidou pass)")
    ax.set_ylabel("Δ Spearman ρ from filtering")
    ax.set_title("D. Retention vs biomarker improvement trade-off")

    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------
# 5. Driver
# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--window-table", type=Path,
                   default=Path("results/real_data/wesad_deep/window_table.csv"))
    p.add_argument("--out-dir", type=Path,
                   default=Path("results/downstream_demo"))
    p.add_argument("--classifier", choices=["logreg", "rf"], default="logreg")
    p.add_argument("--inhouse-threshold", type=float, default=0.70)
    args = p.parse_args()
    out = ensure_dir(args.out_dir)

    log.info("Loading per-window table from %s", args.window_table)
    df = load_per_window_table(args.window_table)
    log.info("Loaded %d windows from %d subjects",
             len(df), df["subject_id"].nunique())

    df = add_audit_masks(df, inhouse_threshold=args.inhouse_threshold)
    log.info(
        "Audit retention: inhouse=%.3f, orphanidou=%.3f, both=%.3f",
        df["pass_inhouse"].mean(),
        df["pass_orphanidou"].mean(),
        df["pass_both"].mean(),
    )

    log.info("Track A: LOSO baseline-vs-stress classification (%s)…",
             args.classifier)
    class_result = classification_track(df, FEATURE_COLS, args.classifier)
    summary = class_result["summary"]
    log.info("\n%s", summary.to_string(index=False))
    log.info("\nPaired Δ AUROC vs 'all' condition:")
    log.info("\n%s", class_result["deltas"].to_string(index=False))

    # Save per-fold and summary
    for name, fold in class_result["per_fold"].items():
        fold.to_csv(out / f"classification_perfold_{name}.csv", index=False)
    summary.to_csv(out / "classification_summary.csv", index=False)
    class_result["deltas"].to_csv(out / "classification_deltas.csv", index=False)

    log.info("Track B: per-subject biomarker correlation…")
    corr = biomarker_correlation_track(df)
    corr.to_csv(out / "biomarker_correlation.csv", index=False)
    log.info("\n%s", corr.to_string(index=False))

    log.info("Paired Wilcoxon test of ρ improvement:")
    for base, cond in [("rho_all", "rho_inhouse"),
                       ("rho_all", "rho_orphanidou"),
                       ("rho_all", "rho_both")]:
        res = paired_wilcoxon(corr, base, cond)
        log.info("  %s vs %s: %s", base, cond, res)

    log.info("Rendering figure…")
    make_figure(class_result, corr, out / "figure_downstream.png")
    log.info("Wrote figure → %s", out / "figure_downstream.png")
    log.info("Done. All outputs in %s", out)


if __name__ == "__main__":
    main()
