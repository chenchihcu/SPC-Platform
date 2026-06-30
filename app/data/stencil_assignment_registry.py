"""
階梯鋼板 RefDes 指派（SQLite-backed）。

相容性行為：
- 對外函式簽名維持不變。
- 仍以 product_name 維度讀寫，內部映射至 products.id。
"""
from __future__ import annotations

from typing import List, Optional

from app.data.master_data_db import (
    db_conn,
    get_product_id,
    normalize_product_name,
    upsert_product,
)

ASSIGNMENT_SOURCE_MANUAL = "manual"
ASSIGNMENT_SOURCE_BATCH_RULE = "batch_rule"
ASSIGNMENT_SOURCE_DEFAULT = "default"
PROFILE_MAIN = "main"
PROFILE_PRECISION = "precision"


def list_precision_refdes(product_name: str) -> List[str]:
    """回傳該產品被指派為精密厚度的 RefDes 列表。"""
    key = normalize_product_name(product_name)
    if not key:
        return []
    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return []
        rows = conn.execute(
            """
            SELECT refdes
            FROM stencil_assignments
            WHERE product_id = ? AND assigned_profile = ?
            ORDER BY refdes ASC
            """,
            (pid, PROFILE_PRECISION),
        ).fetchall()
    return [str(r["refdes"] or "").strip() for r in rows if str(r["refdes"] or "").strip()]


def get_assignment_coord_path(product_name: str) -> Optional[str]:
    """回傳該產品建立指派時記錄的座標檔路徑；若無則 None。"""
    key = normalize_product_name(product_name)
    if not key:
        return None
    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return None
        row = conn.execute(
            """
            SELECT coord_file_path
            FROM stencil_assignment_meta
            WHERE product_id = ?
            """,
            (pid,),
        ).fetchone()
    if row is None:
        return None
    path = str(row["coord_file_path"] or "").strip()
    return path if path else None


def is_coord_path_changed(product_name: str, current_coord_path: Optional[str]) -> bool:
    """
    若該產品有階梯指派，且 current_coord_path 與記錄路徑不同（或記錄空白），
    視為座標已更新，應清空指派。無指派時回傳 False。
    """
    key = normalize_product_name(product_name)
    if not key:
        return False
    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return False
        row = conn.execute(
            "SELECT COUNT(1) AS cnt FROM stencil_assignments WHERE product_id = ?",
            (pid,),
        ).fetchone()
        has_assignments = bool(row and int(row["cnt"] or 0) > 0)
        if not has_assignments:
            return False
        meta = conn.execute(
            "SELECT coord_file_path FROM stencil_assignment_meta WHERE product_id = ?",
            (pid,),
        ).fetchone()

    recorded = str(meta["coord_file_path"] or "").strip() if meta else ""
    if not recorded:
        return True
    current = str(current_coord_path or "").strip()
    return current != recorded


def save_assignments(
    product_name: str,
    precision_refdes: List[str],
    coord_file_path: Optional[str] = None,
) -> bool:
    """
    儲存該產品的階梯指派（僅 precision 清單；其餘預設 main）。
    """
    key = normalize_product_name(product_name)
    if not key:
        return False
    try:
        with db_conn() as conn:
            pid = upsert_product(conn, key, "")
            conn.execute("DELETE FROM stencil_assignments WHERE product_id = ?", (pid,))
            refdes_set = sorted({str(r).strip() for r in precision_refdes if str(r).strip()})
            for refdes in refdes_set:
                conn.execute(
                    """
                    INSERT INTO stencil_assignments(
                        product_id, refdes, assigned_profile, assignment_source, created_at
                    )
                    VALUES(?, ?, ?, ?, datetime('now'))
                    """,
                    (pid, refdes, PROFILE_PRECISION, ASSIGNMENT_SOURCE_MANUAL),
                )
            if coord_file_path is not None:
                conn.execute(
                    """
                    INSERT INTO stencil_assignment_meta(product_id, coord_file_path, updated_at)
                    VALUES(?, ?, datetime('now'))
                    ON CONFLICT(product_id) DO UPDATE SET
                        coord_file_path = excluded.coord_file_path,
                        updated_at = excluded.updated_at
                    """,
                    (pid, str(coord_file_path or "").strip()),
                )
        return True
    except (OSError, ValueError):
        return False


def clear_by_product(product_name: str) -> bool:
    """清空該產品之所有階梯指派與對應座標路徑快照。"""
    key = normalize_product_name(product_name)
    if not key:
        return False
    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return False
        cur1 = conn.execute("DELETE FROM stencil_assignments WHERE product_id = ?", (pid,))
        cur2 = conn.execute("DELETE FROM stencil_assignment_meta WHERE product_id = ?", (pid,))
    return int(cur1.rowcount) > 0 or int(cur2.rowcount) > 0


def get_profile_by_refdes(product_name: str, refdes: str) -> str:
    """回傳該產品下此 RefDes 的 profile：main 或 precision。"""
    key = normalize_product_name(product_name)
    ref = str(refdes or "").strip()
    if not key or not ref:
        return PROFILE_MAIN
    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return PROFILE_MAIN
        row = conn.execute(
            """
            SELECT assigned_profile
            FROM stencil_assignments
            WHERE product_id = ? AND refdes = ?
            LIMIT 1
            """,
            (pid, ref),
        ).fetchone()
    if row is None:
        return PROFILE_MAIN
    return str(row["assigned_profile"] or PROFILE_MAIN)


def has_any_precision_assignment(product_name: str) -> bool:
    """該產品是否至少有一個精密厚度指派 RefDes。"""
    return len(list_precision_refdes(product_name)) > 0
