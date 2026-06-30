"""
SPI 規格版本庫相容層（legacy facade）。

新架構改為雙庫後，此模組以錫膏印刷規格版本（paste_printing_spec_versions）為主，
並附帶 active 鋼板厚度資訊供舊畫面欄位顯示。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.data.master_data_db import db_conn
from app.data.paste_printing_spec_library import (
    delete_paste_printing_spec_version,
    list_paste_printing_spec_versions,
    set_active_paste_printing_spec_version,
    update_paste_printing_spec_metadata,
)
from app.data.stencil_thickness_registry import UNIT_MODE_ABSOLUTE


def list_spec_versions(
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
    相容查詢：以錫膏印刷規格版本為主，附帶產品 active 鋼板厚度資訊。
    """
    paste_rows = list_paste_printing_spec_versions(
        product_name=product_name,
        product_name_exact=product_name_exact,
        product_part_no=product_part_no,
        date_from=date_from,
        date_to=date_to,
        keyword=keyword,
        limit=limit,
    )
    if not paste_rows:
        return []
    product_ids = sorted({int(r.get("product_id") or 0) for r in paste_rows if int(r.get("product_id") or 0) > 0})
    if not product_ids:
        return paste_rows

    placeholders = ",".join(["?"] * len(product_ids))
    with db_conn() as conn:
        stencil_rows = conn.execute(
            f"""
            SELECT
                product_id,
                stencil_type,
                thickness_main,
                thickness_precision,
                precision_is_main,
                unit_mode,
                height_denominator_mm
            FROM stencil_thickness_versions
            WHERE is_active = 1 AND product_id IN ({placeholders})
            """,
            product_ids,
        ).fetchall()
    stencil_map = {int(r["product_id"]): dict(r) for r in stencil_rows}

    merged: List[Dict[str, Any]] = []
    for row in paste_rows:
        item = dict(row)
        st = stencil_map.get(int(item.get("product_id") or 0), {})
        item["stencil_type"] = st.get("stencil_type", "normal")
        item["thickness_main"] = st.get("thickness_main", 0.12)
        item["thickness_precision"] = st.get("thickness_precision")
        item["precision_is_main"] = st.get("precision_is_main", 0)
        item["unit_mode"] = st.get("unit_mode", "percent")
        item["height_denominator_mm"] = st.get("height_denominator_mm")
        if str(item.get("unit_mode") or "").strip().lower() == UNIT_MODE_ABSOLUTE:
            try:
                denominator = float(item.get("height_denominator_mm") or item.get("thickness_main") or 0.12)
            except (TypeError, ValueError):
                denominator = 0.12
            item["default_height_target"] = denominator
        else:
            item["default_height_target"] = 100.0
        merged.append(item)
    return merged


def set_active_spec_version(version_id: int) -> bool:
    """相容 API：切換錫膏印刷規格 active 版本。"""
    return set_active_paste_printing_spec_version(version_id)


def delete_spec_version(version_id: int) -> bool:
    """相容 API：刪除錫膏印刷規格版本。"""
    return delete_paste_printing_spec_version(version_id)


def update_spec_metadata(
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
    default_height_target: Optional[float] = None,
    default_height_lsl: Optional[float] = None,
    default_height_usl: Optional[float] = None,
) -> bool:
    """
    相容 API：
    - Height target 已改為鋼板基準推導，不在錫膏庫儲存。
    - `default_height_target` 參數保留但忽略。
    """
    _ = default_height_target  # compatibility no-op
    return update_paste_printing_spec_metadata(
        version_id,
        product_name=product_name,
        product_part_no=product_part_no,
        default_volume_target=default_volume_target,
        default_volume_lsl=default_volume_lsl,
        default_volume_usl=default_volume_usl,
        default_area_target=default_area_target,
        default_area_lsl=default_area_lsl,
        default_area_usl=default_area_usl,
        default_height_lsl=default_height_lsl,
        default_height_usl=default_height_usl,
    )
