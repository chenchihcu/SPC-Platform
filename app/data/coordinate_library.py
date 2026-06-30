"""
座標資料庫 (Coordinate Version Library)

提供座標檔註冊後的歷史版本查詢與管理功能。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.data.master_data_db import (
    db_conn,
    normalize_product_name,
)
from app.data.sql_filters import append_joined_product_version_filters


def list_coordinate_versions(
    *,
    product_name: str = "",
    product_name_exact: bool = False,
    product_part_no: str = "",
    date_from: str = "",
    date_to: str = "",
    keyword: str = "",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    查詢座標版本記錄，支援多條件搜尋。
    """
    clauses: List[str] = []
    params: List[Any] = []

    append_joined_product_version_filters(
        clauses,
        params,
        product_name=product_name,
        product_name_exact=product_name_exact,
        product_part_no=product_part_no,
        date_from=date_from,
        date_to=date_to,
        date_column="cv.created_at",
    )

    if keyword:
        kw = f"%{keyword.lower()}%"
        clauses.append(
            "(LOWER(p.product_name) LIKE ? OR LOWER(p.product_part_no) LIKE ?"
            " OR LOWER(cv.file_path) LIKE ?)"
        )
        params.extend([kw, kw, kw])

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT
            cv.id,
            cv.product_id,
            p.product_name,
            p.product_part_no,
            cv.file_path,
            cv.file_hash,
            cv.row_count,
            cv.created_at,
            cv.is_active
        FROM coordinate_versions cv
        JOIN products p ON cv.product_id = p.id
        {where_sql}
        ORDER BY cv.created_at DESC
        LIMIT ?
    """
    params.append(limit)

    with db_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def set_active_coordinate_version(version_id: int) -> bool:
    """將指定的座標版本設為該產品的現行版本。"""
    with db_conn() as conn:
        # 取得該版本的 product_id
        row = conn.execute("SELECT product_id FROM coordinate_versions WHERE id = ?", (version_id,)).fetchone()
        if not row:
            return False
        pid = row["product_id"]

        # 將該產品的所有版本設為不啟用
        conn.execute("UPDATE coordinate_versions SET is_active = 0 WHERE product_id = ?", (pid,))
        # 將指定版本設為啟用
        cur = conn.execute("UPDATE coordinate_versions SET is_active = 1 WHERE id = ?", (version_id,))
        return cur.rowcount > 0


def delete_coordinate_version(version_id: int) -> bool:
    """刪除指定的座標版本（不刪除檔案）。"""
    with db_conn() as conn:
        # 檢查是否為啟用中版本，如果是則不允許直接刪除 (或需提醒)
        row = conn.execute("SELECT is_active FROM coordinate_versions WHERE id = ?", (version_id,)).fetchone()
        if row and row["is_active"]:
            # 如果是 active，可能需要先切換到別的版本或者不允許刪除
            # 這裡簡化處理：直接刪除，但如果有 CASCADE 可能會影響，不過目前 schema 是 product_id CASCADE
            pass

        cur = conn.execute("DELETE FROM coordinate_versions WHERE id = ?", (version_id,))
        return cur.rowcount > 0

def update_coordinate_metadata(
    version_id: int,
    *,
    product_name: Optional[str] = None,
    product_part_no: Optional[str] = None,
) -> bool:
    """更新座標關聯的產品資訊（同步更新 products 表）。"""
    # 注意：這裡會影響所有使用該 product_id 的版本
    with db_conn() as conn:
        row = conn.execute("SELECT product_id FROM coordinate_versions WHERE id = ?", (version_id,)).fetchone()
        if not row:
            return False
        pid = row["product_id"]

        updates = []
        params = []
        if product_name is not None:
            name = normalize_product_name(product_name)
            updates.append("product_name = ?")
            params.append(name)
            updates.append("product_name_ci = ?")
            params.append(name.lower())

        if product_part_no is not None:
            updates.append("product_part_no = ?")
            params.append(product_part_no.strip())

        if not updates:
            return False

        params.append(pid)
        sql = f"UPDATE products SET {', '.join(updates)} WHERE id = ?"
        cur = conn.execute(sql, params)
        return cur.rowcount > 0
