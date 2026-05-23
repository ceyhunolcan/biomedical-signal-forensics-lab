"""Plotting helpers. Matplotlib only.

We deliberately don't import seaborn anywhere in the codebase.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


_STYLE_APPLIED = False


def apply_style() -> None:
    global _STYLE_APPLIED
    if _STYLE_APPLIED:
        return
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 160,
            "figure.figsize": (8, 4.5),
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "font.size": 10,
            "legend.frameon": False,
        }
    )
    _STYLE_APPLIED = True


def savefig(fig, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p
