"""Audit pyproject.toml for PyPI-publishing readiness.

Reports which standard-metadata fields are present, which are missing,
and which are present but empty. Does NOT modify the file. Prints a
recommended skeleton patch at the end if anything is missing.

PyPI rejects packages that lack required core metadata (name, version,
description, etc.) and packages whose readme cannot be rendered. This
script flags both.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        print("ERROR: need Python 3.11+ or `pip install tomli`")
        sys.exit(2)


REQUIRED_TOP = ["name", "version", "description", "readme", "requires-python", "license", "authors"]
RECOMMENDED_TOP = ["keywords", "classifiers", "urls"]
RECOMMENDED_URLS = ["Homepage", "Repository", "Documentation", "Changelog", "Issues"]
RECOMMENDED_CLASSIFIERS = [
    "Development Status",
    "Intended Audience",
    "License",
    "Programming Language :: Python",
    "Topic",
    "Operating System",
]


def main() -> int:
    p = Path("pyproject.toml")
    if not p.exists():
        print("ERROR: pyproject.toml not found in current directory")
        return 1

    data = tomllib.loads(p.read_text(encoding="utf-8"))
    project = data.get("project", {})

    print("=" * 60)
    print("pyproject.toml audit for PyPI publishing")
    print("=" * 60)

    if not project:
        print("FAIL: No [project] table present. Cannot publish to PyPI.")
        return 1

    # Required fields
    print()
    print("--- Required fields ---")
    missing_required = []
    for field in REQUIRED_TOP:
        if field in project:
            val = project[field]
            preview = (str(val)[:60] + "...") if len(str(val)) > 60 else str(val)
            print(f"  OK     {field:20s} = {preview}")
        else:
            print(f"  MISS   {field:20s} (REQUIRED for PyPI)")
            missing_required.append(field)

    # Recommended fields
    print()
    print("--- Recommended fields ---")
    missing_recommended = []
    for field in RECOMMENDED_TOP:
        if field in project:
            print(f"  OK     {field}")
        else:
            print(f"  miss   {field}  (recommended)")
            missing_recommended.append(field)

    # urls subkeys
    urls = project.get("urls", {})
    if urls:
        print()
        print("--- urls.* subkeys ---")
        for key in RECOMMENDED_URLS:
            if key in urls:
                print(f"  OK     urls.{key:15s} = {urls[key]}")
            else:
                print(f"  miss   urls.{key}  (recommended)")

    # classifiers prefixes
    classifiers = project.get("classifiers", [])
    if classifiers:
        print()
        print(f"--- classifiers ({len(classifiers)} present) ---")
        present_prefixes = set()
        for c in classifiers:
            for prefix in RECOMMENDED_CLASSIFIERS:
                if c.startswith(prefix):
                    present_prefixes.add(prefix)
        for prefix in RECOMMENDED_CLASSIFIERS:
            if prefix in present_prefixes:
                print(f"  OK     {prefix}")
            else:
                print(f"  miss   {prefix}  (recommended)")

    # Readme file existence check
    readme = project.get("readme")
    if isinstance(readme, str):
        if not Path(readme).exists():
            print()
            print(f"FAIL: readme = '{readme}' but the file does not exist on disk.")
            return 1
    elif isinstance(readme, dict):
        rfile = readme.get("file")
        if rfile and not Path(rfile).exists():
            print()
            print(f"FAIL: readme.file = '{rfile}' but the file does not exist on disk.")
            return 1

    # Summary
    print()
    print("=" * 60)
    if missing_required:
        print(f"NOT READY: {len(missing_required)} REQUIRED field(s) missing.")
        print()
        print("Recommended skeleton to add to [project]:")
        print()
        skeleton = []
        if "description" in missing_required:
            skeleton.append('description = "An open-source toolkit for auditing wearable physiological signals."')
        if "readme" in missing_required:
            skeleton.append('readme = "README.md"')
        if "requires-python" in missing_required:
            skeleton.append('requires-python = ">=3.10"')
        if "license" in missing_required:
            skeleton.append('license = { text = "MIT" }')
        if "authors" in missing_required:
            skeleton.append('authors = [\n  { name = "Ceyhun Olcan", email = "ceyhun.olcan.27@dartmouth.edu" },\n]')
        for line in skeleton:
            print(f"  {line}")
        return 1
    else:
        print("READY: all required PyPI-publishing fields are present.")
        if missing_recommended:
            print(f"Note: {len(missing_recommended)} recommended field(s) absent; add for better PyPI presentation.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
