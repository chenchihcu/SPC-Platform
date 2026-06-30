"""
鋼板厚度規格版本庫（產品層）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.data.master_data_db import db_conn, normalize_product_name
from app.data.sql_filters import append_joined_product_version_filters
from app.data.stencil_thickness_registry import (
    STENCIL_NORMAL,
    STENCIL_STEPPED,
    UNIT_MODE_ABSOLUTE,
    UNIT_MODE_PERCENT,
)


def list_stencil_thickness_versions(
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
        date_column="sv.updated_at",
    )
    if keyword:
        kw = f"%{keyword.lower()}%"
        clauses.append(
            "(LOWER(p.product_name) LIKE ? OR LOWER(p.product_part_no) LIKE ? OR LOWER(sv.stencil_type) LIKE ?)"
        )
        params.extend([kw, kw, kw])

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT
            sv.id,
            sv.product_id,
            p.product_name,
            p.product_part_no,
            sv.stencil_type,
            sv.thickness_main,
            sv.thickness_precision,
            sv.precision_is_main,
            sv.unit_mode,
            sv.height_denominator_mm,
            sv.updated_at,
            sv.is_active
        FROM stencil_thickness_versions sv
        JOIN products p ON sv.product_id = p.id
        {where_sql}
        ORDER BY sv.updated_at DESC
        LIMIT ?
    """
    params.append(limit)
    with db_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def set_active_stencil_thickness_version(version_id: int) -> bool:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT product_id FROM stencil_thickness_versions WHERE id = ?",
            (version_id,),
        ).fetchone()
        if not row:
            return False
        pid = int(row["product_id"])
        conn.execute(
            "UPDATE stencil_thickness_versions SET is_active = 0 WHERE product_id = ?",
            (pid,),
        )
        cur = conn.execute(
            "UPDATE stencil_thickness_versions SET is_active = 1 WHERE id = ?",
            (version_id,),
        )
        return cur.rowcount > 0


def delete_stencil_thickness_version(version_id: int) -> bool:
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM stencil_thickness_versions WHERE id = ?", (version_id,))
        return cur.rowcount > 0


def update_stencil_thickness_metadata(
    version_id: int,
    *,
    product_name: Optional[str] = None,
    product_part_no: Optional[str] = None,
    stencil_type: Optional[str] = None,
    thickness_main: Optional[float] = None,
    thickness_precision: Optional[float] = None,
    precision_is_main: Optional[bool] = None,
    unit_mode: Optional[str] = None,
    height_denominator_mm: Optional[float] = None,
) -> bool:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT product_id FROM stencil_thickness_versions WHERE id = ?",
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
        if stencil_type is not None:
            normalized = str(stencil_type).strip().lower()
            if normalized not in (STENCIL_NORMAL, STENCIL_STEPPED):
                normalized = STENCIL_NORMAL
            spec_updates.append("stencil_type = ?")
            spec_params.append(normalized)
        if thickness_main is not None:
            spec_updates.append("thickness_main = ?")
            spec_params.append(float(thickness_main))
        if thickness_precision is not None:
            spec_updates.append("thickness_precision = ?")
            spec_params.append(float(thickness_precision))
        if precision_is_main is not None:
            spec_updates.append("precision_is_main = ?")
            spec_params.append(1 if precision_is_main else 0)
        if unit_mode is not None:
            normalized_mode = str(unit_mode).strip().lower()
            if normalized_mode not in (UNIT_MODE_PERCENT, UNIT_MODE_ABSOLUTE):
                normalized_mode = UNIT_MODE_PERCENT
            spec_updates.append("unit_mode = ?")
            spec_params.append(normalized_mode)
        if height_denominator_mm is not None:
            spec_updates.append("height_denominator_mm = ?")
            spec_params.append(float(height_denominator_mm))

        if spec_updates:
            spec_updates.append("updated_at = ?")
            spec_params.append(datetime.now().isoformat())
            spec_params.append(version_id)
            conn.execute(
                f"UPDATE stencil_thickness_versions SET {', '.join(spec_updates)} WHERE id = ?",
                spec_params,
            )
            return True
        return product_changed
