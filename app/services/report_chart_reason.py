from __future__ import annotations

from typing import Any, Callable, Dict


_NO_CHART_FALLBACK: Dict[str, str] = {
    "boxplot": "元件分組不足（需 ≥ 2 個 RefDes 群組；單特徵且 RefDes 全部相同時無法繪製）",
    "boxplot_3f": "元件分組不足（需 ≥ 2 個 RefDes 群組）",
    "spatial_heatmap": "缺乏有效座標映射資料（請確認座標檔已匯入且關聯成功率 > 0%）",
}


def get_no_chart_reason(
    chart_id: str,
    payload: Dict[str, Any],
    *,
    catalog_by_id_fn: Callable[[], Dict[str, Dict[str, Any]]],
) -> str:
    """Resolve why a chart cannot be rendered from payload metadata or fallback text."""
    entry = catalog_by_id_fn().get(chart_id, {})
    payload_key = entry.get("payload_key")

    if isinstance(payload_key, str):
        sub = payload.get(payload_key) or {}
        err = sub.get("metadata", {}).get("error", "")
        if err:
            return str(err)
    elif isinstance(payload_key, (list, tuple)):
        for key in payload_key:
            sub = payload.get(key) or {}
            err = sub.get("metadata", {}).get("error", "")
            if err:
                return str(err)

    return _NO_CHART_FALLBACK.get(chart_id, "此條件下資料不足或格式不符，無法產出圖表")
