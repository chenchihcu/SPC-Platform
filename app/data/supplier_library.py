"""
供應商資料庫 (Supplier Library)

提供供應商管理分頁使用的查詢與維護操作。
"""
from __future__ import annotations

import re
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from app.data.master_data_db import db_conn, db_path, now_iso

_SUPPLIER_CODE_MIGRATION_META_KEY = "supplier_code_auto_renumber_v1"
_SUPPLIER_CODE_PREFIX = "SUP-"
_SUPPLIER_CODE_MIN_WIDTH = 4
_SUPPLIER_CODE_PATTERN = re.compile(r"^SUP-(\d+)$", re.IGNORECASE)
_MIGRATION_LOCK = threading.Lock()
_MIGRATION_READY_DB_PATH: Optional[str] = None


class SupplierCodeMigrationConflictError(ValueError):
    """歷史供應商編號重編時發生衝突（同新編號 + 同鋼板編號）。"""

    def __init__(self, conflicts: Sequence[Dict[str, Any]]) -> None:
        self.conflicts = list(conflicts)
        preview_parts: List[str] = []
        for c in self.conflicts[:5]:
            record_ids = ",".join(str(v) for v in c.get("record_ids", []))
            preview_parts.append(
                f"{c.get('supplier_name', '')} / {c.get('steel_plate_no', '')} / ids={record_ids}"
            )
        preview = "；".join(preview_parts)
        more = ""
        if len(self.conflicts) > 5:
            more = f"；另有 {len(self.conflicts) - 5} 筆未列出"
        message = (
            f"供應商編號自動重編中止：偵測到 {len(self.conflicts)} 筆同名同鋼板衝突。"
            f"請先清理資料後再重試。衝突摘要：{preview}{more}"
        )
        super().__init__(message)


def _validate_required(name: str, value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{name}不可空白。")
    return normalized


def _validate_date(date_text: str) -> str:
    value = _validate_required("鋼板生產日期", date_text)
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("鋼板生產日期格式需為 YYYY-MM-DD。") from exc
    return value


def _set_schema_meta_value(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO schema_meta(key, value)
        VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def _parse_generated_supplier_code(code: str) -> Optional[int]:
    raw = (code or "").strip().upper()
    if not raw:
        return None
    match = _SUPPLIER_CODE_PATTERN.fullmatch(raw)
    if not match:
        return None
    try:
        value = int(match.group(1))
    except ValueError:
        return None
    return value if value > 0 else None


def _format_supplier_code(sequence_no: int) -> str:
    return f"{_SUPPLIER_CODE_PREFIX}{sequence_no:0{_SUPPLIER_CODE_MIN_WIDTH}d}"


def _current_db_key() -> str:
    return str(db_path().resolve())


def _run_supplier_code_renumber_migration(conn: sqlite3.Connection) -> None:
    marker = conn.execute(
        "SELECT value FROM schema_meta WHERE key = ?",
        (_SUPPLIER_CODE_MIGRATION_META_KEY,),
    ).fetchone()
    if marker is not None and str(marker["value"]) == "1":
        return

    rows = conn.execute(
        """
        SELECT id, supplier_name, steel_plate_no
        FROM supplier_records
        ORDER BY id ASC
        """
    ).fetchall()
    if not rows:
        _set_schema_meta_value(conn, _SUPPLIER_CODE_MIGRATION_META_KEY, "1")
        return

    sequence_no = 1
    supplier_name_to_code: Dict[str, str] = {}
    assignments: List[Dict[str, Any]] = []
    for row in rows:
        supplier_name = _validate_required("供應商名稱", str(row["supplier_name"] or ""))
        steel_plate_no = _validate_required("鋼板編號", str(row["steel_plate_no"] or ""))
        supplier_code = supplier_name_to_code.get(supplier_name)
        if supplier_code is None:
            supplier_code = _format_supplier_code(sequence_no)
            supplier_name_to_code[supplier_name] = supplier_code
            sequence_no += 1
        assignments.append(
            {
                "id": int(row["id"]),
                "supplier_name": supplier_name,
                "steel_plate_no": steel_plate_no,
                "supplier_code": supplier_code,
            }
        )

    seen: Dict[tuple[str, str], Dict[str, Any]] = {}
    conflicts: List[Dict[str, Any]] = []
    for item in assignments:
        key = (str(item["supplier_code"]), str(item["steel_plate_no"]))
        bucket = seen.get(key)
        if bucket is None:
            seen[key] = {
                "supplier_code": key[0],
                "steel_plate_no": key[1],
                "supplier_name": item["supplier_name"],
                "record_ids": [int(item["id"])],
            }
            continue
        bucket["record_ids"].append(int(item["id"]))
    for value in seen.values():
        if len(value["record_ids"]) > 1:
            conflicts.append(value)
    if conflicts:
        raise SupplierCodeMigrationConflictError(conflicts)

    for item in assignments:
        conn.execute(
            "UPDATE supplier_records SET supplier_code = ? WHERE id = ?",
            (str(item["supplier_code"]), int(item["id"])),
        )
    _set_schema_meta_value(conn, _SUPPLIER_CODE_MIGRATION_META_KEY, "1")


def _ensure_supplier_code_migration_applied() -> None:
    global _MIGRATION_READY_DB_PATH
    db_key = _current_db_key()
    if _MIGRATION_READY_DB_PATH == db_key:
        return
    with _MIGRATION_LOCK:
        if _MIGRATION_READY_DB_PATH == db_key:
            return
        with db_conn() as conn:
            _run_supplier_code_renumber_migration(conn)
        _MIGRATION_READY_DB_PATH = db_key


def _pick_existing_supplier_code(conn: sqlite3.Connection, supplier_name: str) -> Optional[str]:
    row = conn.execute(
        """
        SELECT supplier_code
        FROM supplier_records
        WHERE TRIM(supplier_name) = ? AND supplier_code != ''
        ORDER BY id ASC
        LIMIT 1
        """,
        (supplier_name,),
    ).fetchone()
    if row is None:
        return None
    code = str(row["supplier_code"] or "").strip()
    if not code:
        return None
    seq = _parse_generated_supplier_code(code)
    if seq is None:
        return code
    return _format_supplier_code(seq)


def _next_supplier_code(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT supplier_code FROM supplier_records").fetchall()
    max_seq = 0
    for row in rows:
        seq = _parse_generated_supplier_code(str(row["supplier_code"] or ""))
        if seq is not None and seq > max_seq:
            max_seq = seq
    return _format_supplier_code(max_seq + 1)


def _resolve_supplier_code_for_create(conn: sqlite3.Connection, supplier_name: str) -> str:
    existing = _pick_existing_supplier_code(conn, supplier_name)
    if existing:
        return existing
    return _next_supplier_code(conn)


def list_supplier_records(
    *,
    supplier_code: str = "",
    supplier_name: str = "",
    steel_plate_no: str = "",
    date_from: str = "",
    date_to: str = "",
    keyword: str = "",
    limit: int = 300,
) -> List[Dict[str, Any]]:
    """查詢供應商管理資料。"""
    _ensure_supplier_code_migration_applied()
    clauses: List[str] = []
    params: List[Any] = []

    if supplier_code:
        clauses.append("LOWER(supplier_code) LIKE ?")
        params.append(f"%{supplier_code.lower()}%")
    if supplier_name:
        clauses.append("LOWER(supplier_name) LIKE ?")
        params.append(f"%{supplier_name.lower()}%")
    if steel_plate_no:
        clauses.append("LOWER(steel_plate_no) LIKE ?")
        params.append(f"%{steel_plate_no.lower()}%")
    if date_from:
        clauses.append("steel_plate_production_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("steel_plate_production_date <= ?")
        params.append(date_to)
    if keyword:
        kw = f"%{keyword.lower()}%"
        clauses.append(
            "(LOWER(supplier_code) LIKE ? OR LOWER(supplier_name) LIKE ?"
            " OR LOWER(steel_plate_no) LIKE ?)"
        )
        params.extend([kw, kw, kw])

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT
            id,
            supplier_code,
            supplier_name,
            steel_plate_no,
            steel_plate_production_date,
            created_at,
            updated_at
        FROM supplier_records
        {where_sql}
        ORDER BY updated_at DESC
        LIMIT ?
    """
    params.append(limit)
    with db_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def list_supplier_codes(*, limit: int = 500) -> List[str]:
    """回傳供應商編號清單（供下拉篩選）。"""
    _ensure_supplier_code_migration_applied()
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT supplier_code
            FROM supplier_records
            WHERE supplier_code != ''
            ORDER BY supplier_code COLLATE NOCASE
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [str(r["supplier_code"]) for r in rows]


def list_supplier_names(*, limit: int = 500) -> List[str]:
    """回傳供應商名稱清單（供資料設定頁下拉選單）。"""
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT supplier_name
            FROM supplier_records
            WHERE supplier_name != ''
            ORDER BY supplier_name COLLATE NOCASE
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [str(r["supplier_name"]) for r in rows]


def create_supplier_record(
    *,
    supplier_name: str,
    steel_plate_no: str,
    steel_plate_production_date: str,
) -> int:
    """新增供應商管理資料。"""
    _ensure_supplier_code_migration_applied()
    name = _validate_required("供應商名稱", supplier_name)
    plate_no = _validate_required("鋼板編號", steel_plate_no)
    production_date = _validate_date(steel_plate_production_date)
    now = now_iso()
    with db_conn() as conn:
        code = _resolve_supplier_code_for_create(conn, name)
        cur = conn.execute(
            """
            INSERT INTO supplier_records(
                supplier_code,
                supplier_name,
                steel_plate_no,
                steel_plate_production_date,
                created_at,
                updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (code, name, plate_no, production_date, now, now),
        )
    return int(cur.lastrowid)  # type: ignore[arg-type]


def update_supplier_record(
    record_id: int,
    *,
    supplier_name: Optional[str] = None,
    steel_plate_no: Optional[str] = None,
    steel_plate_production_date: Optional[str] = None,
) -> bool:
    """更新供應商管理資料。"""
    _ensure_supplier_code_migration_applied()
    updates: List[str] = []
    params: List[Any] = []

    if supplier_name is not None:
        updates.append("supplier_name = ?")
        params.append(_validate_required("供應商名稱", supplier_name))
    if steel_plate_no is not None:
        updates.append("steel_plate_no = ?")
        params.append(_validate_required("鋼板編號", steel_plate_no))
    if steel_plate_production_date is not None:
        updates.append("steel_plate_production_date = ?")
        params.append(_validate_date(steel_plate_production_date))

    if not updates:
        return False

    updates.append("updated_at = ?")
    params.append(now_iso())
    params.append(int(record_id))
    sql = f"UPDATE supplier_records SET {', '.join(updates)} WHERE id = ?"
    with db_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.rowcount > 0


def delete_supplier_record(record_id: int) -> bool:
    """刪除供應商管理資料。"""
    _ensure_supplier_code_migration_applied()
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM supplier_records WHERE id = ?", (int(record_id),))
        return cur.rowcount > 0
