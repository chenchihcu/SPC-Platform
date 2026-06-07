"""Isolated SQLite + real registries: stepped stencil resolve_workorder_spec (subprocess, temp DB)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_stepped_stencil_resolve_workorder_spec_via_sqlite_subprocess() -> None:
    """
    Uses SPC_MASTER_DB_PATH so this process never shares init_db state with the child.
    Child imports app fresh and writes only to a tempfile DB.
    """
    repo = Path(__file__).resolve().parents[1]
    fd, db_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(db_str)
    try:
        _run_child(repo, db_path)
    finally:
        db_path.unlink(missing_ok=True)


def _run_child(repo: Path, db_path: Path) -> None:
    code = f"""
import os
import sys

os.environ["SPC_MASTER_DB_PATH"] = {str(db_path)!r}
sys.path.insert(0, {str(repo)!r})

from app.data.product_spec_registry import STENCIL_STEPPED, save as save_spec
from app.data.stencil_assignment_registry import save_assignments
from app.services.spec_resolver import can_run_analysis, resolve_workorder_spec

prod = "GoldenDbSteppedE2E"
assert save_spec({{
    "product_name": prod,
    "stencil_type": STENCIL_STEPPED,
    "thickness_main": 0.12,
    "thickness_precision": 0.08,
    "precision_is_main": False,
    "default_volume_target": 100.0,
    "default_volume_lsl": 70.0,
    "default_volume_usl": 150.0,
    "default_area_target": 100.0,
    "default_area_lsl": 70.0,
    "default_area_usl": 150.0,
}})

wo, err = resolve_workorder_spec(prod)
assert wo is None and err and "階梯鋼板" in err
ok, msg = can_run_analysis(prod)
assert ok is False and msg and "階梯鋼板" in msg

assert save_assignments(prod, ["R1"], coord_file_path="golden_e2e_placeholder.csv")
wo2, err2 = resolve_workorder_spec(prod)
assert err2 is None and wo2 is not None
assert set(wo2.keys()) >= {{"volume", "area", "height"}}
ok2, msg2 = can_run_analysis(prod)
assert ok2 is True and msg2 == ""
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r}\nstdout={proc.stdout!r}"
