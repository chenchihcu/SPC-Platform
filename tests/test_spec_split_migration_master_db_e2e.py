"""Isolated SQLite e2e: legacy spec_versions auto-split migration."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_legacy_spec_versions_split_into_dual_tables() -> None:
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
import sqlite3
import sys
from pathlib import Path

db_path = Path({str(db_path)!r})
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript(
    '''
    CREATE TABLE schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        product_name_ci TEXT NOT NULL UNIQUE,
        product_part_no TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE spec_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        stencil_type TEXT NOT NULL,
        thickness_main REAL NOT NULL,
        thickness_precision REAL,
        precision_is_main INTEGER NOT NULL DEFAULT 0,
        default_volume_target REAL NOT NULL,
        default_volume_lsl REAL NOT NULL,
        default_volume_usl REAL NOT NULL,
        default_area_target REAL NOT NULL,
        default_area_lsl REAL NOT NULL,
        default_area_usl REAL NOT NULL,
        default_height_target REAL NOT NULL DEFAULT 100.0,
        default_height_lsl REAL NOT NULL DEFAULT 70.0,
        default_height_usl REAL NOT NULL DEFAULT 140.0,
        updated_at TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    '''
)
conn.execute(
    "INSERT INTO schema_meta(key, value) VALUES(?, ?)",
    ("json_registry_migrated_v1", "1"),
)
conn.execute(
    '''
    INSERT INTO products(product_name, product_name_ci, product_part_no, status, created_at, updated_at)
    VALUES('LegacyProd', 'legacyprod', 'PN-1', 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')
    '''
)
conn.execute(
    '''
    INSERT INTO spec_versions(
        product_id, stencil_type, thickness_main, thickness_precision, precision_is_main,
        default_volume_target, default_volume_lsl, default_volume_usl,
        default_area_target, default_area_lsl, default_area_usl,
        default_height_target, default_height_lsl, default_height_usl,
        updated_at, is_active
    )
    VALUES(1, 'normal', 0.12, NULL, 0, 100, 70, 150, 100, 70, 150, 100, 75, 135, '2026-01-02T00:00:00', 1)
    '''
)
conn.commit()
conn.close()

sys.path.insert(0, {str(repo)!r})
import os
os.environ["SPC_MASTER_DB_PATH"] = str(db_path)

from app.data.master_data_db import db_conn

with db_conn() as conn2:
    paste_row = conn2.execute(
        "SELECT default_height_lsl, default_height_usl, is_active FROM paste_printing_spec_versions WHERE product_id = 1"
    ).fetchone()
    stencil_row = conn2.execute(
        "SELECT stencil_type, thickness_main, unit_mode, height_denominator_mm, is_active FROM stencil_thickness_versions WHERE product_id = 1"
    ).fetchone()
    marker = conn2.execute(
        "SELECT value FROM schema_meta WHERE key = 'spec_versions_split_v1'"
    ).fetchone()

assert paste_row is not None
assert float(paste_row[0]) == 75.0
assert float(paste_row[1]) == 135.0
assert int(paste_row[2]) == 1
assert stencil_row is not None
assert stencil_row[0] == 'normal'
assert float(stencil_row[1]) == 0.12
assert stencil_row[2] == 'percent'
assert float(stencil_row[3]) == 0.12
assert int(stencil_row[4]) == 1
assert marker is not None and str(marker[0]) == '1'
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r}\nstdout={proc.stdout!r}"
