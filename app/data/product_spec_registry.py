"""
產品規格相容層（legacy facade）。

新架構已拆分為：
- paste_printing_spec_registry（錫膏印刷規格）
- stencil_thickness_registry（鋼板厚度規格）

此模組保留舊有 `get/save/remove/list_products/build_height_spec` 對外介面，
避免既有呼叫點一次性大改。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.data.paste_printing_spec_registry import (
    DEFAULT_AREA_LSL,
    DEFAULT_AREA_TARGET,
    DEFAULT_AREA_USL,
    DEFAULT_HEIGHT_LSL,
    DEFAULT_HEIGHT_TARGET,
    DEFAULT_HEIGHT_USL,
    DEFAULT_VOLUME_LSL,
    DEFAULT_VOLUME_TARGET,
    DEFAULT_VOLUME_USL,
    get as get_paste_spec,
    list_products as list_paste_products,
    remove as remove_paste_spec,
    save as save_paste_spec,
)
from app.data.stencil_thickness_registry import (
    STENCIL_NORMAL,
    STENCIL_STEPPED,
    UNIT_MODE_ABSOLUTE,
    UNIT_MODE_PERCENT,
    build_height_spec as _build_height_spec_new,
    get as get_stencil_spec,
    list_products as list_stencil_products,
    remove as remove_stencil_spec,
    save as save_stencil_spec,
)

__all__ = [
    "STENCIL_NORMAL",
    "STENCIL_STEPPED",
    "UNIT_MODE_PERCENT",
    "UNIT_MODE_ABSOLUTE",
    "list_products",
    "get",
    "save",
    "remove",
    "build_height_spec",
]


def list_products() -> List[str]:
    """
    回傳同時具備「錫膏印刷規格 + 鋼板厚度規格」active 設定的產品列表。
    """
    paste_names = {str(n).strip() for n in list_paste_products()}
    stencil_names = {str(n).strip() for n in list_stencil_products()}
    return sorted([n for n in paste_names.intersection(stencil_names) if n], key=str.lower)


def get(product_name: str) -> Optional[Dict[str, Any]]:
    """
    相容回傳：整合錫膏與鋼板兩庫為舊結構 dict。
    任一庫缺失時回傳 None（維持分析前 gate 行為）。
    """
    paste = get_paste_spec(product_name)
    stencil = get_stencil_spec(product_name)
    if not paste or not stencil:
        return None

    unit_mode = str(stencil.get("unit_mode") or UNIT_MODE_PERCENT).strip().lower()
    thickness_main = float(stencil.get("thickness_main") or 0.12)
    denominator = float(stencil.get("height_denominator_mm") or thickness_main or 0.12)
    if unit_mode == UNIT_MODE_ABSOLUTE:
        height_target = denominator * DEFAULT_HEIGHT_TARGET / 100.0
    else:
        height_target = DEFAULT_HEIGHT_TARGET

    updated_at = str(stencil.get("updated_at") or "") or str(paste.get("updated_at") or "")
    paste_updated = str(paste.get("updated_at") or "")
    if paste_updated and (not updated_at or paste_updated > updated_at):
        updated_at = paste_updated

    return {
        "product_name": str(stencil.get("product_name") or paste.get("product_name") or ""),
        "stencil_type": str(stencil.get("stencil_type") or STENCIL_NORMAL),
        "thickness_main": thickness_main,
        "thickness_precision": stencil.get("thickness_precision"),
        "precision_is_main": bool(stencil.get("precision_is_main", False)),
        "unit_mode": unit_mode,
        "height_denominator_mm": denominator,
        "default_volume_target": float(paste.get("default_volume_target") or DEFAULT_VOLUME_TARGET),
        "default_volume_lsl": float(paste.get("default_volume_lsl") or DEFAULT_VOLUME_LSL),
        "default_volume_usl": float(paste.get("default_volume_usl") or DEFAULT_VOLUME_USL),
        "default_area_target": float(paste.get("default_area_target") or DEFAULT_AREA_TARGET),
        "default_area_lsl": float(paste.get("default_area_lsl") or DEFAULT_AREA_LSL),
        "default_area_usl": float(paste.get("default_area_usl") or DEFAULT_AREA_USL),
        "default_height_target": float(height_target),
        "default_height_lsl": float(paste.get("default_height_lsl") or DEFAULT_HEIGHT_LSL),
        "default_height_usl": float(paste.get("default_height_usl") or DEFAULT_HEIGHT_USL),
        "updated_at": updated_at,
    }


def save(spec: Dict[str, Any]) -> bool:
    """
    相容儲存：將舊 payload 拆寫至兩個新規格庫。
    """
    product_name = str(spec.get("product_name") or "").strip()
    if not product_name:
        return False

    thickness_main = float(spec.get("thickness_main", 0.12))
    stencil_payload = {
        "product_name": product_name,
        "stencil_type": spec.get("stencil_type", STENCIL_NORMAL),
        "thickness_main": thickness_main,
        "thickness_precision": spec.get("thickness_precision"),
        "precision_is_main": bool(spec.get("precision_is_main", False)),
        "unit_mode": spec.get("unit_mode", UNIT_MODE_PERCENT),
        "height_denominator_mm": spec.get("height_denominator_mm", thickness_main),
    }
    paste_payload = {
        "product_name": product_name,
        "default_volume_target": spec.get("default_volume_target", DEFAULT_VOLUME_TARGET),
        "default_volume_lsl": spec.get("default_volume_lsl", DEFAULT_VOLUME_LSL),
        "default_volume_usl": spec.get("default_volume_usl", DEFAULT_VOLUME_USL),
        "default_area_target": spec.get("default_area_target", DEFAULT_AREA_TARGET),
        "default_area_lsl": spec.get("default_area_lsl", DEFAULT_AREA_LSL),
        "default_area_usl": spec.get("default_area_usl", DEFAULT_AREA_USL),
        "default_height_lsl": spec.get("default_height_lsl", DEFAULT_HEIGHT_LSL),
        "default_height_usl": spec.get("default_height_usl", DEFAULT_HEIGHT_USL),
    }
    return bool(save_stencil_spec(stencil_payload) and save_paste_spec(paste_payload))


def remove(product_name: str) -> bool:
    """移除指定產品的兩庫規格資料。"""
    removed_stencil = remove_stencil_spec(product_name)
    removed_paste = remove_paste_spec(product_name)
    return bool(removed_stencil or removed_paste)


def build_height_spec(thickness: float) -> Dict[str, float]:
    """相容函式：預設以 percent 模式回傳 Height 規格。"""
    return _build_height_spec_new(thickness, unit_mode=UNIT_MODE_PERCENT, height_denominator_mm=None)
