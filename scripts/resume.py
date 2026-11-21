#!/usr/bin/env python3
"""Shortcut: python scripts/resume.py {prepare|finalize|approve} <job_id>  (also: sync, scan, jobs)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
py = ROOT / ".venv" / "bin" / "python"
raise SystemExit(subprocess.call([str(py if py.exists() else sys.executable), "-m", "app.cli", *sys.argv[1:]],
                                 cwd=ROOT / "backend"))
