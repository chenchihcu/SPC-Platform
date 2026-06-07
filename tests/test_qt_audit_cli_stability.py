from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_qt_audit_cli_is_stable_with_cp950_output() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "0"
    env["PYTHONIOENCODING"] = "cp950"

    proc = subprocess.run(
        [sys.executable, "scripts/qt_audit.py", "app"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        encoding="cp950",
        errors="replace",
    )

    output = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode in {0, 1}
    assert "Qt Audit Results" in output
    assert "UnicodeEncodeError" not in output
