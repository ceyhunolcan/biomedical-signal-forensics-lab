"""Tiny standalone test runner so the suite can be validated in sandboxes without pytest.

Discovers test_*.py files under tests/, imports each, runs every top-level callable named
test_*. Uses tmp_path fixture via Python's tempfile when needed.

Not a pytest replacement: it's a sanity check that the suite is structurally sound.
Real users should run `pytest -q`.
"""
from __future__ import annotations

import importlib.util
import inspect
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(test_path: Path):
    spec = importlib.util.spec_from_file_location(test_path.stem, test_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _call(fn):
    params = inspect.signature(fn).parameters
    if "tmp_path" in params:
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
    else:
        fn()


def main() -> int:
    tests_dir = ROOT / "tests"
    failures: list[tuple[str, str]] = []
    skipped: list[str] = []
    passed = 0

    for path in sorted(tests_dir.glob("test_*.py")):
        try:
            mod = _load(path)
        except Exception as exc:  # noqa: BLE001
            # importorskip raises pytest.skip.Exception or ImportError before pytest is present
            msg = repr(exc)
            msg_lower = msg.lower()
            optional_keywords = ("fastapi", "pydantic", "pytest", "importorskip", "skipped")
            if any(k in msg_lower for k in optional_keywords):
                skipped.append(f"{path.name} (missing optional dep: {exc})")
            else:
                failures.append((path.name, traceback.format_exc()))
            continue

        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if not name.startswith("test_") or fn.__module__ != mod.__name__:
                continue
            try:
                _call(fn)
                passed += 1
                print(f"  PASS  {path.name}::{name}")
            except Exception:  # noqa: BLE001
                failures.append((f"{path.name}::{name}", traceback.format_exc()))
                print(f"  FAIL  {path.name}::{name}")

    print()
    print(f"Passed:  {passed}")
    print(f"Failed:  {len(failures)}")
    print(f"Skipped: {len(skipped)}")
    for s in skipped:
        print(f"  - {s}")
    for name, tb in failures:
        print(f"\n--- {name} ---\n{tb}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
