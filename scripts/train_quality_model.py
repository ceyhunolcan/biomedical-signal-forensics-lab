"""Train baselines + (if available) the PyTorch autoencoder. Write the leaderboard.

If PyTorch is not installed, the autoencoder rows are emitted with NaN metrics and a
note that explains why. Everything else still runs.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src.models.anomaly_detector import train_baselines, _prepare
from src.evaluation.metrics import expected_calibration_error
from src.utils.config import load_yaml
from src.utils.logging import get_logger
from src.utils.paths import ensure_dir, resolve

log = get_logger("train")


def _robustness_score(model, X_test, y_test, noise_std: float = 0.05, n_trials: int = 5) -> float:
    """Fraction of predictions preserved under Gaussian feature perturbation."""
    base_pred = (model.predict_proba(X_test)[:, 1] > 0.5).astype(int)
    matches = []
    rng = np.random.default_rng(0)
    sd = X_test.std(axis=0) + 1e-6
    for _ in range(n_trials):
        noise = rng.normal(0, noise_std * sd, X_test.shape)
        pert = X_test + noise
        try:
            pred = (model.predict_proba(pert)[:, 1] > 0.5).astype(int)
            matches.append((pred == base_pred).mean())
        except Exception:  # noqa: BLE001
            continue
    return float(np.mean(matches)) if matches else float("nan")


def _isoforest_robustness(model, X_test, noise_std: float = 0.05, n_trials: int = 5) -> float:
    base = (-model.score_samples(X_test) < np.median(-model.score_samples(X_test))).astype(int)
    matches = []
    rng = np.random.default_rng(0)
    sd = X_test.std(axis=0) + 1e-6
    for _ in range(n_trials):
        pert = X_test + rng.normal(0, noise_std * sd, X_test.shape)
        s = -model.score_samples(pert)
        pred = (s < np.median(s)).astype(int)
        matches.append((pred == base).mean())
    return float(np.mean(matches)) if matches else float("nan")


def _baseline_metrics(df: pd.DataFrame, seed: int = 42) -> list[dict]:
    """Train baselines with full metric panel."""
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    X, y, _ = _prepare(df)
    if len(np.unique(y)) < 2:
        note = (f"target is single-class; cannot train supervised baselines "
                f"(found {len(np.unique(y))} unique labels)")
        return [
            {"model_name": n, "quality_detection_AUROC": float("nan"),
             "artifact_detection_F1": float("nan"),
             "calibration_error": float("nan"),
             "robustness_score": float("nan"), "notes": note}
            for n in ("logistic_regression", "random_forest", "isolation_forest")
        ]
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    X_train, X_test, y_train, y_test = train_test_split(
        Xs, y, test_size=0.2, random_state=seed, stratify=y
    )

    rows: list[dict] = []

    lr = LogisticRegression(C=1.0, max_iter=1000).fit(X_train, y_train)
    p = lr.predict_proba(X_test)[:, 1]
    rows.append({
        "model_name": "logistic_regression",
        "quality_detection_AUROC": float(roc_auc_score(y_test, p)),
        "artifact_detection_F1": float(f1_score(y_test, (p > 0.5).astype(int))),
        "calibration_error": float(expected_calibration_error(y_test, p)),
        "robustness_score": _robustness_score(lr, X_test, y_test),
        "notes": "linear baseline",
    })

    rf = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=seed).fit(X_train, y_train)
    p = rf.predict_proba(X_test)[:, 1]
    rows.append({
        "model_name": "random_forest",
        "quality_detection_AUROC": float(roc_auc_score(y_test, p)),
        "artifact_detection_F1": float(f1_score(y_test, (p > 0.5).astype(int))),
        "calibration_error": float(expected_calibration_error(y_test, p)),
        "robustness_score": _robustness_score(rf, X_test, y_test),
        "notes": "ensemble baseline (200 trees, depth 12)",
    })

    iso = IsolationForest(n_estimators=200, contamination=0.2, random_state=seed).fit(X_train)
    s = -iso.score_samples(X_test)
    try:
        auroc = float(roc_auc_score(y_test, -s))
    except ValueError:
        auroc = float("nan")
    rows.append({
        "model_name": "isolation_forest",
        "quality_detection_AUROC": auroc,
        "artifact_detection_F1": float(f1_score(y_test, (s < np.median(s)).astype(int))),
        "calibration_error": float("nan"),  # not a calibrated probability output
        "robustness_score": _isoforest_robustness(iso, X_test),
        "notes": "unsupervised anomaly detector",
    })
    return rows


def _autoencoder_metrics(df: pd.DataFrame, include_confounding: bool) -> dict:
    """Try training the AE. If torch isn't available, return a row of NaN with a note."""
    name = "quality_autoencoder_plus_confounding" if include_confounding else "quality_autoencoder"
    try:
        from src.models.quality_autoencoder import train as train_ae  # noqa: WPS433
    except ImportError as exc:
        log.warning("PyTorch unavailable, skipping %s: %s", name, exc)
        return {
            "model_name": name,
            "quality_detection_AUROC": float("nan"),
            "artifact_detection_F1": float("nan"),
            "calibration_error": float("nan"),
            "robustness_score": float("nan"),
            "notes": "skipped: torch not installed",
        }
    res = train_ae(df, include_confounding=include_confounding)
    return {
        "model_name": name,
        "quality_detection_AUROC": float(res.auroc),
        "artifact_detection_F1": float(res.f1),
        "calibration_error": float(getattr(res, "calibration_error", float("nan"))),
        "robustness_score": float(getattr(res, "robustness_score", float("nan"))),
        "notes": getattr(res, "notes", "PyTorch autoencoder"),
    }


def main(include_extensions: bool = False) -> None:
    """Train baselines and write the leaderboard.

    By default, only the three baselines (logistic regression, random forest,
    isolation forest) are trained and reported. The PyTorch autoencoder is
    an extension point, not a headline result; pass `include_extensions=True`
    to include it (requires `torch`).
    """
    cfg = load_yaml("configs/default.yaml")
    df = pd.read_csv(resolve(cfg.paths.synthetic_csv))

    rows = _baseline_metrics(df)
    if include_extensions:
        rows.append(_autoencoder_metrics(df, include_confounding=False))
        rows.append(_autoencoder_metrics(df, include_confounding=True))

    out = pd.DataFrame(rows)
    # round for legibility but leave NaN intact
    for c in ("quality_detection_AUROC", "artifact_detection_F1", "calibration_error", "robustness_score"):
        out[c] = out[c].apply(lambda v: round(v, 4) if pd.notna(v) else v)

    ensure_dir(Path(cfg.paths.leaderboard_csv).parent)
    out.to_csv(resolve(cfg.paths.leaderboard_csv), index=False)
    log.info("Leaderboard written → %s", cfg.paths.leaderboard_csv)
    log.info("\n%s", out.to_string(index=False))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--include-extensions", action="store_true",
                   help="Also train the PyTorch autoencoder rows (extension points).")
    args = p.parse_args()
    main(include_extensions=args.include_extensions)
