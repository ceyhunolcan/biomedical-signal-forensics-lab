"""Tiny GRU baseline for sequence-level quality (per-participant time series).

Trained against per-participant mean reliability_ground_truth as a regression
sanity check. Not the main contribution: just here so reviewers can see we
considered the temporal dimension.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
import torch.nn as nn


class SmallGRU(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 16) -> None:
        super().__init__()
        self.gru = nn.GRU(in_dim, hidden, batch_first=True)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, h = self.gru(x)
        return self.head(h.squeeze(0))


@dataclass
class SeqResult:
    rmse: float
    notes: str


def train(df: pd.DataFrame, epochs: int = 15, seed: int = 42) -> SeqResult:
    torch.manual_seed(seed)
    feats = ["resting_hr", "hrv_rmssd", "step_count", "sleep_efficiency",
             "heat_index", "wearable_minutes"]
    seqs = []
    targets = []
    for pid, g in df.groupby("participant_id"):
        g_sorted = g.sort_values("date")
        x = g_sorted[feats].fillna(g_sorted[feats].median()).to_numpy(dtype=np.float32)
        y = float(g_sorted["reliability_ground_truth"].mean())
        if len(x) < 10:
            continue
        # take first 30 days, pad otherwise
        x = x[:30]
        if len(x) < 30:
            pad = np.zeros((30 - len(x), len(feats)), dtype=np.float32)
            x = np.concatenate([x, pad], axis=0)
        seqs.append(x)
        targets.append(y)
    if len(seqs) < 20:
        return SeqResult(float("nan"), "Not enough sequences.")
    X = torch.tensor(np.stack(seqs))
    Y = torch.tensor(np.array(targets, dtype=np.float32)).unsqueeze(1)
    n_train = int(len(X) * 0.8)
    model = SmallGRU(in_dim=X.shape[-1])
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()
    for _ in range(epochs):
        opt.zero_grad()
        pred = model(X[:n_train])
        loss = loss_fn(pred, Y[:n_train])
        loss.backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        pred = model(X[n_train:]).cpu().numpy().squeeze()
    truth = Y[n_train:].cpu().numpy().squeeze()
    rmse = float(np.sqrt(np.mean((pred - truth) ** 2)))
    return SeqResult(rmse, "1-layer GRU, 30-day window")
