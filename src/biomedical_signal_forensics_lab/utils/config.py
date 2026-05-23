"""Config loading. YAML in, plain dict out, with a small dot-access wrapper."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .paths import resolve


class DotDict(dict):
    """Dictionary that supports attribute-style access.

    Note: this class assumes nested dicts have already been converted to
    DotDict by `_wrap` (which `load_yaml` calls). Attribute access is
    side-effect free; if you build a DotDict by hand with raw nested dicts,
    inner dicts will be returned as plain dicts.
    """

    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


def load_yaml(path: str | Path) -> DotDict:
    full = resolve(path)
    with open(full, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _wrap(raw)


def _wrap(obj: Any) -> Any:
    if isinstance(obj, dict):
        return DotDict({k: _wrap(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_wrap(v) for v in obj]
    return obj


def load_all() -> DotDict:
    """Load every config in configs/ and merge under their basename keys."""
    out: dict[str, Any] = {}
    cfg_dir = resolve("configs")
    for f in sorted(cfg_dir.glob("*.yaml")):
        out[f.stem] = load_yaml(f)
    return _wrap(out)
