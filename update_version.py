"""Explicit version bumper.

Earlier versions of this repository used inline sed commands like
    sed -i '' 's/version = "0.9.0"/version = "0.10.0"/' pyproject.toml
to bump the version on each release. That approach pattern-matched against
the PRIOR version string, so if one bump silently failed (because the file
already contained an unexpected version), every subsequent bump silently
failed too. As a result, the package version stayed at 0.8.0 for four
releases while git tags advanced to v0.12.0.

This script reads the current version, reports it, and writes the target
version explicitly. It does not depend on any particular prior version
being present.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TARGET_VERSION = "0.13.0"


def update_pyproject(path: Path, target: str) -> tuple[str, str]:
    txt = path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', txt, flags=re.MULTILINE)
    if not match:
        raise SystemExit(f"Could not find a version line in {path}")
    prior = match.group(1)
    new_txt = re.sub(
        r'^(version\s*=\s*)"[^"]+"(\s*)$',
        rf'\1"{target}"\2',
        txt,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(new_txt)
    return prior, target


def update_init(path: Path, target: str) -> tuple[str, str]:
    txt = path.read_text()
    match = re.search(r'^__version__\s*=\s*"([^"]+)"\s*$', txt, flags=re.MULTILINE)
    if not match:
        raise SystemExit(f"Could not find a __version__ line in {path}")
    prior = match.group(1)
    new_txt = re.sub(
        r'^(__version__\s*=\s*)"[^"]+"(\s*)$',
        rf'\1"{target}"\2',
        txt,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(new_txt)
    return prior, target


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    # If invoked from anywhere else, fall back to assuming cwd is repo root
    if not (repo_root / "pyproject.toml").exists():
        repo_root = Path.cwd()
    pyproject = repo_root / "pyproject.toml"
    init_py = repo_root / "src" / "__init__.py"

    if not pyproject.exists():
        raise SystemExit(f"pyproject.toml not found at {pyproject}")
    if not init_py.exists():
        raise SystemExit(f"src/__init__.py not found at {init_py}")

    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_VERSION
    prior_a, _ = update_pyproject(pyproject, target)
    prior_b, _ = update_init(init_py, target)

    print(f"pyproject.toml: {prior_a} -> {target}")
    print(f"src/__init__.py: {prior_b} -> {target}")


if __name__ == "__main__":
    main()
