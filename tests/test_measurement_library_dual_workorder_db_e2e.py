"""Isolated SQLite e2e: measurement_sessions dual-workorder migration + CRUD compatibility."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_measurement_library_dual_workorder_migration_and_crud_subprocess() -> None:
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
import sqlite3
import sys

db_path = {str(db_path)!r}
conn = sqlite3.connect(db_path)
conn.executescript(
    '''
    CREATE TABLE IF NOT EXISTS measurement_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        product_name TEXT NOT NULL DEFAULT '',
        work_order_no TEXT NOT NULL DEFAULT '',
        batch_no TEXT NOT NULL DEFAULT '',
        product_part_no TEXT NOT NULL DEFAULT '',
        file_path TEXT NOT NULL,
        file_hash TEXT NOT NULL DEFAULT '',
        row_count INTEGER,
        upload_datetime TEXT NOT NULL,
        notes TEXT NOT NULL DEFAULT ''
    );
    INSERT INTO measurement_sessions(
        product_name, work_order_no, batch_no, product_part_no,
        file_path, file_hash, row_count, upload_datetime, notes
    )
    VALUES(
        'LegacyBeforeInit', 'WO-PRE-INIT', '', '',
        'C:/tmp/pre_init_legacy.csv', '', NULL, '2026-01-01T00:00:00', ''
    );
    '''
)
conn.commit()
conn.close()

os.environ["SPC_MASTER_DB_PATH"] = db_path
sys.path.insert(0, {str(repo)!r})

from app.data.master_data_db import WORK_ORDER_CLEAR_MIGRATION_KEY, db_conn
from app.data.measurement_library import (
    get_measurement_session,
    list_measurement_sessions,
    save_measurement_session,
    update_measurement_session,
)

with db_conn() as conn:
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(measurement_sessions)").fetchall()]
    legacy_row = conn.execute(
        "SELECT work_order_no FROM measurement_sessions WHERE file_path = ?",
        ("C:/tmp/pre_init_legacy.csv",),
    ).fetchone()
    migration_flag = conn.execute(
        "SELECT value FROM schema_meta WHERE key = ?",
        (WORK_ORDER_CLEAR_MIGRATION_KEY,),
    ).fetchone()
assert "supplier_work_order_no" in cols
assert "outsource_work_order_no" in cols
assert "supplier" in cols
assert legacy_row is not None
assert legacy_row["work_order_no"] == ""
assert migration_flag is not None and migration_flag["value"] == "1"

sid = save_measurement_session(
    "C:/tmp/meas_dual.csv",
    product_name="DualProduct",
    supplier="振順豐",
    supplier_work_order_no="SUP-100",
    outsource_work_order_no="OUT-200",
    batch_no="OUT-200",
)
row = get_measurement_session(sid)
assert row is not None
assert row["supplier"] == "振順豐"
assert row["supplier_work_order_no"] == "SUP-100"
assert row["outsource_work_order_no"] == "OUT-200"
assert row["work_order_no"] == ""

rows = list_measurement_sessions(work_order_no="OUT-200")
assert rows
assert rows[0]["supplier"] == "振順豐"
assert rows[0]["supplier_work_order_no"] == "SUP-100"

rows_by_supplier = list_measurement_sessions(keyword="振順豐")
assert rows_by_supplier
assert rows_by_supplier[0]["supplier"] == "振順豐"

ok = update_measurement_session(
    sid,
    supplier="振順豐二廠",
    supplier_work_order_no="SUP-101",
    outsource_work_order_no="OUT-201",
)
assert ok is True
row2 = get_measurement_session(sid)
assert row2 is not None
assert row2["supplier"] == "振順豐二廠"
assert row2["supplier_work_order_no"] == "SUP-101"
assert row2["outsource_work_order_no"] == "OUT-201"
assert row2["work_order_no"] == ""

sid2 = save_measurement_session(
    "C:/tmp/meas_legacy.csv",
    product_name="LegacyProduct",
    work_order_no="WO-LEGACY-1",
)
row3 = get_measurement_session(sid2)
assert row3 is not None
assert row3["work_order_no"] == ""
assert row3["supplier"] == ""
assert row3["supplier_work_order_no"] == ""
assert row3["outsource_work_order_no"] == ""
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
