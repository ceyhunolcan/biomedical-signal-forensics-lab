"""A small PyTorch autoencoder used as an unsupervised quality probe.

We train it on what looks like 'good' data (high signal quality ground truth)
and use reconstruction error as a quality score for new samples.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from .anomaly_detector import FEATURE_COLUMNS, _prepare


class QualityAutoencoder(nn.Module):
    def __init__(self, in_dim: int, hidden_dims: tuple[int, ...] = (32, 16, 8)) -> None:
        super().__init__()
        enc_layers = []
        prev = in_dim
        for h in hidden_dims:
            enc_layers += [nn.Linear(prev, h), nn.ReLU()]
            prev = h
        self.encoder = nn.Sequential(*enc_layers)

        dec_layers = []
        for h in list(reversed(hidden_dims[:-1])) + [in_dim]:
            dec_layers += [nn.Linear(prev, h)]
            if h != in_dim:
                dec_layers += [nn.ReLU()]
            prev = h
        self.decoder = nn.Sequential(*dec_layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


@dataclass
class AETrainResult:
    auroc: float
    f1: float
    notes: str


def train(df: pd.DataFrame, epochs: int = 25, batch_size: int = 128,
          lr: float = 1e-3, weight_decay: float = 1e-5,
          seed: int = 42, include_confounding: bool = False) -> AETrainResult:
    torch.manual_seed(seed)
    X, y, _ = _prepare(df)
    if include_confounding:
        extras = [c for c in ("heat_index", "humidity", "aqi") if c in df.columns]
        X = np.concatenate(
            [X, df[extras].fillna(df[extras].median()).to_numpy()], axis=1
        )
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    X_train, X_test, y_train, y_test = train_test_split(
        Xs, y, test_size=0.2, random_state=seed, stratify=y
    )

    # train only on "good" samples
    good = X_train[y_train == 1]
    if len(good) < 32:
        return AETrainResult(float("nan"), float("nan"), "Not enough good samples.")

    in_dim = good.shape[1]
    model = QualityAutoencoder(in_dim)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = nn.MSELoss()

    good_t = torch.tensor(good, dtype=torch.float32)
    for _ in range(epochs):
        idx = torch.randperm(len(good_t))
        for start in range(0, len(good_t), batch_size):
            batch = good_t[idx[start:start + batch_size]]
            opt.zero_grad()
            rec = model(batch)
            loss = loss_fn(rec, batch)
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        test_t = torch.tensor(X_test, dtype=torch.float32)
        rec = model(test_t)
        recon_err = ((rec - test_t) ** 2).mean(dim=1).cpu().numpy()
    # high recon error -> low quality (y == 0)
    try:
        auroc = float(roc_auc_score(y_test, -recon_err))
        preds = (recon_err > np.median(recon_err)).astype(int)
        # invert because high err = predicted bad
        preds = 1 - preds
        f1 = float(f1_score(y_test, preds))
    except ValueError:
        auroc, f1 = float("nan"), float("nan")

    note = "AE on quality features" + (" + environmental" if include_confounding else "")
    return AETrainResult(auroc, f1, note)
