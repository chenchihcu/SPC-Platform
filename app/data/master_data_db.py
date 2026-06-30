"""
SQLite-backed master data store for product/coordinate/spec/assignment registries.

Compatibility goals:
- Keep existing registry module function signatures unchanged.
- Migrate legacy JSON registries into SQLite on first initialization.
- Enforce case-insensitive product uniqueness via `product_name_ci`.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

DB_FILENAME = "spc_master.db"
# Optional absolute path to a SQLite file (tests / automation). When unset, uses data_dir() / DB_FILENAME.
_MASTER_DB_PATH_ENV = "SPC_MASTER_DB_PATH"
MIGRATION_KEY = "json_registry_migrated_v1"
WORK_ORDER_CLEAR_MIGRATION_KEY = "measurement_work_order_cleared_v1"
SPEC_SPLIT_MIGRATION_KEY = "spec_versions_split_v1"
_MEASUREMENT_SESSIONS_SCHEMA_SQL = """
        CREATE TABLE IF NOT EXISTS measurement_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product_name TEXT NOT NULL DEFAULT '',
            supplier TEXT NOT NULL DEFAULT '',
            work_order_no TEXT NOT NULL DEFAULT '',
            supplier_work_order_no TEXT NOT NULL DEFAULT '',
            outsource_work_order_no TEXT NOT NULL DEFAULT '',
            batch_no TEXT NOT NULL DEFAULT '',
            product_part_no TEXT NOT NULL DEFAULT '',
            file_path TEXT NOT NULL,
            file_hash TEXT NOT NULL DEFAULT '',
            row_count INTEGER,
            upload_datetime TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_meas_sessions_product
            ON measurement_sessions(product_id);
        CREATE INDEX IF NOT EXISTS idx_meas_sessions_upload
            ON measurement_sessions(upload_datetime);
        CREATE INDEX IF NOT EXISTS idx_meas_sessions_workorder
            ON measurement_sessions(work_order_no);
"""

_SUPPLIER_RECORDS_SCHEMA_SQL = """
        CREATE TABLE IF NOT EXISTS supplier_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_code TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            steel_plate_no TEXT NOT NULL,
            steel_plate_production_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_supplier_records_unique
            ON supplier_records(supplier_code, steel_plate_no);
        CREATE INDEX IF NOT EXISTS idx_supplier_records_code
            ON supplier_records(supplier_code);
        CREATE INDEX IF NOT EXISTS idx_supplier_records_name
            ON supplier_records(supplier_name);
        CREATE INDEX IF NOT EXISTS idx_supplier_records_production_date
            ON supplier_records(steel_plate_production_date);
"""

_INIT_LOCK = threading.Lock()
_INITIALIZED = False


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def data_dir() -> Path:
    return _repo_root() / "data"


def db_path() -> Path:
    override = (os.environ.get(_MASTER_DB_PATH_ENV) or "").strip()
    if override:
        return Path(override)
    return data_dir() / DB_FILENAME


def _coordinate_json_path() -> Path:
    return data_dir() / "coordinate_registry.json"


def _spec_json_path() -> Path:
    return data_dir() / "product_spec_registry.json"


def _assignment_json_path() -> Path:
    return data_dir() / "stencil_assignments.json"


def now_iso() -> str:
    return datetime.now().isoformat()


def normalize_product_name(name: str) -> str:
    return (name or "").strip()


def normalize_product_name_ci(name: str) -> str:
    return normalize_product_name(name).lower()


def file_sha256(path: str) -> str:
    p = (path or "").strip()
    if not p:
        return ""
    fp = Path(p)
    if not fp.exists() or not fp.is_file():
        return ""
    h = hashlib.sha256()
    try:
        with open(fp, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _last_insert_id(cur: sqlite3.Cursor) -> int:
    row_id = cur.lastrowid
    if row_id is None:
        raise RuntimeError("SQLite did not return lastrowid for insert")
    return int(row_id)


def _ensure_data_dir() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            product_name_ci TEXT NOT NULL UNIQUE,
            product_part_no TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS coordinate_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            file_hash TEXT NOT NULL DEFAULT '',
            row_count INTEGER,
            schema_result TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_coordinate_versions_product
            ON coordinate_versions(product_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_coordinate_active_unique
            ON coordinate_versions(product_id)
            WHERE is_active = 1;

        CREATE TABLE IF NOT EXISTS spec_versions (
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
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_spec_versions_product
            ON spec_versions(product_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_spec_active_unique
            ON spec_versions(product_id)
            WHERE is_active = 1;

        CREATE TABLE IF NOT EXISTS paste_printing_spec_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            default_volume_target REAL NOT NULL,
            default_volume_lsl REAL NOT NULL,
            default_volume_usl REAL NOT NULL,
            default_area_target REAL NOT NULL,
            default_area_lsl REAL NOT NULL,
            default_area_usl REAL NOT NULL,
            default_height_lsl REAL NOT NULL,
            default_height_usl REAL NOT NULL,
            updated_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_paste_printing_spec_versions_product
            ON paste_printing_spec_versions(product_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_paste_printing_spec_active_unique
            ON paste_printing_spec_versions(product_id)
            WHERE is_active = 1;

        CREATE TABLE IF NOT EXISTS stencil_thickness_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            stencil_type TEXT NOT NULL,
            thickness_main REAL NOT NULL,
            thickness_precision REAL,
            precision_is_main INTEGER NOT NULL DEFAULT 0,
            unit_mode TEXT NOT NULL DEFAULT 'percent',
            height_denominator_mm REAL,
            updated_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_stencil_thickness_versions_product
            ON stencil_thickness_versions(product_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_stencil_thickness_active_unique
            ON stencil_thickness_versions(product_id)
            WHERE is_active = 1;

        CREATE TABLE IF NOT EXISTS stencil_assignment_meta (
            product_id INTEGER PRIMARY KEY,
            coord_file_path TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS stencil_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            refdes TEXT NOT NULL,
            assigned_profile TEXT NOT NULL DEFAULT 'precision',
            assignment_source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(product_id, refdes)
        );
        CREATE INDEX IF NOT EXISTS idx_stencil_assignments_product
            ON stencil_assignments(product_id);

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            operation_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT 'system'
        );
        """
        + _MEASUREMENT_SESSIONS_SCHEMA_SQL
        + _SUPPLIER_RECORDS_SCHEMA_SQL
    )


def _ensure_spec_height_columns(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add height limit columns to spec_versions table if missing."""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(spec_versions)").fetchall()]
    if "default_height_target" not in cols:
        conn.execute("ALTER TABLE spec_versions ADD COLUMN default_height_target REAL NOT NULL DEFAULT 100.0")
    if "default_height_lsl" not in cols:
        conn.execute("ALTER TABLE spec_versions ADD COLUMN default_height_lsl REAL NOT NULL DEFAULT 70.0")
    if "default_height_usl" not in cols:
        conn.execute("ALTER TABLE spec_versions ADD COLUMN default_height_usl REAL NOT NULL DEFAULT 140.0")


def _ensure_stencil_thickness_columns(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add unit columns to stencil_thickness_versions if missing."""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(stencil_thickness_versions)").fetchall()]
    if not cols:
        return
    if "unit_mode" not in cols:
        conn.execute(
            "ALTER TABLE stencil_thickness_versions "
            "ADD COLUMN unit_mode TEXT NOT NULL DEFAULT 'percent'"
        )
    if "height_denominator_mm" not in cols:
        conn.execute("ALTER TABLE stencil_thickness_versions ADD COLUMN height_denominator_mm REAL")


def _ensure_measurement_sessions_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add measurement_sessions table + metadata columns."""
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='measurement_sessions'"
    ).fetchone()
    if not exists:
        conn.executescript(_MEASUREMENT_SESSIONS_SCHEMA_SQL)
    _ensure_measurement_sessions_metadata_columns(conn)


def _ensure_measurement_sessions_metadata_columns(conn: sqlite3.Connection) -> None:
    """Idempotent migration: ensure measurement_sessions metadata fields exist."""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(measurement_sessions)").fetchall()]
    if "supplier" not in cols:
        conn.execute(
            "ALTER TABLE measurement_sessions "
            "ADD COLUMN supplier TEXT NOT NULL DEFAULT ''"
        )
    if "supplier_work_order_no" not in cols:
        conn.execute(
            "ALTER TABLE measurement_sessions "
            "ADD COLUMN supplier_work_order_no TEXT NOT NULL DEFAULT ''"
        )
    if "outsource_work_order_no" not in cols:
        conn.execute(
            "ALTER TABLE measurement_sessions "
            "ADD COLUMN outsource_work_order_no TEXT NOT NULL DEFAULT ''"
        )


def _ensure_supplier_records_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add supplier_records table to existing DBs."""
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='supplier_records'"
    ).fetchone()
    if exists:
        return
    conn.executescript(_SUPPLIER_RECORDS_SCHEMA_SQL)


def _schema_meta_value(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    return str(row["value"])


def _set_schema_meta_value(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO schema_meta(key, value)
        VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def get_product_id(conn: sqlite3.Connection, product_name: str) -> Optional[int]:
    key_ci = normalize_product_name_ci(product_name)
    if not key_ci:
        return None
    row = conn.execute(
        "SELECT id FROM products WHERE product_name_ci = ?",
        (key_ci,),
    ).fetchone()
    return int(row["id"]) if row is not None else None


def upsert_product(
    conn: sqlite3.Connection,
    product_name: str,
    product_part_no: str = "",
    *,
    status: str = "active",
    created_at: Optional[str] = None,
) -> int:
    name = normalize_product_name(product_name)
    if not name:
        raise ValueError("product_name is required")
    name_ci = normalize_product_name_ci(name)
    now = now_iso()
    created = created_at or now
    row = conn.execute(
        """
        SELECT id, product_name, product_part_no, status, created_at
        FROM products
        WHERE product_name_ci = ?
        """,
        (name_ci,),
    ).fetchone()
    if row is None:
        cur = conn.execute(
            """
            INSERT INTO products(
                product_name, product_name_ci, product_part_no, status, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                name_ci,
                (product_part_no or "").strip(),
                status if status in ("active", "inactive") else "active",
                created,
                now,
            ),
        )
        return _last_insert_id(cur)

    product_id = int(row["id"])
    prev_part_no = str(row["product_part_no"] or "")
    next_part_no = (product_part_no or "").strip() or prev_part_no
    next_status = status if status in ("active", "inactive") else str(row["status"] or "active")
    conn.execute(
        """
        UPDATE products
        SET product_name = ?,
            product_part_no = ?,
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (name, next_part_no, next_status, now, product_id),
    )
    return product_id


def _import_coordinate_registry(conn: sqlite3.Connection) -> None:
    payload = _read_json(_coordinate_json_path())
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return

    normalized_entries = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        product_name = normalize_product_name(str(e.get("product_name", "")))
        file_path = str(e.get("file_path", "")).strip()
        if not product_name or not file_path:
            continue
        normalized_entries.append(
            {
                "product_name": product_name,
                "product_part_no": str(e.get("product_part_no", "")).strip(),
                "file_path": file_path,
                "created_at": str(e.get("created_at", "")).strip() or now_iso(),
            }
        )

    normalized_entries.sort(key=lambda x: x["created_at"])
    active_row_id_by_product: Dict[int, int] = {}
    for entry in normalized_entries:
        pid = upsert_product(
            conn,
            entry["product_name"],
            entry["product_part_no"],
            created_at=entry["created_at"],
        )
        cur = conn.execute(
            """
            INSERT INTO coordinate_versions(
                product_id, file_path, file_hash, row_count, schema_result, created_at, is_active
            )
            VALUES(?, ?, ?, NULL, '', ?, 0)
            """,
            (
                pid,
                entry["file_path"],
                file_sha256(entry["file_path"]),
                entry["created_at"],
            ),
        )
        active_row_id_by_product[pid] = _last_insert_id(cur)

    for pid, rid in active_row_id_by_product.items():
        conn.execute("UPDATE coordinate_versions SET is_active = 0 WHERE product_id = ?", (pid,))
        conn.execute(
            "UPDATE coordinate_versions SET is_active = 1 WHERE id = ? AND product_id = ?",
            (rid, pid),
        )


def _import_spec_registry(conn: sqlite3.Connection) -> None:
    payload = _read_json(_spec_json_path())
    specs = payload.get("specs")
    if not isinstance(specs, dict):
        return

    rows = []
    for _, raw in specs.items():
        if not isinstance(raw, dict):
            continue
        product_name = normalize_product_name(str(raw.get("product_name", "")))
        if not product_name:
            continue
        updated_at = str(raw.get("updated_at", "")).strip() or now_iso()
        rows.append((updated_at, product_name, raw))

    rows.sort(key=lambda x: x[0])
    active_row_id_by_product: Dict[int, int] = {}
    for updated_at, product_name, raw in rows:
        pid = upsert_product(conn, product_name, "")
        cur = conn.execute(
            """
            INSERT INTO spec_versions(
                product_id,
                stencil_type,
                thickness_main,
                thickness_precision,
                precision_is_main,
                default_volume_target,
                default_volume_lsl,
                default_volume_usl,
                default_area_target,
                default_area_lsl,
                default_area_usl,
                default_height_target,
                default_height_lsl,
                default_height_usl,
                updated_at,
                is_active
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                pid,
                str(raw.get("stencil_type", "normal") or "normal").strip().lower(),
                float(raw.get("thickness_main", 0.12)),
                (
                    float(raw["thickness_precision"])
                    if raw.get("thickness_precision") is not None
                    else None
                ),
                1 if bool(raw.get("precision_is_main", False)) else 0,
                float(raw.get("default_volume_target", 100.0)),
                float(raw.get("default_volume_lsl", 70.0)),
                float(raw.get("default_volume_usl", 150.0)),
                float(raw.get("default_area_target", 100.0)),
                float(raw.get("default_area_lsl", 70.0)),
                float(raw.get("default_area_usl", 150.0)),
                float(raw.get("default_height_target", 100.0)),
                float(raw.get("default_height_lsl", 70.0)),
                float(raw.get("default_height_usl", 140.0)),
                updated_at,
            ),
        )
        active_row_id_by_product[pid] = _last_insert_id(cur)

    for pid, rid in active_row_id_by_product.items():
        conn.execute("UPDATE spec_versions SET is_active = 0 WHERE product_id = ?", (pid,))
        conn.execute(
            "UPDATE spec_versions SET is_active = 1 WHERE id = ? AND product_id = ?",
            (rid, pid),
        )


def _import_assignment_registry(conn: sqlite3.Connection) -> None:
    payload = _read_json(_assignment_json_path())
    assignments = payload.get("assignments")
    coord_map = payload.get("coord_path_by_product")
    if not isinstance(assignments, dict):
        assignments = {}
    if not isinstance(coord_map, dict):
        coord_map = {}

    for product_name, raw_list in assignments.items():
        if not isinstance(raw_list, list):
            continue
        name = normalize_product_name(str(product_name))
        if not name:
            continue
        pid = upsert_product(conn, name, "")
        conn.execute("DELETE FROM stencil_assignments WHERE product_id = ?", (pid,))
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            refdes = str(item.get("refdes", "")).strip()
            if not refdes:
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO stencil_assignments(
                    product_id, refdes, assigned_profile, assignment_source, created_at
                )
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    refdes,
                    str(item.get("assigned_profile", "precision") or "precision").strip() or "precision",
                    str(item.get("assignment_source", "manual") or "manual").strip() or "manual",
                    now_iso(),
                ),
            )

    # Persist coord path map even when assignment list is empty.
    for product_name, coord_path in coord_map.items():
        name = normalize_product_name(str(product_name))
        if not name:
            continue
        pid = upsert_product(conn, name, "")
        conn.execute(
            """
            INSERT INTO stencil_assignment_meta(product_id, coord_file_path, updated_at)
            VALUES(?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                coord_file_path = excluded.coord_file_path,
                updated_at = excluded.updated_at
            """,
            (pid, str(coord_path or "").strip(), now_iso()),
        )


def _run_legacy_json_migration(conn: sqlite3.Connection) -> None:
    if _schema_meta_value(conn, MIGRATION_KEY) == "1":
        return

    _import_coordinate_registry(conn)
    _import_spec_registry(conn)
    _import_assignment_registry(conn)
    _set_schema_meta_value(conn, MIGRATION_KEY, "1")


def _clear_legacy_work_order_column(conn: sqlite3.Connection) -> None:
    """One-shot migration: clear legacy work_order_no values for all measurement sessions."""
    if _schema_meta_value(conn, WORK_ORDER_CLEAR_MIGRATION_KEY) == "1":
        return
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='measurement_sessions'"
    ).fetchone()
    if exists:
        conn.execute("UPDATE measurement_sessions SET work_order_no = '' WHERE work_order_no <> ''")
    _set_schema_meta_value(conn, WORK_ORDER_CLEAR_MIGRATION_KEY, "1")


def _run_spec_split_migration(conn: sqlite3.Connection) -> None:
    """
    One-shot migration: split legacy mixed `spec_versions` rows into
    - paste_printing_spec_versions
    - stencil_thickness_versions
    """
    if _schema_meta_value(conn, SPEC_SPLIT_MIGRATION_KEY) == "1":
        return

    legacy_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='spec_versions'"
    ).fetchone()
    if not legacy_exists:
        _set_schema_meta_value(conn, SPEC_SPLIT_MIGRATION_KEY, "1")
        return

    paste_cnt_row = conn.execute("SELECT COUNT(1) AS cnt FROM paste_printing_spec_versions").fetchone()
    stencil_cnt_row = conn.execute("SELECT COUNT(1) AS cnt FROM stencil_thickness_versions").fetchone()
    paste_cnt = int((paste_cnt_row["cnt"] if paste_cnt_row else 0) or 0)
    stencil_cnt = int((stencil_cnt_row["cnt"] if stencil_cnt_row else 0) or 0)
    if paste_cnt > 0 or stencil_cnt > 0:
        _set_schema_meta_value(conn, SPEC_SPLIT_MIGRATION_KEY, "1")
        return

    rows = conn.execute(
        """
        SELECT
            product_id,
            stencil_type,
            thickness_main,
            thickness_precision,
            precision_is_main,
            default_volume_target,
            default_volume_lsl,
            default_volume_usl,
            default_area_target,
            default_area_lsl,
            default_area_usl,
            default_height_lsl,
            default_height_usl,
            updated_at,
            is_active
        FROM spec_versions
        ORDER BY updated_at ASC, id ASC
        """
    ).fetchall()

    for row in rows:
        product_id = int(row["product_id"])
        thickness_main = float(row["thickness_main"] or 0.12)
        denominator = thickness_main if thickness_main > 0 else 0.12
        is_active = 1 if int(row["is_active"] or 0) else 0
        updated_at = str(row["updated_at"] or now_iso())

        conn.execute(
            """
            INSERT INTO paste_printing_spec_versions(
                product_id,
                default_volume_target,
                default_volume_lsl,
                default_volume_usl,
                default_area_target,
                default_area_lsl,
                default_area_usl,
                default_height_lsl,
                default_height_usl,
                updated_at,
                is_active
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                float(row["default_volume_target"] or 100.0),
                float(row["default_volume_lsl"] or 70.0),
                float(row["default_volume_usl"] or 150.0),
                float(row["default_area_target"] or 100.0),
                float(row["default_area_lsl"] or 70.0),
                float(row["default_area_usl"] or 150.0),
                float(row["default_height_lsl"] or 70.0),
                float(row["default_height_usl"] or 140.0),
                updated_at,
                is_active,
            ),
        )

        conn.execute(
            """
            INSERT INTO stencil_thickness_versions(
                product_id,
                stencil_type,
                thickness_main,
                thickness_precision,
                precision_is_main,
                unit_mode,
                height_denominator_mm,
                updated_at,
                is_active
            )
            VALUES(?, ?, ?, ?, ?, 'percent', ?, ?, ?)
            """,
            (
                product_id,
                str(row["stencil_type"] or "normal").strip().lower() or "normal",
                thickness_main,
                (
                    float(row["thickness_precision"])
                    if row["thickness_precision"] is not None
                    else None
                ),
                1 if int(row["precision_is_main"] or 0) else 0,
                denominator,
                updated_at,
                is_active,
            ),
        )

    _set_schema_meta_value(conn, SPEC_SPLIT_MIGRATION_KEY, "1")


def init_db() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    with _INIT_LOCK:
        if _INITIALIZED:
            return
        _ensure_data_dir()
        with sqlite3.connect(db_path()) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            _create_schema(conn)
            _ensure_measurement_sessions_table(conn)
            _ensure_supplier_records_table(conn)
            _ensure_spec_height_columns(conn)
            _ensure_stencil_thickness_columns(conn)
            _run_legacy_json_migration(conn)
            _run_spec_split_migration(conn)
            _clear_legacy_work_order_column(conn)
            conn.commit()
        _INITIALIZED = True


@contextmanager
def db_conn() -> Iterator[sqlite3.Connection]:
    init_db()
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
