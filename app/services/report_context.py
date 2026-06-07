from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.data.session_store import SessionStore
from app.services import report_risk
from app.utils.constants import FEATURE_COLUMNS
from app.analytics.chart_registry import (
    CHART_CATALOG,
    CHART_ORDER,
    get_chart_display_name,
    get_incompatible_reason,
    get_incompatible_short_reason,
    is_chart_available_for_selection,
)

logger = logging.getLogger(__name__)


def _infer_single_value(df: pd.DataFrame, columns: List[str]) -> Optional[str]:
    for col in columns:
        if col not in df.columns:
            continue
        series = df[col].dropna().astype(str).str.strip()
        series = series[series != ""]
        if series.empty:
            continue
        uniq = list(series.unique())
        if len(uniq) == 1:
            return str(uniq[0])
    return None


def _infer_time_range(df: pd.DataFrame, columns: List[str]) -> Tuple[Optional[str], Optional[str]]:
    for col in columns:
        if col not in df.columns:
            continue
        series = df[col].dropna().astype(str).str.strip()
        series = series[series != ""]
        if series.empty:
            continue
        return str(series.min()), str(series.max())
    return None, None


def _has_valid_coordinate_data(df: pd.DataFrame) -> bool:
    if df is None or df.empty or "X" not in df.columns or "Y" not in df.columns:
        return False
    try:
        xy = df[["X", "Y"]].dropna()
    except (KeyError, TypeError, ValueError):
        return False
    return not xy.empty


def _chart_required_feature_count(chart_id: str) -> int:
    for entry in CHART_CATALOG:
        if str(entry.get("id", "")).strip() != chart_id:
            continue
        raw_count = entry.get("required_feature_count", 1)
        if isinstance(raw_count, bool):
            return 1
        if isinstance(raw_count, (int, float)):
            return int(raw_count)
        if isinstance(raw_count, str):
            try:
                return int(raw_count)
            except ValueError:
                return 1
    return 1


def _resolve_chart_features_for_coverage(
    chart_id: str,
    *,
    selected_features: List[str],
    available_features: List[str],
) -> List[str]:
    ordered: List[str] = []
    for feature in [*selected_features, *available_features]:
        normalized = str(feature or "").strip()
        if not normalized or normalized in ordered:
            continue
        ordered.append(normalized)
    required = _chart_required_feature_count(chart_id)
    if required <= 1:
        return ordered[:1]
    return ordered[:required]


def build_data_scope(
    *,
    filtered_df: pd.DataFrame,
    selected_features: List[str],
    batch: str,
    refdes_filter: str,
    part_type: str,
    product: Optional[str],
    time_start: Optional[str],
    time_end: Optional[str],
    line: Optional[str],
) -> Dict[str, Any]:
    """Return report-source scope and excluded evidence for PPTX trust disclosure."""
    has_measurement_data = filtered_df is not None and not filtered_df.empty
    has_coordinate_data = _has_valid_coordinate_data(filtered_df)
    sample_n = int(len(filtered_df)) if has_measurement_data else 0
    used_sources = ["量測資料", "管制規格", "工單資訊"]
    excluded_evidence: List[Dict[str, str]] = []
    if has_coordinate_data:
        used_sources.append("座標值/空間映射")
    else:
        excluded_evidence.append(
            {
                "id": "spatial",
                "label": "座標值 / 空間映射 / 空間熱圖",
                "reason": "本批資料未提供有效 X/Y 座標欄位",
            }
        )
    filters = {
        "batch": batch,
        "refdes": refdes_filter,
        "part_type": part_type,
        "product": product,
        "time_start": time_start,
        "time_end": time_end,
        "line": line,
    }
    return {
        "has_measurement_data": has_measurement_data,
        "has_coordinate_data": has_coordinate_data,
        "sample_n": sample_n,
        "selected_features": [str(f) for f in selected_features if str(f).strip()],
        "available_features": [col for col in FEATURE_COLUMNS if col in filtered_df.columns],
        "used_sources": used_sources,
        "excluded_evidence": excluded_evidence,
        "filters": filters,
        "section_trust": {
            "statistics": "可信：資料直接計算",
            "charts": "可信：圖表證據",
            "inference": "需複核：規則推論",
            "spatial": "可信：資料直接計算" if has_coordinate_data else "未納入：資料缺失",
        },
    }


def build_chart_evidence_coverage(
    *,
    selected_chart_ids: List[str],
    selected_features: List[str],
    available_features: List[str],
    has_coordinate_data: bool,
) -> Dict[str, Any]:
    """Build a report-wide chart evidence coverage table before rendering."""
    selected_set = {str(cid).strip() for cid in selected_chart_ids if str(cid).strip()}
    items: List[Dict[str, Any]] = []
    for chart_id in CHART_ORDER:
        features = _resolve_chart_features_for_coverage(
            chart_id,
            selected_features=selected_features,
            available_features=available_features,
        )
        selected = chart_id in selected_set
        available = is_chart_available_for_selection(chart_id, selected_features)
        reason = ""
        status = "待輸出" if selected and available else "本次排除"
        if chart_id == "spatial_heatmap" and not has_coordinate_data:
            available = False
            status = "未納入"
            reason = "缺座標資料"
        elif not available:
            status = "不相容"
            reason = (
                get_incompatible_short_reason(chart_id, selected_features)
                or get_incompatible_reason(chart_id, selected_features)
                or "特徵條件不符"
            )
        elif not selected:
            reason = "未勾選匯出"

        items.append(
            {
                "chart_id": chart_id,
                "chart_name": get_chart_display_name(chart_id, lang="zh_only"),
                "selected": selected,
                "available": available,
                "features": features,
                "status": status,
                "reason": reason,
            }
        )

    available_count = sum(1 for item in items if item["available"])
    incompatible_count = sum(1 for item in items if item["status"] == "不相容")
    excluded_count = sum(1 for item in items if item["status"] == "未納入")
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "selected": sum(1 for item in items if item["selected"]),
            "available": available_count,
            "incompatible": incompatible_count,
            "excluded": excluded_count,
        },
    }


def build_pptx_report_context(
    *,
    store: SessionStore,
    filtered_df: pd.DataFrame,
    summary_data: Dict[str, Any],
    diagnostics: List[Dict[str, Any]],
    selected_features: List[str],
    batch: str,
    refdes_filter: str,
    part_type: str,
    product: Optional[str],
    time_start: Optional[str],
    time_end: Optional[str],
    line: Optional[str],
    analysis_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build PPTX context payload used by deck section rendering."""
    process_data = summary_data.get("process", {}) if isinstance(summary_data, dict) else {}
    risk_assessment = report_risk.build_risk_assessment(
        process=process_data if isinstance(process_data, dict) else {},
        diagnostics=diagnostics,
    )
    inferred_time_start, inferred_time_end = _infer_time_range(
        filtered_df,
        ["Time", "Timestamp", "timestamp", "DateTime"],
    )

    wo_master = getattr(store, "workorder_master", None) or {}
    report_context: Dict[str, Any] = {
        "relation_meta": getattr(store, "relation_meta", {}) or {},
        "workorder_context": {
            "product_name": str(wo_master.get("product_name") or "").strip(),
            "work_order_no": str(wo_master.get("work_order_no") or "").strip(),
            "supplier_work_order_no": str(wo_master.get("supplier_work_order_no") or "").strip(),
            "outsource_work_order_no": str(wo_master.get("outsource_work_order_no") or "").strip(),
            "product_part_no": str(wo_master.get("product_part_no") or "").strip(),
            "supplier": str(wo_master.get("supplier") or "").strip(),
            "batch_no": str(wo_master.get("batch_no") or "").strip(),
            "batch_qty": str(wo_master.get("batch_qty") or "").strip(),
            "line_name": str(wo_master.get("line_name") or "").strip(),
            "production_date": str(wo_master.get("production_date") or "").strip(),
        },
        "filter_context": {
            "batch": batch,
            "refdes": refdes_filter,
            "part_type": part_type,
            "product": product,
            "time_start": time_start,
            "time_end": time_end,
            "line": line,
        },
        "selected_features": selected_features,
        "available_features": [col for col in FEATURE_COLUMNS if col in filtered_df.columns],
        "data_scope": build_data_scope(
            filtered_df=filtered_df,
            selected_features=selected_features,
            batch=batch,
            refdes_filter=refdes_filter,
            part_type=part_type,
            product=product,
            time_start=time_start,
            time_end=time_end,
            line=line,
        ),
        "metric_definitions": {
            "primary_ooc_ratio": "主特徵管制圖失控比例",
            "overall_event_ooc": "整體事件層級異常比例",
            "risk_level": "由製程摘要與診斷嚴重度共同判定",
        },
        "risk_assessment": risk_assessment,
        "inferred_context": {
            "line_name": _infer_single_value(filtered_df, ["Line", "line_id", "LineId", "LineName"]),
            "product_name": _infer_single_value(
                filtered_df,
                ["Product", "product_id", "ProductId", "ProductName"],
            ),
            "time_start": inferred_time_start,
            "time_end": inferred_time_end,
        },
    }

    product_name = str((getattr(store, "workorder_master", {}) or {}).get("product_name", "")).strip()
    if product_name:
        try:
            from app.data.product_spec_registry import get as get_product_spec

            profile = get_product_spec(product_name)
            if isinstance(profile, dict):
                report_context["product_spec_profile"] = profile
        except ImportError:
            logger.debug("PPTX: product_spec_registry unavailable", exc_info=True)

        try:
            from app.data.coordinate_registry import list_registered

            entries = [
                entry
                for entry in list_registered()
                if str(entry.get("product_name", "")).strip() == product_name
            ]
            if entries:
                report_context["coordinate_registry_entry"] = entries[-1]
        except ImportError:
            logger.debug("PPTX: coordinate_registry unavailable", exc_info=True)

    height_spec_by_refdes = getattr(store, "height_spec_by_refdes", None)
    if isinstance(height_spec_by_refdes, dict) and height_spec_by_refdes:
        distinct_height_targets = {
            str((spec or {}).get("target"))
            for spec in height_spec_by_refdes.values()
            if isinstance(spec, dict)
        }
        report_context["height_spec_stats"] = {
            "assigned_refdes": len(height_spec_by_refdes),
            "distinct_height_targets": len([t for t in distinct_height_targets if t and t != "None"]),
        }

    ap = analysis_payload if isinstance(analysis_payload, dict) else {}
    if ap.get("summary") and isinstance(ap["summary"], dict):
        from app.services.diagnostic_evidence_matrix import build_diagnostic_evidence_matrix
        from app.services.report_process_narrative import (
            build_decision_narrative,
            build_process_diagnosis_report_payload,
        )

        matrix = build_diagnostic_evidence_matrix(
            ap,
            filter_context=report_context["filter_context"],
        )
        if matrix:
            report_context["diagnostic_evidence_matrix"] = matrix
            ap["diagnostic_evidence_matrix"] = matrix
        report_context["decision_narrative"] = build_decision_narrative(ap)
        pdr = build_process_diagnosis_report_payload(ap)
        if pdr:
            report_context["process_diagnosis_report"] = pdr

    return report_context
