"""
座標檔註冊表：產品名稱/料號與座標檔路徑的持久化對應。
自 2026-04 起改由 SQLite (`data/spc_master.db`) 持久化。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.data.master_data_db import (
    db_conn,
    file_sha256,
    get_product_id,
    normalize_product_name,
    upsert_product,
)

logger = logging.getLogger(__name__)


def list_registered() -> List[Dict[str, Any]]:
    """
    回傳已註冊的座標清單（active 版本），每筆含：
    product_name, product_part_no, file_path, created_at。
    """
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                p.product_name AS product_name,
                p.product_part_no AS product_part_no,
                cv.file_path AS file_path,
                cv.created_at AS created_at
            FROM products p
            JOIN coordinate_versions cv
              ON cv.product_id = p.id AND cv.is_active = 1
            ORDER BY p.product_name_ci ASC, cv.created_at ASC
            """
        ).fetchall()
    return [
        {
            "product_name": str(r["product_name"] or "").strip(),
            "product_part_no": str(r["product_part_no"] or "").strip(),
            "file_path": str(r["file_path"] or "").strip(),
            "created_at": str(r["created_at"] or ""),
        }
        for r in rows
    ]


def register(product_name: str, file_path: str, product_part_no: str = "", row_count: Optional[int] = None) -> bool:
    """
    將座標檔與產品名稱（及選填產品料號）綁定並寫入註冊表。
    行為：同一產品新增一筆新版本並切換為 active（舊版本保留）。
    """
    product_name = normalize_product_name(product_name)
    file_path = (file_path or "").strip()
    if not product_name or not file_path:
        return False

    try:
        with db_conn() as conn:
            pid = upsert_product(conn, product_name, (product_part_no or "").strip())
            conn.execute(
                "UPDATE coordinate_versions SET is_active = 0 WHERE product_id = ?",
                (pid,),
            )
            conn.execute(
                """
                INSERT INTO coordinate_versions(
                    product_id, file_path, file_hash, row_count, schema_result, created_at, is_active
                )
                VALUES(?, ?, ?, ?, '', ?, 1)
                """,
                (
                    pid,
                    file_path,
                    file_sha256(file_path),
                    row_count,
                    datetime.now().isoformat(),
                ),
            )
        return True
    except (OSError, ValueError):
        return False


def get_path_by_product_name(product_name: str) -> Optional[str]:
    """依產品名稱回傳已註冊的座標檔路徑；若無則回傳 None。"""
    key = normalize_product_name(product_name)
    if not key:
        return None
    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return None
        row = conn.execute(
            """
            SELECT file_path
            FROM coordinate_versions
            WHERE product_id = ? AND is_active = 1
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (pid,),
        ).fetchone()
    if row is None:
        return None
    path = str(row["file_path"] or "").strip()
    return path if path else None


def remove_by_product_name(product_name: str) -> bool:
    """
    從註冊表移除指定產品名稱的紀錄；
    並同步移除該產品之鋼板規格與階梯指派。
    """
    key = normalize_product_name(product_name)
    if not key:
        return False

    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return False
        conn.execute("DELETE FROM products WHERE id = ?", (pid,))
    # Compatibility: keep cascading clean-up call semantics explicit.
    try:
        from app.data.product_spec_registry import remove as remove_product_spec
        from app.data.stencil_assignment_registry import clear_by_product
        remove_product_spec(key)
        clear_by_product(key)
    except ImportError:
        logger.exception("coordinate cleanup dependency import failed for product=%s", key)
        return False
    return True
