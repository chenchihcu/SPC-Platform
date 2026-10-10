import json
import logging
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from app.data.session_store import SessionStore
from app.utils.constants import FEATURE_COLUMNS, FEATURE_DISPLAY_NAMES
from app.services import report_risk
from app.services import report_diagnostics
from app.services import report_context
from app.services import report_chart_lookup
from app.services import report_actions
from app.services import report_formatters
from app.services import report_chart_reason

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
    stencil_analysis: Optional[Dict[str, Any]] = None,
) -> bool:
    if not isinstance(payload, dict):
        return False
    if list(payload.get("selected_features") or []) != list(selected_features):
        return False
    scope_matches = (
        str(payload.get("_ctx_batch", "")) == str(batch)
        and str(payload.get("_ctx_refdes", "")) == str(refdes)
        and str(payload.get("_ctx_part_type", "")) == str(part_type)
    )
    if not scope_matches:
        return False
    if stencil_analysis is not None:
        return (payload.get("stencil_analysis") or {}) == stencil_analysis
    return True


def _make_cached_chart_renderer(
    stats: Dict[str, int],
) -> Callable[..., Optional[bytes]]:
    from app.services.chart_render import render_chart_to_png_bytes

    cache: Dict[Tuple[str, Tuple[str, ...], bool, str, str], Optional[bytes]] = {}

    def _render(
        chart_id: str,
        payload: Dict[str, Any],
        *,
        features: Optional[List[str]] = None,
        normalized: bool = False,
        group_key: Optional[str] = None,
        context: str = "report",
    ) -> Optional[bytes]:
        key = (
            chart_id,
            tuple(features or []),
            bool(normalized),
            str(group_key or "default"),
            context,
        )
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
            group_key=group_key,
            context=context,
        )
        cache[key] = rendered
        return rendered

    return _render




# ── Risk level ──────────────────────────────────────────────────────────────

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



def _get_no_chart_reason(chart_id: str, payload: Dict[str, Any]) -> str:
    return report_chart_reason.get_no_chart_reason(
        chart_id,
        payload,
        catalog_by_id_fn=_catalog_by_id,
    )


def _get_spec_for_feature(workorder_spec: dict, col: str) -> Tuple[float, float, float]:
    """Extract USL/LSL/Target for a single feature column from workorder spec."""
    key_map = {"Volume": "volume", "Area": "area", "Height": "height"}
    entry = workorder_spec.get(key_map.get(col, col.lower()), {}) or {}
    try:
        usl_raw = entry.get("usl")
        lsl_raw = entry.get("lsl")
        target_raw = entry.get("target")
        usl = float(usl_raw) if usl_raw is not None else 120.0
        lsl = float(lsl_raw) if lsl_raw is not None else 80.0
        target = float(target_raw) if target_raw is not None else 100.0
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
            from app.viewmodels.chart_analysis_viewmodel import (
                _apply_stencil_statistical_contract,
                compute_analysis_payload,
            )

            wo_master = getattr(store, "workorder_master", {}) or {}
            wo_spec = getattr(store, "workorder_spec", {}) or {}
            source_wo_spec = wo_spec

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

            from app.services.stencil_document_service import (
                derive_percentage_dataframe,
                infer_measurement_side,
                percentage_workorder_spec,
            )

            product_name = str(wo_master.get("product_name") or "").strip()
            side = infer_measurement_side(filtered_df, getattr(store, "meas_meta", {}) or {})
            if product_name and side:
                domain_result = derive_percentage_dataframe(
                    filtered_df,
                    product_name=product_name,
                    side=side,
                    measurement_units=(getattr(store, "meas_meta", {}) or {}).get(
                        "measurement_units"
                    )
                    or {},
                )
                filtered_df = domain_result.dataframe
                store.analysis_domain_meta = dict(domain_result.metadata)
                if domain_result.metadata.get("value_domain") == "percent":
                    wo_spec = percentage_workorder_spec(product_name) or {}
                else:
                    wo_spec = {}
            elif product_name:
                store.analysis_domain_meta = {
                    "value_domain": "raw",
                    "side": "",
                    "matched": 0,
                    "total": int(len(filtered_df)),
                    "coverage": 0.0,
                    "verify": True,
                    "verify_reasons": ["量測資料無法確認 Top/Bottom Side"],
                    "unmatched_pads": [],
                    "original_units": dict(
                        ((getattr(store, "meas_meta", {}) or {}).get("measurement_units") or {})
                    ),
                }
                wo_spec = {}
            else:
                store.analysis_domain_meta = {
                    "value_domain": "legacy",
                    "side": "",
                    "matched": int(len(filtered_df)),
                    "total": int(len(filtered_df)),
                    "coverage": 1.0,
                    "verify": False,
                    "verify_reasons": [],
                    "unmatched_pads": [],
                    "original_units": dict(
                        ((getattr(store, "meas_meta", {}) or {}).get("measurement_units") or {})
                    ),
                }
            wo_master = {
                **dict(wo_master),
                "_stencil_analysis": dict(
                    getattr(store, "analysis_domain_meta", {}) or {}
                ),
            }

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
                spec_version=store.spec_cache_token(wo_spec)
                + "|"
                + json.dumps(
                    getattr(store, "analysis_domain_meta", {}) or {},
                    sort_keys=True,
                    ensure_ascii=True,
                    default=str,
                ),
            )
            cached_payload = getattr(store, "_analysis_cache", {}).get(cache_key)
            if isinstance(cached_payload, dict):
                payload = cached_payload
            else:
                # Historical raw sessions used a cache key without stencil-domain
                # evidence.  Reuse their trend payload only after applying the new
                # fail-closed statistical contract; percent-domain caches never use
                # this compatibility path.
                domain_meta = dict(getattr(store, "analysis_domain_meta", {}) or {})
                if domain_meta.get("value_domain") == "raw":
                    legacy_cache_key = _analysis_cache_key(
                        selected_features,
                        batch,
                        refdes_filter,
                        part_type,
                        product=product,
                        time_start=time_start,
                        time_end=time_end,
                        line=line,
                        spec_version=store.spec_cache_token(source_wo_spec),
                    )
                    legacy_cached = getattr(store, "_analysis_cache", {}).get(
                        legacy_cache_key
                    )
                    if isinstance(legacy_cached, dict):
                        payload = deepcopy(legacy_cached)
                        _apply_stencil_statistical_contract(payload, domain_meta)

            if not payload:
                last_payload = getattr(store, "last_analysis_payload", None)
                if isinstance(last_payload, dict) and _payload_matches_report_context(
                    last_payload,
                    selected_features=selected_features,
                    batch=batch,
                    refdes=refdes_filter,
                    part_type=part_type,
                    stencil_analysis=dict(
                        getattr(store, "analysis_domain_meta", {}) or {}
                    ),
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
