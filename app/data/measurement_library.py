"""
量測資料庫 (Measurement Session Library)

提供量測 CSV 上傳後的本機 SQLite 儲存與查詢功能。
每次上傳的量測資料會記錄至 measurement_sessions 表，
支援依產品名稱、工單編號、日期範圍、關鍵字搜尋。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.data.master_data_db import (
    db_conn,
    file_sha256,
    get_product_id,
    now_iso,
    normalize_product_name,
)


def save_measurement_session(
    file_path: str,
    *,
    product_name: str = "",
    supplier: str = "",
    work_order_no: str = "",
    supplier_work_order_no: str = "",
    outsource_work_order_no: str = "",
    batch_no: str = "",
    product_part_no: str = "",
    row_count: Optional[int] = None,
    notes: str = "",
) -> int:
    """
    儲存一筆量測上傳記錄至資料庫。

    Returns:
        新記錄的 id（整數）。
    """
    file_path = (file_path or "").strip()
    if not file_path:
        raise ValueError("file_path is required")

    p_name = normalize_product_name(product_name)
    fhash = file_sha256(file_path)
    now = now_iso()
    supplier_name = (supplier or "").strip()
    supplier_wo = (supplier_work_order_no or "").strip()
    outsource_wo = (outsource_work_order_no or "").strip()

    with db_conn() as conn:
        product_id: Optional[int] = None
        if p_name:
            product_id = get_product_id(conn, p_name)

        cur = conn.execute(
            """
            INSERT INTO measurement_sessions(
                product_id, product_name, supplier, work_order_no,
                supplier_work_order_no, outsource_work_order_no, batch_no,
                product_part_no, file_path, file_hash, row_count,
                upload_datetime, notes
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                p_name,
                supplier_name,
                "",
                supplier_wo,
                outsource_wo,
                (batch_no or "").strip(),
                (product_part_no or "").strip(),
                file_path,
                fhash,
                row_count,
                now,
                (notes or "").strip(),
            ),
        )
        return int(cur.lastrowid)  # type: ignore[arg-type]


def list_measurement_sessions(
    *,
    product_name: str = "",
    product_name_exact: bool = False,
    work_order_no: str = "",
    supplier_work_order_no: str = "",
    outsource_work_order_no: str = "",
    batch_no: str = "",
    product_part_no: str = "",
    date_from: str = "",
    date_to: str = "",
    keyword: str = "",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    查詢量測記錄，支援多條件搜尋。

    product_name_exact=True 時使用完全相符比對（下拉選單用）；
    False 時使用 LIKE 模糊比對（關鍵字文字搜尋用）。
    keyword 會比對 product_name、supplier、work_order_no、supplier_work_order_no、
    outsource_work_order_no、batch_no、product_part_no、file_path、notes。
    日期格式使用 ISO 8601（YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SS）。

    Returns:
        list of dict，由新到舊排序。
    """
    clauses: List[str] = []
    params: List[Any] = []

    if product_name:
        if product_name_exact:
            clauses.append("LOWER(product_name) = ?")
            params.append(product_name.lower())
        else:
            clauses.append("LOWER(product_name) LIKE ?")
            params.append(f"%{product_name.lower()}%")

    if work_order_no:
        kw_work_order = f"%{work_order_no.lower()}%"
        clauses.append(
            "("
            "LOWER(work_order_no) LIKE ? OR "
            "LOWER(supplier_work_order_no) LIKE ? OR "
            "LOWER(outsource_work_order_no) LIKE ?"
            ")"
        )
        params.extend([kw_work_order, kw_work_order, kw_work_order])

    if supplier_work_order_no:
        clauses.append("LOWER(supplier_work_order_no) LIKE ?")
        params.append(f"%{supplier_work_order_no.lower()}%")

    if outsource_work_order_no:
        clauses.append("LOWER(outsource_work_order_no) LIKE ?")
        params.append(f"%{outsource_work_order_no.lower()}%")

    if batch_no:
        clauses.append("LOWER(batch_no) LIKE ?")
        params.append(f"%{batch_no.lower()}%")

    if product_part_no:
        clauses.append("LOWER(product_part_no) LIKE ?")
        params.append(f"%{product_part_no.lower()}%")

    if date_from:
        clauses.append("upload_datetime >= ?")
        params.append(date_from)

    if date_to:
        # 包含當天結尾
        end = date_to if "T" in date_to else f"{date_to}T23:59:59"
        clauses.append("upload_datetime <= ?")
        params.append(end)

    if keyword:
        kw = f"%{keyword.lower()}%"
        clauses.append(
            "(LOWER(product_name) LIKE ? OR LOWER(supplier) LIKE ? OR LOWER(work_order_no) LIKE ?"
            " OR LOWER(supplier_work_order_no) LIKE ? OR LOWER(outsource_work_order_no) LIKE ?"
            " OR LOWER(batch_no) LIKE ? OR LOWER(product_part_no) LIKE ?"
            " OR LOWER(file_path) LIKE ? OR LOWER(notes) LIKE ?)"
        )
        params.extend([kw, kw, kw, kw, kw, kw, kw, kw, kw])

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT id, product_id, product_name, work_order_no,
               supplier, supplier_work_order_no, outsource_work_order_no, batch_no,
               product_part_no, file_path, file_hash, row_count,
               upload_datetime, notes
        FROM measurement_sessions
        {where_sql}
        ORDER BY upload_datetime DESC
        LIMIT ?
    """
    params.append(limit)

    with db_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_measurement_session(session_id: int) -> Optional[Dict[str, Any]]:
    """取得單筆量測記錄。"""
    with db_conn() as conn:
        row = conn.execute(
            """
            SELECT id, product_id, product_name, work_order_no,
                   supplier, supplier_work_order_no, outsource_work_order_no, batch_no,
                   product_part_no, file_path, file_hash, row_count,
                   upload_datetime, notes
            FROM measurement_sessions WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
        return dict(row) if row else None


def update_measurement_session(
    session_id: int,
    *,
    product_name: Optional[str] = None,
    supplier: Optional[str] = None,
    work_order_no: Optional[str] = None,
    supplier_work_order_no: Optional[str] = None,
    outsource_work_order_no: Optional[str] = None,
    batch_no: Optional[str] = None,
    product_part_no: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    """
    更新量測記錄的中繼資料（不更改檔案路徑與雜湊）。

    Returns:
        True 若有更新，False 若 id 不存在。
    """
    updates: List[str] = []
    params: List[Any] = []

    if product_name is not None:
        p_name = normalize_product_name(product_name)
        updates.append("product_name = ?")
        params.append(p_name)
        # 同步 product_id
        updates.append("product_id = (SELECT id FROM products WHERE product_name_ci = ? LIMIT 1)")
        params.append(p_name.lower())

    if work_order_no is not None:
        updates.append("work_order_no = ?")
        params.append("")

    if supplier is not None:
        updates.append("supplier = ?")
        params.append((supplier or "").strip())

    if supplier_work_order_no is not None:
        updates.append("supplier_work_order_no = ?")
        params.append((supplier_work_order_no or "").strip())

    if outsource_work_order_no is not None:
        updates.append("outsource_work_order_no = ?")
        params.append((outsource_work_order_no or "").strip())

    if batch_no is not None:
        updates.append("batch_no = ?")
        params.append((batch_no or "").strip())

    if product_part_no is not None:
        updates.append("product_part_no = ?")
        params.append((product_part_no or "").strip())

    if notes is not None:
        updates.append("notes = ?")
        params.append((notes or "").strip())

    if updates and work_order_no is None:
        updates.append("work_order_no = ?")
        params.append("")

    if not updates:
        return False

    params.append(session_id)
    sql = f"UPDATE measurement_sessions SET {', '.join(updates)} WHERE id = ?"
    with db_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.rowcount > 0


def delete_measurement_session(session_id: int) -> bool:
    """
    刪除一筆量測記錄（僅刪除 DB 記錄，不刪除本機檔案）。

    Returns:
        True 若成功刪除。
    """
    with db_conn() as conn:
        cur = conn.execute(
            "DELETE FROM measurement_sessions WHERE id = ?",
            (session_id,),
        )
        return cur.rowcount > 0


def list_product_names_with_sessions() -> List[str]:
    """回傳所有有量測記錄的產品名稱（供下拉篩選用）。"""
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT product_name FROM measurement_sessions
            WHERE product_name != ''
            ORDER BY product_name COLLATE NOCASE
            """
        ).fetchall()
        return [str(r["product_name"]) for r in rows]
