"""Generate the markdown audit report.

Usage: python scripts/generate_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.reports.report_generator import generate_report
from src.utils.logging import get_logger

log = get_logger("report-cli")


def main() -> None:
    p = generate_report()
    log.info("Report at: %s", p)


if __name__ == "__main__":
    main()
