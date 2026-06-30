"""
鋼板厚度規格主檔（產品層 active 視角）。

管理範圍：
- 鋼板類型、主/精密厚度、精密指派策略
- Height 單位模式與換算分母（給 resolver 轉換用）
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.data.master_data_db import (
    db_conn,
    get_product_id,
    normalize_product_name,
    upsert_product,
)

STENCIL_NORMAL = "normal"
STENCIL_STEPPED = "stepped"

UNIT_MODE_PERCENT = "percent"
UNIT_MODE_ABSOLUTE = "absolute"

DEFAULT_THICKNESS_MAIN = 0.12
DEFAULT_THICKNESS_PRECISION = 0.08
DEFAULT_HEIGHT_TARGET = 100.0
DEFAULT_HEIGHT_LSL = 70.0
DEFAULT_HEIGHT_USL = 140.0


def list_products() -> List[str]:
    """回傳已建立 active 鋼板厚度規格之產品名稱列表。"""
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT p.product_name
            FROM products p
            JOIN stencil_thickness_versions sv
              ON sv.product_id = p.id AND sv.is_active = 1
            ORDER BY p.product_name_ci ASC
            """
        ).fetchall()
    return [str(r["product_name"] or "").strip() for r in rows if str(r["product_name"] or "").strip()]


def get(product_name: str) -> Optional[Dict[str, Any]]:
    """依產品名稱取得 active 鋼板厚度規格。"""
    key = normalize_product_name(product_name)
    if not key:
        return None
    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return None
        row = conn.execute(
            """
            SELECT
                p.product_name AS product_name,
                sv.stencil_type AS stencil_type,
                sv.thickness_main AS thickness_main,
                sv.thickness_precision AS thickness_precision,
                sv.precision_is_main AS precision_is_main,
                sv.unit_mode AS unit_mode,
                sv.height_denominator_mm AS height_denominator_mm,
                sv.updated_at AS updated_at
            FROM stencil_thickness_versions sv
            JOIN products p ON p.id = sv.product_id
            WHERE sv.product_id = ? AND sv.is_active = 1
            ORDER BY sv.updated_at DESC, sv.id DESC
            LIMIT 1
            """,
            (pid,),
        ).fetchone()
    if row is None:
        return None
    thickness_main = float(row["thickness_main"] or DEFAULT_THICKNESS_MAIN)
    denominator = row["height_denominator_mm"]
    return {
        "product_name": str(row["product_name"] or ""),
        "stencil_type": str(row["stencil_type"] or STENCIL_NORMAL),
        "thickness_main": thickness_main,
        "thickness_precision": (
            float(row["thickness_precision"])
            if row["thickness_precision"] is not None
            else None
        ),
        "precision_is_main": bool(int(row["precision_is_main"] or 0)),
        "unit_mode": str(row["unit_mode"] or UNIT_MODE_PERCENT),
        "height_denominator_mm": float(denominator) if denominator is not None else thickness_main,
        "updated_at": str(row["updated_at"] or ""),
    }


def save(spec: Dict[str, Any]) -> bool:
    """儲存一筆產品層鋼板厚度規格，並切換為 active。"""
    product_name = normalize_product_name(spec.get("product_name") or "")
    if not product_name:
        return False
    product_part_no = str(spec.get("product_part_no") or "").strip()

    stencil_type = str(spec.get("stencil_type") or STENCIL_NORMAL).strip().lower()
    if stencil_type not in (STENCIL_NORMAL, STENCIL_STEPPED):
        stencil_type = STENCIL_NORMAL

    unit_mode = str(spec.get("unit_mode") or UNIT_MODE_PERCENT).strip().lower()
    if unit_mode not in (UNIT_MODE_PERCENT, UNIT_MODE_ABSOLUTE):
        unit_mode = UNIT_MODE_PERCENT

    try:
        thickness_main = float(spec.get("thickness_main", DEFAULT_THICKNESS_MAIN))
        thickness_precision: Optional[float]
        if stencil_type == STENCIL_STEPPED:
            thickness_precision = float(spec.get("thickness_precision", DEFAULT_THICKNESS_PRECISION))
        else:
            thickness_precision = None
        precision_is_main = 1 if bool(spec.get("precision_is_main", False)) else 0
        denominator = float(spec.get("height_denominator_mm", thickness_main))
    except (TypeError, ValueError):
        return False

    if denominator <= 0:
        denominator = thickness_main if thickness_main > 0 else DEFAULT_THICKNESS_MAIN
    updated_at = datetime.now().isoformat()

    try:
        with db_conn() as conn:
            pid = upsert_product(conn, product_name, product_part_no)
            conn.execute(
                "UPDATE stencil_thickness_versions SET is_active = 0 WHERE product_id = ?",
                (pid,),
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
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    pid,
                    stencil_type,
                    thickness_main,
                    thickness_precision,
                    precision_is_main,
                    unit_mode,
                    denominator,
                    updated_at,
                ),
            )
        return True
    except (OSError, TypeError, ValueError):
        return False


def remove(product_name: str) -> bool:
    """移除指定產品之所有鋼板厚度規格版本。"""
    key = normalize_product_name(product_name)
    if not key:
        return False
    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return False
        cur = conn.execute("DELETE FROM stencil_thickness_versions WHERE product_id = ?", (pid,))
        return int(cur.rowcount) > 0


def build_height_spec(
    thickness: float,
    *,
    unit_mode: str = UNIT_MODE_PERCENT,
    height_denominator_mm: Optional[float] = None,
) -> Dict[str, float]:
    """
    由基準厚度推導 Height 規格（同一邏輯供 resolver 與相容層使用）。
    - percent 模式：固定百分比 target/lsl/usl
    - absolute 模式：以分母(mm)換算成絕對值界線
    """
    mode = str(unit_mode or UNIT_MODE_PERCENT).strip().lower()
    if mode == UNIT_MODE_ABSOLUTE:
        try:
            denominator = float(height_denominator_mm) if height_denominator_mm is not None else float(thickness)
        except (TypeError, ValueError):
            denominator = float(thickness or DEFAULT_THICKNESS_MAIN)
        if denominator <= 0:
            denominator = DEFAULT_THICKNESS_MAIN
        return {
            "target": denominator * DEFAULT_HEIGHT_TARGET / 100.0,
            "lsl": denominator * DEFAULT_HEIGHT_LSL / 100.0,
            "usl": denominator * DEFAULT_HEIGHT_USL / 100.0,
        }
    return {
        "target": DEFAULT_HEIGHT_TARGET,
        "lsl": DEFAULT_HEIGHT_LSL,
        "usl": DEFAULT_HEIGHT_USL,
    }
