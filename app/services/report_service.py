import base64
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from app.data.session_store import SessionStore
from app.ui.theme.tokens import (
    RPT_DARK_BG, RPT_DARK_BG_CODE, RPT_DARK_TEXT, RPT_DARK_BORDER,
    RPT_FOOTER_TEXT, RPT_ERROR_TEXT,
    RPT_FONT_LABEL_PX, RPT_FONT_FOOTER_PX,
)
from app.utils.constants import FEATURE_COLUMNS, FEATURE_DISPLAY_NAMES
from app.utils.numeric_utils import coerce_float, coerce_int
from app.services import report_risk
from app.services import report_diagnostics
from app.services import report_context
from app.services import report_chart_lookup
from app.services import report_actions
from app.services import report_formatters
from app.services import report_chart_reason
from app.services import report_exec_summary
from app.analytics.chart_registry import (
    get_chart_display_name,
)

TEMPLATE_ENGINEERING = "engineering"
ENGINEERING_DEFAULT_CHART_IDS: List[str] = [
    "imr",
    "xbar_r",
    "run_chart",
    "ewma",
    "cusum",
    "histogram_spec",
    "boxplot",
    "normality",
    "ooc_analysis",
    "shift_detection",
    "drift_detection",
    "pattern_recognition",
    "pareto",
    "repeated_offender",
    "spatial_heatmap",
    "correlation_heatmap",
]
TEMPLATE_DEFAULT_CHARTS = {
    TEMPLATE_ENGINEERING: ENGINEERING_DEFAULT_CHART_IDS,
}


def _catalog_by_id():
    return report_chart_lookup.catalog_by_id()


def _get_pptx_chart_title(chart_id: str) -> str:
    return report_chart_lookup.get_pptx_chart_title(chart_id)


def _normalize_pptx_observable_charts(chart_names: Any) -> List[str]:
    return report_chart_lookup.normalize_pptx_observable_charts(chart_names)


def _pptx_severity_rank(severity: Any) -> int:
    """Sort diagnostics so PPTX opens with the highest-risk findings first."""
    level = str(severity or "info").strip().lower()
    if level == "error":
        return 0
    if level == "warning":
        return 1
    return 2


def _normalize_pptx_severity(value: Any, *, priority: Any = None) -> str:
    return report_risk.normalize_pptx_severity(value, priority=priority)


def _display_name_to_chart_id(chart_name: str) -> Optional[str]:
    return report_chart_lookup.display_name_to_chart_id(chart_name)


def _format_pptx_evidence_lines(evidence: Dict[str, Any], limit: int = 4) -> List[str]:
    return report_formatters.format_pptx_evidence_lines(evidence, limit=limit)


def _format_pptx_ipc_lines(ipc_refs: Any, limit: int = 2) -> List[str]:
    return report_formatters.format_pptx_ipc_lines(ipc_refs, limit=limit)


def _collect_pptx_actions(payload: Dict[str, Any], *, rule_id: Optional[str] = None, limit: int = 3) -> List[str]:
    return report_actions.collect_pptx_actions(payload, rule_id=rule_id, limit=limit)


def _build_pptx_diagnostics(
    payload: Dict[str, Any],
    selected_features: List[str],
    *,
    include_chart_render: bool = True,
    render_chart_fn: Optional[Callable[..., Optional[bytes]]] = None,
) -> List[Dict[str, Any]]:
    return report_diagnostics.build_pptx_diagnostics(
        payload,
        selected_features,
        include_chart_render=include_chart_render,
        feature_display_names=FEATURE_DISPLAY_NAMES,
        normalize_pptx_severity_fn=_normalize_pptx_severity,
        collect_actions_fn=_collect_pptx_actions,
        normalize_observable_charts_fn=_normalize_pptx_observable_charts,
        display_name_to_chart_id_fn=_display_name_to_chart_id,
        get_pptx_chart_title_fn=_get_pptx_chart_title,
        format_evidence_lines_fn=_format_pptx_evidence_lines,
        format_ipc_lines_fn=_format_pptx_ipc_lines,
        get_no_chart_reason_fn=_get_no_chart_reason,
        logger=logger,
        render_chart_fn=render_chart_fn,
    )


def _filter_diagnostics_by_selected_charts(
    diagnostics: List[Dict[str, Any]],
    selected_chart_ids: List[str],
) -> List[Dict[str, Any]]:
    if not selected_chart_ids:
        return diagnostics
    allowed = set(selected_chart_ids)
    filtered: List[Dict[str, Any]] = []
    for item in diagnostics:
        diag = dict(item)
        chart_title = str(diag.get("chart_title", "")).strip()
        chart_id = _display_name_to_chart_id(chart_title) if chart_title else None
        if chart_id is None:
            observable = diag.get("observable_charts") or []
            if isinstance(observable, list):
                for name in observable:
                    chart_id = _display_name_to_chart_id(name)
                    if chart_id:
                        break
        if chart_id and chart_id not in allowed:
            existing_reason = str(diag.get("chart_missing_reason", "")).strip()
            diag["chart_bytes"] = None
            if existing_reason:
                diag["chart_missing_reason"] = f"{existing_reason}；未納入本次匯出勾選的圖表。"
            else:
                diag["chart_missing_reason"] = "未納入本次匯出勾選的圖表。"
            diag["chart_title"] = _get_pptx_chart_title(chart_id)
        filtered.append(diag)
    return filtered


def _payload_matches_report_context(
    payload: Any,
    *,
    selected_features: List[str],
    batch: str,
    refdes: str,
    part_type: str,
) -> bool:
    if not isinstance(payload, dict):
        return False
    if list(payload.get("selected_features") or []) != list(selected_features):
        return False
    return (
        str(payload.get("_ctx_batch", "")) == str(batch)
        and str(payload.get("_ctx_refdes", "")) == str(refdes)
        and str(payload.get("_ctx_part_type", "")) == str(part_type)
    )


def _make_cached_chart_renderer(
    stats: Dict[str, int],
) -> Callable[..., Optional[bytes]]:
    from app.services.chart_render import render_chart_to_png_bytes

    cache: Dict[Tuple[str, Tuple[str, ...], bool, str], Optional[bytes]] = {}

    def _render(
        chart_id: str,
        payload: Dict[str, Any],
        *,
        features: Optional[List[str]] = None,
        normalized: bool = False,
        context: str = "report",
    ) -> Optional[bytes]:
        key = (chart_id, tuple(features or []), bool(normalized), context)
        stats["requests"] = stats.get("requests", 0) + 1
        if key in cache:
            stats["hits"] = stats.get("hits", 0) + 1
            return cache[key]
        stats["misses"] = stats.get("misses", 0) + 1
        rendered = render_chart_to_png_bytes(
            chart_id,
            payload,
            features=features,
            normalized=normalized,
            context=context,
        )
        cache[key] = rendered
        return rendered

    return _render


def _coerce_float(value: Any, default: float = 0.0) -> float:
    return coerce_float(value, default)


def _coerce_int(value: Any, default: int = 0) -> int:
    return coerce_int(value, default)


# ── Risk level ──────────────────────────────────────────────────────────────
def _risk_level_display(level: str) -> str:
    return report_risk.risk_level_display(level)


def _compute_risk_level(
    hints: List[Dict[str, Any]],
    *,
    process: Optional[Dict[str, Any]] = None,
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return report_risk.compute_risk_level(
        hints,
        process=process,
        diagnostics=diagnostics,
    )


def _build_risk_assessment(
    *,
    process: Optional[Dict[str, Any]] = None,
    hints: Optional[List[Dict[str, Any]]] = None,
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return report_risk.build_risk_assessment(
        process=process,
        hints=hints,
        diagnostics=diagnostics,
    )


def _get_no_chart_reason(chart_id: str, payload: Dict[str, Any]) -> str:
    return report_chart_reason.get_no_chart_reason(
        chart_id,
        payload,
        catalog_by_id_fn=_catalog_by_id,
    )


# ── Executive Summary ────────────────────────────────────────────────────────
def _build_executive_summary_html(
    hints: List[Dict[str, Any]],
    ro_payload: Dict[str, Any],
    summary_data: Dict[str, Any],
    total_n: int,
    batch_qty: Any,
    *,
    batch_no: Any = None,
    supplier_work_order_no: Any = None,
    outsource_work_order_no: Any = None,
    primary_feature: Optional[str] = None,
    diagnostics: Optional[List[Dict[str, Any]]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
    decision_narrative: Optional[Dict[str, str]] = None,
) -> str:
    return report_exec_summary.build_executive_summary_html(
        hints,
        ro_payload,
        summary_data,
        total_n,
        batch_qty,
        batch_no=batch_no,
        supplier_work_order_no=supplier_work_order_no,
        outsource_work_order_no=outsource_work_order_no,
        compute_risk_level_fn=_compute_risk_level,
        primary_feature=primary_feature,
        diagnostics=diagnostics,
        risk_assessment=risk_assessment,
        decision_narrative=decision_narrative,
    )


# ── Component Focus cross-table ──────────────────────────────────────────────
def _build_component_focus_html(
    ro_by_feature: Dict[str, Dict[str, Any]],
    top_n: int = 5,
) -> str:
    """
    Build a cross-feature table: TOP N worst RefDes × (Volume, Area, Height) violation counts.
    ro_by_feature: { feature_col -> repeated_offender_payload }
    """
    if not ro_by_feature:
        return ""

    # Collect union of top offenders from all features
    all_counts: Dict[str, Dict[str, int]] = {}
    for feat, ro in ro_by_feature.items():
        if not (ro or {}).get("metadata", {}).get("is_valid"):
            continue
        labels = ro.get("data", {}).get("labels", [])
        counts = ro.get("data", {}).get("counts", [])
        for lbl, cnt in zip(labels, counts):
            all_counts.setdefault(lbl, {})
            all_counts[lbl][feat] = _coerce_int(cnt, 0)

    if not all_counts:
        return ""

    # Sort by total violations across all features
    ranked = sorted(all_counts.items(), key=lambda kv: sum(kv[1].values()), reverse=True)[:top_n]
    features_in_table = list(ro_by_feature.keys())
    display_names = {f: FEATURE_DISPLAY_NAMES.get(f, f) for f in features_in_table}

    parts = [
        "<h2 id='component-focus'>[3.5] 元件聚焦分析（TOP5 跨特徵異常矩陣）</h2>",
        "<p style='font-size:13px;color:#5B6770;'>下表彙整各特徵中違規次數最高的元件，橘底代表中高異常、紅底代表嚴重異常。</p>",
        "<table class='focus-table'>",
        "<tr><th>排名</th><th>元件 (RefDes)</th>",
    ]
    for f in features_in_table:
        parts.append(f"<th class='feature-{f.lower()}'>{display_names[f]} 違規數</th>")
    parts.append("<th>合計</th></tr>")

    for rank, (lbl, feat_counts) in enumerate(ranked, 1):
        total = sum(feat_counts.values())
        parts.append(f"<tr><td style='text-align:center;'>#{rank}</td><td><strong>{lbl}</strong></td>")
        for f in features_in_table:
            cnt = feat_counts.get(f, 0)
            if cnt >= 10:
                cls = "violation-high"
            elif cnt > 0:
                cls = "violation-med"
            else:
                cls = "no-violation"
            cell_text = str(cnt) if cnt > 0 else "—"
            parts.append(f"<td class='{cls}' style='text-align:center;'>{cell_text}</td>")
        parts.append(f"<td style='text-align:center;font-weight:bold;'>{total}</td></tr>")

    parts.append("</table>")
    return "\n".join(parts)


def _format_ipc_refs_html(ipc_refs: list) -> str:
    return report_formatters.format_ipc_refs_html(ipc_refs)


def _format_evidence_html(evidence: dict) -> str:
    return report_formatters.format_evidence_html(evidence)


def _build_report_html(
    store: SessionStore,
    chart_ids_to_export: List[str],
    selected_features: Optional[List[str]] = None,
) -> str:
    """Build HTML report body with summary and embedded chart images."""
    m_meta = store.meas_meta
    c_meta = store.coord_meta
    r_meta = store.relation_meta
    payload = getattr(store, "last_analysis_payload", None) or {}
    selected = selected_features if selected_features is not None else (getattr(store, "selected_features", None) or [])
    feat_line = ", ".join(FEATURE_DISPLAY_NAMES.get(f, f) for f in selected) if selected else "—"
    wo_master = getattr(store, "workorder_master", {}) or {}
    wo_spec = getattr(store, "workorder_spec", {}) or {}
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    process_data = summary.get("process", {}) if isinstance(summary, dict) else {}
    risk_features = [
        str(feature).strip()
        for feature in (selected or payload.get("selected_features") or [])
        if str(feature).strip()
    ]
    risk_diagnostics = _build_pptx_diagnostics(payload, risk_features, include_chart_render=False)
    risk_assessment = _build_risk_assessment(
        process=process_data if isinstance(process_data, dict) else {},
        diagnostics=risk_diagnostics,
    )
    risk_level_text = str(risk_assessment.get("level_display", "") or _risk_level_display("LOW"))
    process_verdict = (
        str((process_data or {}).get("verdict", "—") or "—")
        if isinstance(process_data, dict)
        else "—"
    )

    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'/><title>SMT SPI/SPC Engineering Report</title>",
        f"<style>body{{font-family:sans-serif;margin:20px;background:{RPT_DARK_BG};color:{RPT_DARK_TEXT};}}",
        f"h1,h2{{color:{RPT_DARK_TEXT};}} pre{{background:{RPT_DARK_BG_CODE};padding:12px;border-radius:4px;}}",
        f"img{{max-width:100%;height:auto;margin:16px 0;border:1px solid {RPT_DARK_BORDER};}}</style></head><body>",
        "<h1>SMT SPI/SPC Engineering Report</h1>",
        f"<p>產生時間 (Date): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        "<h2>[0] 風險摘要 (Shared Decision)</h2>",
        "<ul>",
        f"<li>Risk Level: {risk_level_text}</li>",
        f"<li>Process Verdict: {process_verdict}</li>",
        (
            "<li>Risk Signals: "
            f"Error={risk_assessment.get('error_count', 0)}, "
            f"Warning={risk_assessment.get('warning_count', 0)}, "
            f"HighPriority={risk_assessment.get('high_priority_count', 0)}, "
            f"Total={risk_assessment.get('total_count', 0)}</li>"
        ),
        "</ul>",
        "<h2>[1] 資料層級診斷</h2>",
        f"<ul><li>量測資料: {'Valid' if m_meta.get('is_valid') else 'Invalid'}</li>",
        f"<li>座標資料: {'Valid' if c_meta.get('is_valid') else 'Invalid'}</li>",
        f"<li>空間映射成功率: {_coerce_float(r_meta.get('match_rate', 0.0), 0.0):.1f}%</li></ul>",
        "<h2>[2] 統計環境前提</h2>",
        f"<p>分析特徵 (Selected Features): {feat_line}</p>",
    ]
    if wo_master:
        parts.append("<h3>工單主檔</h3><ul>")
        parts.append(f"<li>供應商製令工單: {wo_master.get('supplier_work_order_no', '--') or '--'}</li>")
        parts.append(
            f"<li>醫電製令工單: "
            f"{wo_master.get('outsource_work_order_no', '--') or wo_master.get('work_order_no', '--') or '--'}</li>"
        )
        parts.append(f"<li>產品名稱: {wo_master.get('product_name', '--')}</li>")
        parts.append(f"<li>產品料號: {wo_master.get('product_part_no', '--')}</li>")
        parts.append(f"<li>供應商: {wo_master.get('supplier', '--')}</li>")
        parts.append(f"<li>批量: {wo_master.get('batch_qty', '--')}</li>")
        parts.append(f"<li>線別: {wo_master.get('line_name', '--') or '--'}</li>")
        parts.append(f"<li>生產日期: {wo_master.get('production_date', '--') or '--'}</li></ul>")
    if wo_spec:
        parts.append("<h3>管制規格</h3><ul>")
        for key, label in [("volume", "體積"), ("area", "面積"), ("height", "高度")]:
            s = wo_spec.get(key, {})
            if s:
                parts.append(f"<li>{label}: USL={s.get('usl','--')} LSL={s.get('lsl','--')} Target={s.get('target','--')}</li>")
        parts.append("</ul>")
    # Process overview & top abnormal (from payload)
    if summary:
        parts.append("<h2>[2.5] 製程概覽 (Process Overview)</h2><ul>")
        for k, v in list(summary.items())[:10]:
            parts.append(f"<li>{k}: {v}</li>")
        parts.append("</ul>")
    pareto_data = (payload.get("pareto") or {}).get("components", [])
    if pareto_data:
        parts.append("<h2>[2.6] 異常率較高元件 (Top Abnormal Components)</h2><ul>")
        for comp in pareto_data[:15]:
            cid = comp.get("component_id", "")
            rate = _coerce_float(comp.get("abnormal_rate", 0.0), 0.0)
            total = comp.get("total", 0)
            parts.append(f"<li>{cid}: abnormal_rate={rate:.2%}, n={total}</li>")
        parts.append("</ul>")
    try:
        from app.analytics.root_cause_engine import infer_root_cause_hints
        hints = infer_root_cause_hints(payload)
        if hints:
            parts.append("<h2>[2.7] 根因提示 (Root Cause Hints)</h2><ul>")
            for h in hints:
                parts.append(f"<li>{h.get('hint', '')}")
                ev_html = _format_evidence_html(h.get("evidence", {}))
                ipc_html = _format_ipc_refs_html(h.get("ipc_refs", []))
                if ev_html:
                    parts.append(ev_html)
                if ipc_html:
                    parts.append("<div><small>IPC 註解:</small></div>")
                    parts.append(ipc_html)
                parts.append("</li>")
            parts.append("</ul>")
    except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
        logger.exception("產生根因提示失敗: %s", e)
        parts.append(f"<p style='color:{RPT_ERROR_TEXT};font-size:{RPT_FONT_LABEL_PX}px;'>※ 根因提示模組執行失敗，請檢查系統設定或聯絡維護人員。</p>")
    try:
        from app.analytics.anomaly_classifier import classify_anomalies
        from app.analytics.failure_mode_library import get_failure_mode
        anomalies = classify_anomalies(payload)
        if anomalies:
            parts.append("<h2>[2.8] 建議措施 (Recommended Actions)</h2><ul>")
            seen = set()
            for a in anomalies:
                fid = a.get("suggested_failure_mode_id")
                if fid and fid not in seen:
                    seen.add(fid)
                    fm = get_failure_mode(fid)
                    if fm:
                        for act in fm.get("recommended_actions", [])[:3]:
                            parts.append(f"<li>{act}</li>")
                        from app.analytics.ipc_reference_library import get_ipc_references_by_failure_mode
                        ipc_refs = get_ipc_references_by_failure_mode(fid)
                        ipc_html = _format_ipc_refs_html(ipc_refs)
                        if ipc_html:
                            parts.append(f"<li><small>{fid} IPC 註解:</small>{ipc_html}</li>")
            parts.append("</ul>")
    except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
        logger.exception("產生建議措施失敗: %s", e)
        parts.append(f"<p style='color:{RPT_ERROR_TEXT};font-size:{RPT_FONT_LABEL_PX}px;'>※ 建議措施模組執行失敗，可能無法顯示改善建議。</p>")
    parts.append("<h2>[3] 圖表</h2>")
    from app.services.chart_render import render_chart_to_png_bytes
    for chart_id in chart_ids_to_export:
        name = get_chart_display_name(chart_id)
        img_bytes = render_chart_to_png_bytes(
            chart_id,
            payload,
            features=selected,
            context="report",
        )
        if img_bytes:
            b64 = base64.b64encode(img_bytes).decode("ascii")
            parts.append(f"<h3>{name}</h3><img src='data:image/png;base64,{b64}' alt='{name}'/>")
        else:
            parts.append(f"<h3>{name}</h3><p>（無資料或圖表無法產出）</p>")
    parts.append(f"<hr/><p style='font-size:{RPT_FONT_FOOTER_PX}px;color:{RPT_FOOTER_TEXT};'>IPC 引用僅提供工程摘要與條文代碼，非標準全文。</p>")
    parts.append("</body></html>")
    return "\n".join(parts)


def _get_spec_for_feature(workorder_spec: dict, col: str) -> Tuple[float, float, float]:
    """Extract USL/LSL/Target for a single feature column from workorder spec."""
    key_map = {"Volume": "volume", "Area": "area", "Height": "height"}
    entry = workorder_spec.get(key_map.get(col, col.lower()), {}) or {}
    try:
        usl = float(entry.get("usl", 120.0) or 120.0)
        lsl = float(entry.get("lsl", 80.0) or 80.0)
        target = float(entry.get("target", 100.0) or 100.0)
    except (TypeError, ValueError):
        usl, lsl, target = 120.0, 80.0, 100.0
    return usl, lsl, target


class ReportService:
    def generate_pptx_report(
        self,
        output_path: str,
        template_type: str = TEMPLATE_ENGINEERING,
        chart_ids_to_export: Optional[List[str]] = None,
        progress_callback: Optional[Any] = None, # (progress_int, msg_str)
    ) -> Tuple[bool, Optional[str]]:
        """
        Generate PPTX (PowerPoint) only — engineering template is the sole supported mode.

        Core 12-section structure plus optional chart evidence gallery pages when selected charts are renderable:
          1) Product & Work Order Information
          2) Control Specification
          3) Statistics Summary
          4) Process Capability Analysis
          5) SPC Control Charts
          6) Distribution Analysis
          7) Spatial Analysis (PCB / Pad / Component)
          8) Variation Source Analysis
          9) Anomaly Diagnosis & Recommendation (auto-expand pages by anomaly count)
         10) Process Risk Evaluation
         11) Conclusion
         12) Appendix
        Returns (True, None) on success, (False, error_message) on failure.
        """
        store = SessionStore()
        if not store.meas_meta.get("is_valid", False):
            return (False, "無量測資料，無法產生 PPTX 報告。")
        try:
            from app.services.pptx_report_builder import build_pptx_report
            from app.analytics.summary_engine import compute_summary
            from app.data.session_store import _analysis_cache_key, filter_analysis_df
            from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload

            wo_master = getattr(store, "workorder_master", {}) or {}
            wo_spec = getattr(store, "workorder_spec", {}) or {}

            # Build summary data
            df = store.get_analysis_df()
            if df is None or df.empty:
                return (False, "無量測資料。")

            batch = getattr(store, "filter_batch", None) or "全部 (All)"
            refdes_filter = getattr(store, "filter_refdes", None) or "全部 (All)"
            part_type = getattr(store, "filter_part_type", None) or "全部 (All)"
            product = getattr(store, "filter_product", None)
            time_start = getattr(store, "filter_time_start", None)
            time_end = getattr(store, "filter_time_end", None)
            line = getattr(store, "filter_line", None)
            filtered_df = filter_analysis_df(
                df, batch, refdes_filter, part_type,
                product=product, time_start=time_start, time_end=time_end, line=line,
            )
            if filtered_df.empty:
                return (False, "過濾後無資料。")

            available_features = [col for col in FEATURE_COLUMNS if col in filtered_df.columns]
            raw_selected_features = list(getattr(store, "selected_features", None) or [])
            selected_features = [
                col for col in raw_selected_features if col in available_features
            ] or available_features[:1]

            primary_sf = selected_features[0] if selected_features else None
            payload: Dict[str, Any] = {}
            cache_key = _analysis_cache_key(
                selected_features,
                batch,
                refdes_filter,
                part_type,
                product=product,
                time_start=time_start,
                time_end=time_end,
                line=line,
                spec_version=store.spec_cache_token(wo_spec),
            )
            cached_payload = getattr(store, "_analysis_cache", {}).get(cache_key)
            if isinstance(cached_payload, dict):
                payload = cached_payload
            else:
                last_payload = getattr(store, "last_analysis_payload", None)
                if isinstance(last_payload, dict) and _payload_matches_report_context(
                    last_payload,
                    selected_features=selected_features,
                    batch=batch,
                    refdes=refdes_filter,
                    part_type=part_type,
                ):
                    payload = last_payload

            payload_cache_hit = bool(payload)
            if isinstance(payload.get("summary"), dict) and payload["summary"]:
                summary_data = payload["summary"]
            else:
                summary_data = compute_summary(
                    filtered_df,
                    wo_spec,
                    primary_feature=primary_sf,
                    workorder_master=wo_master,
                )

            if selected_features:
                if not payload:
                    usl, lsl, target = _get_spec_for_feature(wo_spec, selected_features[0])
                    computed_payload, payload_err = compute_analysis_payload(
                        filtered_df,
                        selected_features,
                        usl,
                        lsl,
                        target,
                        wo_spec,
                        workorder_master=wo_master,
                    )
                    if computed_payload:
                        payload = computed_payload
                        if isinstance(payload.get("summary"), dict) and payload["summary"]:
                            summary_data = payload["summary"]
                    else:
                        payload = getattr(store, "last_analysis_payload", None) or {}
                        if payload_err:
                            logger.warning(
                                "PPTX 匯出重算分析 payload 失敗，改用快取結果: %s",
                                payload_err,
                            )
                if payload:
                    payload.setdefault("performance", {})["report_payload_cache_hit"] = payload_cache_hit
                    payload.setdefault("performance", {})["report_cache_key"] = cache_key
                    if isinstance(payload.get("summary"), dict) and payload["summary"]:
                        summary_data = payload["summary"]
            else:
                logger.warning(
                    "PPTX 匯出: 過濾後資料缺少可分析特徵欄位，略過診斷 payload 快取回退"
                )
                payload = {}

            if isinstance(payload.get("summary"), dict) and payload["summary"]:
                summary_data = payload["summary"]

            resolved_template = TEMPLATE_ENGINEERING
            if template_type != TEMPLATE_ENGINEERING:
                logger.debug(
                    "generate_pptx_report: template_type=%r coerced to engineering-only",
                    template_type,
                )
            selected_chart_ids = (
                chart_ids_to_export
                if chart_ids_to_export
                else TEMPLATE_DEFAULT_CHARTS.get(resolved_template, [])
            )

            chart_render_stats: Dict[str, int] = {"requests": 0, "hits": 0, "misses": 0}
            cached_chart_render = _make_cached_chart_renderer(chart_render_stats)

            diagnostics = _build_pptx_diagnostics(
                payload,
                selected_features,
                render_chart_fn=cached_chart_render,
            )
            diagnostics = _filter_diagnostics_by_selected_charts(diagnostics, selected_chart_ids)
            report_context_payload = report_context.build_pptx_report_context(
                store=store,
                filtered_df=filtered_df,
                summary_data=summary_data,
                diagnostics=diagnostics,
                selected_features=selected_features,
                batch=batch,
                refdes_filter=refdes_filter,
                part_type=part_type,
                product=product,
                time_start=time_start,
                time_end=time_end,
                line=line,
                analysis_payload=payload if payload else None,
            )
            report_context_payload["template_type"] = resolved_template
            report_context_payload["selected_chart_ids"] = selected_chart_ids
            report_context_payload["performance"] = {
                "payload_cache_hit": payload_cache_hit,
                "analysis_cache_key": cache_key,
                "chart_render_cache": chart_render_stats,
            }
            data_scope = report_context_payload.get("data_scope", {})
            report_context_payload["evidence_coverage"] = report_context.build_chart_evidence_coverage(
                selected_chart_ids=selected_chart_ids,
                selected_features=selected_features,
                available_features=available_features,
                has_coordinate_data=bool(
                    isinstance(data_scope, dict)
                    and data_scope.get("has_coordinate_data")
                ),
            )
            try:
                from app.services.diagnostic_evidence_matrix import build_diagnostic_evidence_matrix
                from app.services.report_process_narrative import build_process_diagnosis_report_payload

                matrix = build_diagnostic_evidence_matrix(
                    payload,
                    selected_chart_ids=selected_chart_ids,
                    filter_context=report_context_payload.get("filter_context", {}),
                )
                if matrix:
                    payload["diagnostic_evidence_matrix"] = matrix
                    report_context_payload["diagnostic_evidence_matrix"] = matrix
                    pdr = build_process_diagnosis_report_payload(payload)
                    if pdr:
                        report_context_payload["process_diagnosis_report"] = pdr
            except (ImportError, AttributeError, KeyError, TypeError, ValueError):
                logger.debug("diagnostic evidence matrix rebuild skipped", exc_info=True)

            ok, err = build_pptx_report(
                wo_master=wo_master,
                wo_spec=wo_spec,
                summary_data=summary_data,
                diagnostics=diagnostics,
                analysis_payload=payload,
                report_context=report_context_payload,
                output_path=output_path,
                template_type=resolved_template,
                chart_ids_to_export=selected_chart_ids,
                progress_callback=progress_callback,
                render_chart_fn=cached_chart_render,
            )
            return (ok, err)
        except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
            logger.exception("匯出 PPTX 報告失敗: %s", output_path)
            return (False, str(e))
