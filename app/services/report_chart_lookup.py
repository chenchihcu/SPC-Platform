from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.analytics.chart_registry import (
    CHART_CATALOG,
    CHART_SHORT_NAMES,
    get_chart_display_name,
)


def catalog_by_id() -> Dict[str, Dict[str, Any]]:
    return {str(entry.get("id", "")): entry for entry in CHART_CATALOG}


def get_pptx_chart_title(chart_id: str) -> str:
    """Return a concise chart title for PPTX slides."""
    if chart_id == "histogram_spec":
        return "分布與能力"
    if chart_id == "normality":
        return "常態分析"
    short_name = str(CHART_SHORT_NAMES.get(chart_id, "")).strip()
    if short_name:
        return short_name
    return get_chart_display_name(chart_id)


def normalize_chart_lookup_token(value: Any) -> str:
    """Normalize chart labels from hints/UI into a comparable token."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = (
        text.replace("（", "(")
        .replace("）", ")")
        .replace("＋", "+")
        .replace("－", "-")
        .replace("—", "-")
    )
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)


_CHART_NAME_ALIAS_MAP: Dict[str, str] = {
    normalize_chart_lookup_token("i-mr"): "imr",
    normalize_chart_lookup_token("個別值與移動極差圖"): "imr",
    normalize_chart_lookup_token("run chart"): "run_chart",
    normalize_chart_lookup_token("趨勢圖"): "run_chart",
    normalize_chart_lookup_token("xbar-r"): "xbar_r",
    normalize_chart_lookup_token("xbar r"): "xbar_r",
    normalize_chart_lookup_token("xbar-r 管制圖"): "xbar_r",
    normalize_chart_lookup_token("subgroup comparison"): "subgroup",
    normalize_chart_lookup_token("子群比較"): "subgroup",
    normalize_chart_lookup_token("repeated offender"): "repeated_offender",
    normalize_chart_lookup_token("重複異常點分析"): "repeated_offender",
    normalize_chart_lookup_token("histogram"): "histogram_spec",
    normalize_chart_lookup_token("capability"): "histogram_spec",
    normalize_chart_lookup_token("製程能力圖"): "histogram_spec",
    normalize_chart_lookup_token("分布能力"): "histogram_spec",
    normalize_chart_lookup_token("分布與能力"): "histogram_spec",
    normalize_chart_lookup_token("直方圖"): "histogram_spec",
    normalize_chart_lookup_token("boxplot"): "boxplot",
    normalize_chart_lookup_token("箱型圖"): "boxplot",
    normalize_chart_lookup_token("normality"): "normality",
    normalize_chart_lookup_token("常態機率圖"): "normality",
    normalize_chart_lookup_token("常態分析"): "normality",
    normalize_chart_lookup_token("spatial heatmap"): "spatial_heatmap",
    normalize_chart_lookup_token("空間熱圖"): "spatial_heatmap",
    normalize_chart_lookup_token("pareto"): "pareto",
    normalize_chart_lookup_token("柏拉圖"): "pareto",
    normalize_chart_lookup_token("ewma"): "ewma",
    normalize_chart_lookup_token("ewma圖"): "ewma",
    normalize_chart_lookup_token("cusum"): "cusum",
    normalize_chart_lookup_token("cusum圖"): "cusum",
    normalize_chart_lookup_token("scatter"): "scatter_spec",
    normalize_chart_lookup_token("scatter+spec"): "scatter_spec",
    normalize_chart_lookup_token("散佈圖"): "scatter_spec",
    normalize_chart_lookup_token("散點與規格區"): "scatter_spec",
    normalize_chart_lookup_token("correlation matrix"): "correlation_matrix",
    normalize_chart_lookup_token("關聯矩陣"): "correlation_matrix",
    normalize_chart_lookup_token("correlation heatmap"): "correlation_heatmap",
    normalize_chart_lookup_token("關聯熱圖"): "correlation_heatmap",
    normalize_chart_lookup_token("anova"): "anova_parttype",
    normalize_chart_lookup_token("anova(parttype)"): "anova_parttype",
    normalize_chart_lookup_token("ooc analysis"): "ooc_analysis",
    normalize_chart_lookup_token("失控分析"): "ooc_analysis",
    normalize_chart_lookup_token("shift detection"): "shift_detection",
    normalize_chart_lookup_token("偏移偵測"): "shift_detection",
    normalize_chart_lookup_token("drift detection"): "drift_detection",
    normalize_chart_lookup_token("漂移偵測"): "drift_detection",
    normalize_chart_lookup_token("outlier analysis"): "outlier_analysis",
    normalize_chart_lookup_token("離群分析"): "outlier_analysis",
    normalize_chart_lookup_token("pattern recognition"): "pattern_recognition",
    normalize_chart_lookup_token("規則辨識"): "pattern_recognition",
    normalize_chart_lookup_token("quadrant"): "quadrant",
    normalize_chart_lookup_token("四象限"): "quadrant",
    normalize_chart_lookup_token("bivariate outlier"): "bivariate_outlier",
    normalize_chart_lookup_token("雙變量離群"): "bivariate_outlier",
    normalize_chart_lookup_token("density"): "density",
    normalize_chart_lookup_token("密度圖"): "density",
    normalize_chart_lookup_token("anomaly 3f"): "anomaly_3f",
    normalize_chart_lookup_token("三特徵異常分數"): "anomaly_3f",
    normalize_chart_lookup_token("consistency 3f"): "consistency_3f",
    normalize_chart_lookup_token("多特徵一致性"): "consistency_3f",
    normalize_chart_lookup_token("parallel coordinates"): "parallel_coord",
    normalize_chart_lookup_token("平行座標"): "parallel_coord",
    normalize_chart_lookup_token("pass/fail summary"): "pass_fail_matrix",
    normalize_chart_lookup_token("過關失敗摘要"): "pass_fail_matrix",
}


def display_name_to_chart_id(chart_name: str) -> Optional[str]:
    """Resolve hint chart labels such as 'CUSUM 圖' or '製程能力圖 (Capability)' to chart ids."""
    token = normalize_chart_lookup_token(chart_name)
    if not token:
        return None
    by_id = catalog_by_id()
    if token in by_id:
        return token
    for alias_token, chart_id in _CHART_NAME_ALIAS_MAP.items():
        if token == alias_token or token in alias_token or alias_token in token:
            return chart_id
    for entry in CHART_CATALOG:
        for candidate in (
            entry.get("id", ""),
            entry.get("name", ""),
            entry.get("display_name_zh", ""),
            entry.get("display_name_en", ""),
        ):
            candidate_token = normalize_chart_lookup_token(candidate)
            if not candidate_token:
                continue
            if token == candidate_token or token in candidate_token or candidate_token in token:
                entry_id = str(entry.get("id", "")).strip()
                return entry_id or None
    return None


def normalize_pptx_observable_charts(chart_names: Any) -> List[str]:
    """Normalize observable chart labels into concise, deduplicated PPTX titles."""
    if not isinstance(chart_names, list):
        return []
    normalized_titles: List[str] = []
    seen: set[str] = set()
    for item in chart_names:
        raw_name = str(item).strip()
        if not raw_name:
            continue
        chart_id = display_name_to_chart_id(raw_name)
        title = get_pptx_chart_title(chart_id) if chart_id else raw_name
        if title in seen:
            continue
        normalized_titles.append(title)
        seen.add(title)
    return normalized_titles
