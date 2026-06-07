"""Gate A-F governance alignment is part of the release gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_governance_alignment_check_passes() -> None:
    repo = _repo_root()
    proc = subprocess.run(
        [sys.executable, "scripts/check_governance_alignment.py"],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
