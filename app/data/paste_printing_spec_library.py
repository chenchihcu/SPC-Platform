"""
錫膏印刷規格版本庫（產品層）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.data.master_data_db import db_conn, normalize_product_name
from app.data.sql_filters import append_joined_product_version_filters

DEFAULT_HEIGHT_TARGET = 100.0


def list_paste_printing_spec_versions(
    *,
    product_name: str = "",
    product_name_exact: bool = False,
    product_part_no: str = "",
    date_from: str = "",
    date_to: str = "",
    keyword: str = "",
    limit: int = 200,
) -> List[Dict[str, Any]]:
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
        date_column="pv.updated_at",
    )
    if keyword:
        kw = f"%{keyword.lower()}%"
        clauses.append("(LOWER(p.product_name) LIKE ? OR LOWER(p.product_part_no) LIKE ?)")
        params.extend([kw, kw])

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT
            pv.id,
            pv.product_id,
            p.product_name,
            p.product_part_no,
            pv.default_volume_target,
            pv.default_volume_lsl,
            pv.default_volume_usl,
            pv.default_area_target,
            pv.default_area_lsl,
            pv.default_area_usl,
            pv.default_height_lsl,
            pv.default_height_usl,
            pv.updated_at,
            pv.is_active
        FROM paste_printing_spec_versions pv
        JOIN products p ON pv.product_id = p.id
        {where_sql}
        ORDER BY pv.updated_at DESC
        LIMIT ?
    """
    params.append(limit)
    with db_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    payload: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["default_height_target"] = DEFAULT_HEIGHT_TARGET
        payload.append(item)
    return payload


def set_active_paste_printing_spec_version(version_id: int) -> bool:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT product_id FROM paste_printing_spec_versions WHERE id = ?",
            (version_id,),
        ).fetchone()
        if not row:
            return False
        pid = int(row["product_id"])
        conn.execute(
            "UPDATE paste_printing_spec_versions SET is_active = 0 WHERE product_id = ?",
            (pid,),
        )
        cur = conn.execute(
            "UPDATE paste_printing_spec_versions SET is_active = 1 WHERE id = ?",
            (version_id,),
        )
        return cur.rowcount > 0


def delete_paste_printing_spec_version(version_id: int) -> bool:
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM paste_printing_spec_versions WHERE id = ?", (version_id,))
        return cur.rowcount > 0


def update_paste_printing_spec_metadata(
    version_id: int,
    *,
    product_name: Optional[str] = None,
    product_part_no: Optional[str] = None,
    default_volume_target: Optional[float] = None,
    default_volume_lsl: Optional[float] = None,
    default_volume_usl: Optional[float] = None,
    default_area_target: Optional[float] = None,
    default_area_lsl: Optional[float] = None,
    default_area_usl: Optional[float] = None,
    default_height_lsl: Optional[float] = None,
    default_height_usl: Optional[float] = None,
) -> bool:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT product_id FROM paste_printing_spec_versions WHERE id = ?",
            (version_id,),
        ).fetchone()
        if not row:
            return False
        pid = int(row["product_id"])

        product_updates: List[str] = []
        product_params: List[Any] = []
        if product_name is not None:
            name = normalize_product_name(product_name)
            product_updates.extend(["product_name = ?", "product_name_ci = ?"])
            product_params.extend([name, name.lower()])
        if product_part_no is not None:
            product_updates.append("product_part_no = ?")
            product_params.append(product_part_no.strip())

        product_changed = False
        if product_updates:
            product_params.append(pid)
            cur = conn.execute(
                f"UPDATE products SET {', '.join(product_updates)} WHERE id = ?",
                product_params,
            )
            product_changed = cur.rowcount > 0

        spec_updates: List[str] = []
        spec_params: List[Any] = []
        for column, value in (
            ("default_volume_target", default_volume_target),
            ("default_volume_lsl", default_volume_lsl),
            ("default_volume_usl", default_volume_usl),
            ("default_area_target", default_area_target),
            ("default_area_lsl", default_area_lsl),
            ("default_area_usl", default_area_usl),
            ("default_height_lsl", default_height_lsl),
            ("default_height_usl", default_height_usl),
        ):
            if value is None:
                continue
            spec_updates.append(f"{column} = ?")
            spec_params.append(float(value))
        if spec_updates:
            spec_updates.append("updated_at = ?")
            spec_params.append(datetime.now().isoformat())
            spec_params.append(version_id)
            conn.execute(
                f"UPDATE paste_printing_spec_versions SET {', '.join(spec_updates)} WHERE id = ?",
                spec_params,
            )
            return True
        return product_changed
