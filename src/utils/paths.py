"""Path helpers.

Everything here works relative to the repo root so scripts and notebooks
can be launched from anywhere without hardcoding absolute paths.
"""
from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Walk up from this file until we find the repo marker (pyproject.toml)."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    # fallback: assume four levels up (src/utils/paths.py -> repo)
    return here.parents[2]


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = repo_root() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else repo_root() / p
