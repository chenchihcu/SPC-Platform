"""Isolated SQLite e2e: update SPI spec limits from library API."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_update_spec_metadata_updates_va_h_limits_in_sqlite_subprocess() -> None:
    repo = Path(__file__).resolve().parents[1]
    fd, db_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(db_str)
    try:
        _run_child(repo, db_path)
    finally:
        db_path.unlink(missing_ok=True)


def test_add_product_spec_preserves_part_no_in_dual_tables_subprocess() -> None:
    repo = Path(__file__).resolve().parents[1]
    fd, db_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(db_str)
    try:
        _run_add_child(repo, db_path)
    finally:
        db_path.unlink(missing_ok=True)


def _run_child(repo: Path, db_path: Path) -> None:
    code = f"""
import os
import sys

os.environ["SPC_MASTER_DB_PATH"] = {str(db_path)!r}
sys.path.insert(0, {str(repo)!r})

from app.data.product_spec_registry import save as save_spec
from app.data.product_spec_library import list_spec_versions, update_spec_metadata

prod = "SpecEditE2E"
assert save_spec({{
    "product_name": prod,
    "stencil_type": "normal",
    "thickness_main": 0.12,
    "default_volume_target": 100.0,
    "default_volume_lsl": 70.0,
    "default_volume_usl": 150.0,
    "default_area_target": 100.0,
    "default_area_lsl": 70.0,
    "default_area_usl": 150.0,
    "default_height_target": 100.0,
    "default_height_lsl": 70.0,
    "default_height_usl": 140.0,
}})

rows = list_spec_versions(product_name=prod, product_name_exact=True, limit=10)
assert len(rows) == 1
sid = int(rows[0]["id"])

ok = update_spec_metadata(
    sid,
    default_volume_target=105.0,
    default_volume_lsl=75.0,
    default_volume_usl=145.0,
    default_area_target=102.0,
    default_area_lsl=76.0,
    default_area_usl=142.0,
    default_height_lsl=80.0,
    default_height_usl=135.0,
)
assert ok is True

rows2 = list_spec_versions(product_name=prod, product_name_exact=True, limit=10)
assert len(rows2) == 1
v = rows2[0]
assert float(v["default_volume_target"]) == 105.0
assert float(v["default_volume_lsl"]) == 75.0
assert float(v["default_volume_usl"]) == 145.0
assert float(v["default_area_target"]) == 102.0
assert float(v["default_area_lsl"]) == 76.0
assert float(v["default_area_usl"]) == 142.0
# Height target now follows stencil baseline (percent mode => 100.0)
assert float(v["default_height_target"]) == 100.0
assert float(v["default_height_lsl"]) == 80.0
assert float(v["default_height_usl"]) == 135.0
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


def _run_add_child(repo: Path, db_path: Path) -> None:
    code = f"""
import os
import sys

os.environ["SPC_MASTER_DB_PATH"] = {str(db_path)!r}
sys.path.insert(0, {str(repo)!r})

from app.data.paste_printing_spec_library import list_paste_printing_spec_versions
from app.data.paste_printing_spec_registry import save as save_paste_spec
from app.data.stencil_thickness_library import list_stencil_thickness_versions
from app.data.stencil_thickness_registry import save as save_stencil_spec

prod = "SpecAddE2E"
part_no = "PN-SPEC-001"

assert save_paste_spec({{
    "product_name": prod,
    "product_part_no": part_no,
    "default_volume_target": 100.0,
    "default_volume_lsl": 70.0,
    "default_volume_usl": 150.0,
    "default_area_target": 100.0,
    "default_area_lsl": 70.0,
    "default_area_usl": 150.0,
    "default_height_lsl": 70.0,
    "default_height_usl": 140.0,
}})
assert save_stencil_spec({{
    "product_name": prod,
    "product_part_no": part_no,
    "stencil_type": "normal",
    "thickness_main": 0.12,
    "thickness_precision": None,
    "precision_is_main": False,
    "unit_mode": "percent",
    "height_denominator_mm": 0.12,
}})

paste_rows = list_paste_printing_spec_versions(product_name=prod, product_name_exact=True)
stencil_rows = list_stencil_thickness_versions(product_name=prod, product_name_exact=True)

assert len(paste_rows) == 1
assert len(stencil_rows) == 1
assert paste_rows[0]["product_part_no"] == part_no
assert stencil_rows[0]["product_part_no"] == part_no
assert int(paste_rows[0]["is_active"]) == 1
assert int(stencil_rows[0]["is_active"]) == 1
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
