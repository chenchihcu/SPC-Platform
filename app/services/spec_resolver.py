"""
規格解析服務：
- 錫膏印刷規格（產品層）提供 Volume/Area + Height LSL/USL
- 鋼板厚度規格（產品層）提供 Height 基準（target）與單位模式
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

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
    get as get_paste_printing_spec,
)
from app.data.stencil_assignment_registry import (
    PROFILE_PRECISION,
    get_profile_by_refdes,
    has_any_precision_assignment,
)
from app.data.stencil_thickness_registry import (
    STENCIL_NORMAL,
    STENCIL_STEPPED,
    UNIT_MODE_ABSOLUTE,
    UNIT_MODE_PERCENT,
    get as get_stencil_thickness_spec,
)


# Length units the measurement loader uses to declare absolute Height data.
_ABSOLUTE_HEIGHT_UNITS = {"mm", "millimeter", "millimetre"}


def _height_data_is_absolute(measurement_units: Optional[Dict[str, Any]]) -> bool:
    """True when the loaded Height measurements are in absolute length units.

    The measurement loader is the ground truth for data units. When it declares
    Height in mm (e.g. the 振順豐 TOP profile), the stencil ``unit_mode`` must be
    treated as absolute even if a stale/mis-set spec still says percent —
    otherwise mm Height data is scored against a percent spec [50,170] and every
    capability index becomes meaningless (|Cpk| in the thousands).
    """
    height_unit = str((measurement_units or {}).get("Height", "")).strip().lower()
    return height_unit in _ABSOLUTE_HEIGHT_UNITS


def _effective_unit_mode(
    stencil_unit_mode: Any, measurement_units: Optional[Dict[str, Any]]
) -> str:
    """Resolve unit_mode, letting declared absolute Height data win over a
    percent flag (data units are authoritative; the flag can drift)."""
    mode = str(stencil_unit_mode or UNIT_MODE_PERCENT).strip().lower()
    if _height_data_is_absolute(measurement_units):
        return UNIT_MODE_ABSOLUTE
    return mode


def _coerce_precision_thickness_raw(master: Dict[str, Any]) -> Any:
    """Keep legacy precision-thickness fallback behavior."""
    raw = master.get("thickness_precision")
    if raw is not None:
        return raw
    try:
        return float(master.get("thickness_precision", 0.08))
    except (TypeError, ValueError):
        return 0.08


def _spec_to_strings(spec: Dict[str, float]) -> Dict[str, str]:
    return {
        "target": str(spec.get("target", "")),
        "lsl": str(spec.get("lsl", "")),
        "usl": str(spec.get("usl", "")),
    }


def _height_limits_in_measurement_domain(
    *,
    unit_mode: str,
    denominator_mm: float,
    lsl_percent: float,
    usl_percent: float,
) -> Dict[str, float]:
    """
    Height 規格轉到量測值域：
    - percent：直接使用 % 值
    - absolute：以分母將 % 界線換算為絕對值
    """
    normalized_mode = str(unit_mode or UNIT_MODE_PERCENT).strip().lower()
    if normalized_mode == UNIT_MODE_ABSOLUTE:
        if denominator_mm <= 0:
            raise ValueError(
                f"Height 絕對模式需要正值鋼板厚度（denominator_mm），收到 {denominator_mm!r}。"
            )
        d = float(denominator_mm)
        return {
            "target": d * DEFAULT_HEIGHT_TARGET / 100.0,
            "lsl": d * float(lsl_percent) / 100.0,
            "usl": d * float(usl_percent) / 100.0,
        }
    return {
        "target": DEFAULT_HEIGHT_TARGET,
        "lsl": float(lsl_percent),
        "usl": float(usl_percent),
    }


def _resolve_active_specs(
    product_name: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    key = str(product_name or "").strip()
    if not key:
        return None, None, "尚未選擇產品。"
    paste = get_paste_printing_spec(key)
    if not paste:
        return None, None, "該產品尚未建立錫膏印刷規格，請至資料設定頁建立。"
    stencil = get_stencil_thickness_spec(key)
    if not stencil:
        return None, None, "該產品尚未建立鋼板厚度規格，請至資料設定頁建立。"
    return paste, stencil, None


def resolve_workorder_spec(
    product_name: str,
    measurement_units: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    依產品名稱解析 workorder_spec（值為字串）。

    measurement_units: 量測載入器回報的單位（如 {"Height": "mm"}）。當 Height
        資料為絕對長度單位時，Height 規格一律以 absolute 模式換算，避免用過時
        的 percent 旗標把 mm 資料對百分比規格評分。
    """
    paste, stencil, err = _resolve_active_specs(product_name)
    if err:
        return None, err
    if paste is None or stencil is None:
        return None, "解析規格失敗：錫膏或鋼板設定為空。"
    key = str(product_name).strip()

    stencil_type = str(stencil.get("stencil_type") or STENCIL_NORMAL).strip().lower()
    thickness_main = float(stencil.get("thickness_main") or 0.12)
    unit_mode = _effective_unit_mode(stencil.get("unit_mode"), measurement_units)
    denominator_mm = float(stencil.get("height_denominator_mm") or thickness_main or 0.12)

    vol = _spec_to_strings(
        {
            "target": float(paste.get("default_volume_target", DEFAULT_VOLUME_TARGET)),
            "lsl": float(paste.get("default_volume_lsl", DEFAULT_VOLUME_LSL)),
            "usl": float(paste.get("default_volume_usl", DEFAULT_VOLUME_USL)),
        }
    )
    area = _spec_to_strings(
        {
            "target": float(paste.get("default_area_target", DEFAULT_AREA_TARGET)),
            "lsl": float(paste.get("default_area_lsl", DEFAULT_AREA_LSL)),
            "usl": float(paste.get("default_area_usl", DEFAULT_AREA_USL)),
        }
    )
    height = _spec_to_strings(
        _height_limits_in_measurement_domain(
            unit_mode=unit_mode,
            denominator_mm=denominator_mm,
            lsl_percent=float(paste.get("default_height_lsl", DEFAULT_HEIGHT_LSL)),
            usl_percent=float(paste.get("default_height_usl", DEFAULT_HEIGHT_USL)),
        )
    )

    if stencil_type == STENCIL_STEPPED and not has_any_precision_assignment(key):
        return None, "階梯鋼板尚未指定精密厚度套用元件，請在資料設定頁指定。"

    return {"volume": vol, "area": area, "height": height}, None


def resolve_height_spec_by_refdes(
    product_name: str,
    refdes_list: Optional[List[str]] = None,
    measurement_units: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, float]]:
    """
    依 RefDes 解析 Height 規格（給細粒度情境使用）。

    measurement_units: 同 :func:`resolve_workorder_spec`，Height 為絕對單位時強制
        以 absolute 模式換算。
    """
    result: Dict[str, Dict[str, float]] = {}
    paste, stencil, err = _resolve_active_specs(product_name)
    if err:
        return result
    if paste is None or stencil is None:
        return result

    stencil_type = str(stencil.get("stencil_type") or STENCIL_NORMAL).strip().lower()
    thickness_main = float(stencil.get("thickness_main") or 0.12)
    t_precision = _coerce_precision_thickness_raw(stencil)
    unit_mode = _effective_unit_mode(stencil.get("unit_mode"), measurement_units)
    denominator_mm = float(stencil.get("height_denominator_mm") or thickness_main or 0.12)
    lsl_percent = float(paste.get("default_height_lsl", DEFAULT_HEIGHT_LSL))
    usl_percent = float(paste.get("default_height_usl", DEFAULT_HEIGHT_USL))

    if not refdes_list:
        return result

    key = str(product_name).strip()
    for raw_refdes in refdes_list:
        refdes = str(raw_refdes or "").strip()
        if not refdes:
            continue

        # v1: product-level denominator. Keep hook for future per-refdes denominator.
        profile_thickness = thickness_main
        if stencil_type == STENCIL_STEPPED:
            profile = get_profile_by_refdes(key, refdes)
            if profile == PROFILE_PRECISION:
                try:
                    profile_thickness = float(t_precision)
                except (TypeError, ValueError):
                    profile_thickness = thickness_main

        denominator = denominator_mm if denominator_mm > 0 else profile_thickness
        result[refdes] = _height_limits_in_measurement_domain(
            unit_mode=unit_mode,
            denominator_mm=float(denominator),
            lsl_percent=lsl_percent,
            usl_percent=usl_percent,
        )
    return result


def can_run_analysis(product_name: str) -> Tuple[bool, str]:
    """
    分析前檢查：
    - 錫膏印刷規格存在
    - 鋼板厚度規格存在
    - 階梯鋼板時有精密 RefDes 指派
    """
    paste, stencil, err = _resolve_active_specs(product_name)
    if err:
        return False, err
    if stencil is None:
        return False, "解析規格失敗：鋼板設定為空。"
    key = str(product_name or "").strip()
    stencil_type = str(stencil.get("stencil_type") or STENCIL_NORMAL).strip().lower()
    if stencil_type == STENCIL_STEPPED and not has_any_precision_assignment(key):
        return False, "階梯鋼板尚未指定精密厚度套用元件，請在資料設定頁指定。"
    return True, ""
