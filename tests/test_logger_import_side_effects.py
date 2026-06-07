from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_import_ui_runtime_diagnostics_does_not_mutate_root_logger() -> None:
    repo = Path(__file__).resolve().parents[1]
    code = r"""
import json
import logging

before = {
    "level": logging.getLogger().getEffectiveLevel(),
    "handlers": len(logging.getLogger().handlers),
}

import app.ui.debug.ui_runtime_diagnostics  # noqa: F401

after = {
    "level": logging.getLogger().getEffectiveLevel(),
    "handlers": len(logging.getLogger().handlers),
}

print(json.dumps({"before": before, "after": after}))
"""
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert lines, "expected JSON output from import probe"
    payload = json.loads(lines[-1])
    assert payload["after"] == payload["before"], payload
