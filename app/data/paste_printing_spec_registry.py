"""
錫膏印刷規格主檔（產品層 active 視角）。

管理範圍：
- Volume/Area 目標與上下限
- Height 上下限（target 由鋼板厚度規格基準決定，不在此表維護）
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

DEFAULT_VOLUME_TARGET = 100.0
DEFAULT_VOLUME_LSL = 70.0
DEFAULT_VOLUME_USL = 150.0
DEFAULT_AREA_TARGET = 100.0
DEFAULT_AREA_LSL = 70.0
DEFAULT_AREA_USL = 150.0
DEFAULT_HEIGHT_TARGET = 100.0
DEFAULT_HEIGHT_LSL = 70.0
DEFAULT_HEIGHT_USL = 140.0


def list_products() -> List[str]:
    """回傳已建立 active 錫膏印刷規格之產品名稱列表。"""
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT p.product_name
            FROM products p
            JOIN paste_printing_spec_versions pv
              ON pv.product_id = p.id AND pv.is_active = 1
            ORDER BY p.product_name_ci ASC
            """
        ).fetchall()
    return [str(r["product_name"] or "").strip() for r in rows if str(r["product_name"] or "").strip()]


def get(product_name: str) -> Optional[Dict[str, Any]]:
    """依產品名稱取得 active 錫膏印刷規格。"""
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
                pv.default_volume_target AS default_volume_target,
                pv.default_volume_lsl AS default_volume_lsl,
                pv.default_volume_usl AS default_volume_usl,
                pv.default_area_target AS default_area_target,
                pv.default_area_lsl AS default_area_lsl,
                pv.default_area_usl AS default_area_usl,
                pv.default_height_lsl AS default_height_lsl,
                pv.default_height_usl AS default_height_usl,
                pv.updated_at AS updated_at
            FROM paste_printing_spec_versions pv
            JOIN products p ON p.id = pv.product_id
            WHERE pv.product_id = ? AND pv.is_active = 1
            ORDER BY pv.updated_at DESC, pv.id DESC
            LIMIT 1
            """,
            (pid,),
        ).fetchone()
    if row is None:
        return None
    return {
        "product_name": str(row["product_name"] or ""),
        "default_volume_target": float(row["default_volume_target"] or DEFAULT_VOLUME_TARGET),
        "default_volume_lsl": float(row["default_volume_lsl"] or DEFAULT_VOLUME_LSL),
        "default_volume_usl": float(row["default_volume_usl"] or DEFAULT_VOLUME_USL),
        "default_area_target": float(row["default_area_target"] or DEFAULT_AREA_TARGET),
        "default_area_lsl": float(row["default_area_lsl"] or DEFAULT_AREA_LSL),
        "default_area_usl": float(row["default_area_usl"] or DEFAULT_AREA_USL),
        "default_height_target": DEFAULT_HEIGHT_TARGET,
        "default_height_lsl": float(row["default_height_lsl"] or DEFAULT_HEIGHT_LSL),
        "default_height_usl": float(row["default_height_usl"] or DEFAULT_HEIGHT_USL),
        "updated_at": str(row["updated_at"] or ""),
    }


def save(spec: Dict[str, Any]) -> bool:
    """儲存一筆產品層錫膏印刷規格，並切換為 active。"""
    product_name = normalize_product_name(spec.get("product_name") or "")
    if not product_name:
        return False
    product_part_no = str(spec.get("product_part_no") or "").strip()
    try:
        payload = {
            "default_volume_target": float(spec.get("default_volume_target", DEFAULT_VOLUME_TARGET)),
            "default_volume_lsl": float(spec.get("default_volume_lsl", DEFAULT_VOLUME_LSL)),
            "default_volume_usl": float(spec.get("default_volume_usl", DEFAULT_VOLUME_USL)),
            "default_area_target": float(spec.get("default_area_target", DEFAULT_AREA_TARGET)),
            "default_area_lsl": float(spec.get("default_area_lsl", DEFAULT_AREA_LSL)),
            "default_area_usl": float(spec.get("default_area_usl", DEFAULT_AREA_USL)),
            "default_height_lsl": float(spec.get("default_height_lsl", DEFAULT_HEIGHT_LSL)),
            "default_height_usl": float(spec.get("default_height_usl", DEFAULT_HEIGHT_USL)),
        }
    except (TypeError, ValueError):
        return False

    updated_at = datetime.now().isoformat()
    try:
        with db_conn() as conn:
            pid = upsert_product(conn, product_name, product_part_no)
            conn.execute(
                "UPDATE paste_printing_spec_versions SET is_active = 0 WHERE product_id = ?",
                (pid,),
            )
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
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    pid,
                    payload["default_volume_target"],
                    payload["default_volume_lsl"],
                    payload["default_volume_usl"],
                    payload["default_area_target"],
                    payload["default_area_lsl"],
                    payload["default_area_usl"],
                    payload["default_height_lsl"],
                    payload["default_height_usl"],
                    updated_at,
                ),
            )
        return True
    except (OSError, TypeError, ValueError):
        return False


def remove(product_name: str) -> bool:
    """移除指定產品之所有錫膏印刷規格版本。"""
    key = normalize_product_name(product_name)
    if not key:
        return False
    with db_conn() as conn:
        pid = get_product_id(conn, key)
        if pid is None:
            return False
        cur = conn.execute("DELETE FROM paste_printing_spec_versions WHERE product_id = ?", (pid,))
        return int(cur.rowcount) > 0
