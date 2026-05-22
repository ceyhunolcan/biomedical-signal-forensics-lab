"""Launch the Streamlit dashboard.

Usage: python scripts/launch_dashboard.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    app = root / "src" / "dashboard" / "app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app),
           "--server.port=8501", "--server.address=0.0.0.0"]
    print(" ".join(cmd))
    subprocess.run(cmd, check=False, cwd=str(root))


if __name__ == "__main__":
    main()
