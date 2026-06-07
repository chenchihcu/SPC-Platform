"""Isolated SQLite e2e: supplier library auto-code + migration contracts."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _run_child(repo: Path, code: str) -> None:
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r}\\nstdout={proc.stdout!r}"


def test_supplier_library_auto_code_and_update_contract_in_sqlite_subprocess() -> None:
    repo = Path(__file__).resolve().parents[1]
    fd, db_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(db_str)
    try:
        code = f"""
import os
import sys

os.environ["SPC_MASTER_DB_PATH"] = {str(db_path)!r}
sys.path.insert(0, {str(repo)!r})

from app.data.supplier_library import (
    create_supplier_record,
    delete_supplier_record,
    list_supplier_records,
    update_supplier_record,
)

rid1 = create_supplier_record(
    supplier_name="Alpha Supplier",
    steel_plate_no="ST-9001",
    steel_plate_production_date="2026-03-15",
)
rid2 = create_supplier_record(
    supplier_name="Alpha Supplier",
    steel_plate_no="ST-9002",
    steel_plate_production_date="2026-03-16",
)
rid3 = create_supplier_record(
    supplier_name="Beta Supplier",
    steel_plate_no="ST-9003",
    steel_plate_production_date="2026-03-17",
)
assert isinstance(rid1, int) and rid1 > 0
assert isinstance(rid2, int) and rid2 > 0
assert isinstance(rid3, int) and rid3 > 0

alpha_rows = list_supplier_records(supplier_name="Alpha Supplier")
assert len(alpha_rows) == 2
assert {{str(r["supplier_code"]) for r in alpha_rows}} == {{"SUP-0001"}}

beta_rows = list_supplier_records(supplier_name="Beta Supplier")
assert len(beta_rows) == 1
assert beta_rows[0]["supplier_code"] == "SUP-0002"

ok = update_supplier_record(
    rid1,
    supplier_name="Alpha Supplier Renamed",
    steel_plate_no="ST-9010",
    steel_plate_production_date="2026-03-18",
)
assert ok is True

renamed_rows = list_supplier_records(supplier_name="Alpha Supplier Renamed")
assert len(renamed_rows) == 1
assert renamed_rows[0]["supplier_code"] == "SUP-0001"
assert renamed_rows[0]["steel_plate_no"] == "ST-9010"
assert renamed_rows[0]["steel_plate_production_date"] == "2026-03-18"

rid4 = create_supplier_record(
    supplier_name="Alpha Supplier Renamed",
    steel_plate_no="ST-9011",
    steel_plate_production_date="2026-03-19",
)
renamed_rows2 = list_supplier_records(supplier_name="Alpha Supplier Renamed")
assert len(renamed_rows2) == 2
assert {{str(r["supplier_code"]) for r in renamed_rows2}} == {{"SUP-0001"}}
assert any(int(r["id"]) == rid4 for r in renamed_rows2)

deleted = delete_supplier_record(rid1)
assert deleted is True
"""
        _run_child(repo, code)
    finally:
        db_path.unlink(missing_ok=True)


def test_supplier_library_legacy_renumber_migration_success_in_sqlite_subprocess() -> None:
    repo = Path(__file__).resolve().parents[1]
    fd, db_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(db_str)
    try:
        code = f"""
import os
import sys

os.environ["SPC_MASTER_DB_PATH"] = {str(db_path)!r}
sys.path.insert(0, {str(repo)!r})

from app.data.master_data_db import db_conn
from app.data.supplier_library import create_supplier_record, list_supplier_records

MIGRATION_KEY = "supplier_code_auto_renumber_v1"

with db_conn() as conn:
    conn.execute("DELETE FROM supplier_records")
    conn.execute("DELETE FROM schema_meta WHERE key = ?", (MIGRATION_KEY,))
    now = "2026-04-22T10:30:00"
    conn.execute(
        '''
        INSERT INTO supplier_records(
            supplier_code, supplier_name, steel_plate_no, steel_plate_production_date, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?)
        ''',
        ("LEG-A", "Alpha", "PL-001", "2026-03-01", now, now),
    )
    conn.execute(
        '''
        INSERT INTO supplier_records(
            supplier_code, supplier_name, steel_plate_no, steel_plate_production_date, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?)
        ''',
        ("LEG-B", "Alpha", "PL-002", "2026-03-02", now, now),
    )
    conn.execute(
        '''
        INSERT INTO supplier_records(
            supplier_code, supplier_name, steel_plate_no, steel_plate_production_date, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?)
        ''',
        ("LEG-C", "Beta", "PL-003", "2026-03-03", now, now),
    )

rows = list_supplier_records(limit=20)
code_by_plate = {{str(r["steel_plate_no"]): str(r["supplier_code"]) for r in rows}}
assert code_by_plate["PL-001"] == "SUP-0001"
assert code_by_plate["PL-002"] == "SUP-0001"
assert code_by_plate["PL-003"] == "SUP-0002"

with db_conn() as conn:
    marker = conn.execute(
        "SELECT value FROM schema_meta WHERE key = ?",
        (MIGRATION_KEY,),
    ).fetchone()
    assert marker is not None and str(marker["value"]) == "1"

rid = create_supplier_record(
    supplier_name="Gamma",
    steel_plate_no="PL-004",
    steel_plate_production_date="2026-03-04",
)
gamma_rows = list_supplier_records(supplier_name="Gamma")
assert len(gamma_rows) == 1
assert int(gamma_rows[0]["id"]) == rid
assert gamma_rows[0]["supplier_code"] == "SUP-0003"
"""
        _run_child(repo, code)
    finally:
        db_path.unlink(missing_ok=True)


def test_supplier_library_legacy_renumber_migration_conflict_abort_in_sqlite_subprocess() -> None:
    repo = Path(__file__).resolve().parents[1]
    fd, db_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(db_str)
    try:
        code = f"""
import os
import sys

os.environ["SPC_MASTER_DB_PATH"] = {str(db_path)!r}
sys.path.insert(0, {str(repo)!r})

from app.data.master_data_db import db_conn
from app.data.supplier_library import (
    SupplierCodeMigrationConflictError,
    list_supplier_records,
)

MIGRATION_KEY = "supplier_code_auto_renumber_v1"

with db_conn() as conn:
    conn.execute("DELETE FROM supplier_records")
    conn.execute("DELETE FROM schema_meta WHERE key = ?", (MIGRATION_KEY,))
    now = "2026-04-22T10:30:00"
    conn.execute(
        '''
        INSERT INTO supplier_records(
            supplier_code, supplier_name, steel_plate_no, steel_plate_production_date, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?)
        ''',
        ("OLD-01", "Alpha", "DUP-001", "2026-03-01", now, now),
    )
    conn.execute(
        '''
        INSERT INTO supplier_records(
            supplier_code, supplier_name, steel_plate_no, steel_plate_production_date, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?)
        ''',
        ("OLD-02", "Alpha", "DUP-001", "2026-03-02", now, now),
    )

try:
    list_supplier_records(limit=20)
    raise AssertionError("Expected SupplierCodeMigrationConflictError")
except SupplierCodeMigrationConflictError as exc:
    msg = str(exc)
    assert "Alpha" in msg
    assert "DUP-001" in msg

with db_conn() as conn:
    marker = conn.execute(
        "SELECT value FROM schema_meta WHERE key = ?",
        (MIGRATION_KEY,),
    ).fetchone()
    assert marker is None
    rows = conn.execute(
        "SELECT supplier_code FROM supplier_records ORDER BY id ASC"
    ).fetchall()
    assert [str(r["supplier_code"]) for r in rows] == ["OLD-01", "OLD-02"]
"""
        _run_child(repo, code)
    finally:
        db_path.unlink(missing_ok=True)
