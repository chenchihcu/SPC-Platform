from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


def build_pptx_diagnostics(
    payload: Dict[str, Any],
    selected_features: List[str],
    *,
    include_chart_render: bool,
    feature_display_names: Dict[str, str],
    normalize_pptx_severity_fn: Callable[..., str],
    collect_actions_fn: Callable[..., List[str]],
    normalize_observable_charts_fn: Callable[[Any], List[str]],
    display_name_to_chart_id_fn: Callable[[str], Optional[str]],
    get_pptx_chart_title_fn: Callable[[str], str],
    format_evidence_lines_fn: Callable[[Dict[str, Any], int], List[str]],
    format_ipc_lines_fn: Callable[[Any, int], List[str]],
    get_no_chart_reason_fn: Callable[[str, Dict[str, Any]], str],
    logger: Any,
    render_chart_fn: Optional[Callable[..., Optional[bytes]]] = None,
) -> List[Dict[str, Any]]:
    """Assemble diagnostic entries from root-cause hints and optional chart snapshots."""
    diagnostics: List[Dict[str, Any]] = []
    try:
        from app.analytics.root_cause_engine import infer_root_cause_hints
        if include_chart_render and render_chart_fn is None:
            from app.services.chart_render import render_chart_to_png_bytes
            render_chart_fn = render_chart_to_png_bytes
    except ImportError:
        return diagnostics

    requested_features = [str(feature).strip() for feature in selected_features if str(feature).strip()]
    payload_features = [
        str(feature).strip()
        for feature in (payload.get("selected_features") or [])
        if str(feature).strip()
    ]
    parameters = (payload.get("parameters") or {}) if isinstance(payload, dict) else {}

    diagnostic_sources: List[Tuple[Optional[str], Dict[str, Any]]] = []
    if len(requested_features) > 1 and isinstance(parameters, dict):
        for feature in requested_features:
            feature_payload = parameters.get(feature)
            if not isinstance(feature_payload, dict):
                continue
            synthesized_payload = dict(feature_payload)
            synthesized_payload["selected_features"] = [feature]
            synthesized_payload["parameters"] = {feature: feature_payload}
            diagnostic_sources.append((feature, synthesized_payload))

    if not diagnostic_sources:
        primary_feature: Optional[str]
        if requested_features:
            primary_feature = requested_features[0]
        elif payload_features:
            primary_feature = payload_features[0]
        else:
            primary_feature = None
        diagnostic_sources.append((primary_feature, payload))

    seen_keys: set[tuple[str, str, str]] = set()
    for feature_name, diagnostic_payload in diagnostic_sources:
        source_emitted = False
        try:
            hints = infer_root_cause_hints(diagnostic_payload)
        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            logger.exception("PPTX: 根因提示計算失敗 feature=%s", feature_name or "unknown")
            continue
        if not isinstance(hints, list):
            continue

        feature_label = (
            feature_display_names.get(feature_name, feature_name).strip()
            if feature_name else ""
        )
        chart_features = [feature_name] if feature_name else requested_features or payload_features
        for hint in hints:
            if not isinstance(hint, dict):
                continue
            severity_level = normalize_pptx_severity_fn(
                hint.get("severity", "info"),
                priority=hint.get("priority"),
            )
            if severity_level not in {"error", "warning"}:
                continue
            summary_text = str(hint.get("hint", "")).strip()
            if not summary_text:
                continue
            rule_id = str(hint.get("rule_id", "")).strip() or None
            priority_level = str(hint.get("priority", "")).strip().lower() or None
            dedupe_key = (feature_name or "", rule_id or "", summary_text)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            recommended_actions = collect_actions_fn(
                diagnostic_payload,
                rule_id=rule_id,
                limit=3,
            )
            chart_title = "相關圖表"
            fallback_chart_title: Optional[str] = None
            fallback_chart_id: Optional[str] = None
            chart_bytes: Optional[bytes] = None
            raw_observable_charts = hint.get("observable_charts", []) or []
            observable_charts = normalize_observable_charts_fn(raw_observable_charts)
            if include_chart_render and render_chart_fn is not None:
                for chart_name in raw_observable_charts:
                    chart_id = display_name_to_chart_id_fn(str(chart_name))
                    if chart_id:
                        base_chart_title = get_pptx_chart_title_fn(chart_id)
                        resolved_chart_title = (
                            f"{feature_label} | {base_chart_title}"
                            if feature_label else base_chart_title
                        )
                        if not fallback_chart_title:
                            fallback_chart_title = resolved_chart_title
                            fallback_chart_id = chart_id
                        try:
                            chart_bytes = render_chart_fn(
                                chart_id,
                                diagnostic_payload,
                                features=chart_features,
                                context="report",
                            )
                        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError, OSError):
                            logger.debug("PPTX: 渲染圖表 %s 失敗", chart_id, exc_info=True)
                    else:
                        raw_chart_title = str(chart_name) or chart_title
                        resolved_chart_title = (
                            f"{feature_label} | {raw_chart_title}"
                            if feature_label else raw_chart_title
                        )
                        if not fallback_chart_title:
                            fallback_chart_title = resolved_chart_title
                    if chart_bytes:
                        chart_title = resolved_chart_title
                        break
                if not chart_bytes and fallback_chart_title:
                    chart_title = fallback_chart_title
                chart_missing_reason = (
                    get_no_chart_reason_fn(fallback_chart_id, diagnostic_payload)
                    if (not chart_bytes and fallback_chart_id)
                    else "此異常目前無可用圖表輸出。"
                )
            else:
                chart_missing_reason = "風險彙總模式：略過圖像渲染。"

            diagnostics.append(
                {
                    "feature_label": feature_label,
                    "summary": (
                        f"[{feature_label}] {summary_text}"
                        if feature_label else summary_text
                    ),
                    "rule_id": rule_id or "",
                    "priority": priority_level,
                    "severity": severity_level,
                    "observable_charts": observable_charts,
                    "chart_title": chart_title,
                    "chart_bytes": chart_bytes,
                    "chart_missing_reason": chart_missing_reason,
                    "evidence_type": (
                        "統計計算 / 圖表證據 / 規則推論"
                        if chart_bytes
                        else "統計計算 / 規則推論"
                    ),
                    "evidence_lines": format_evidence_lines_fn(hint.get("evidence", {}), 4),
                    "ipc_lines": format_ipc_lines_fn(hint.get("ipc_refs", []), 2),
                    "recommended_actions": recommended_actions[:2],
                }
            )
            source_emitted = True

        # Fallback: when no rule hints are emitted but a key chart payload is explicitly invalid,
        # still expose one diagnostic card so reports retain the concrete missing reason.
        if (not source_emitted) and include_chart_render and ("summary" not in diagnostic_payload):
            fallback_specs: list[tuple[str, str, str]] = [
                ("spatial", "spatial_heatmap", "空間分析資料不可用"),
            ]
            for payload_key, chart_id, summary_text in fallback_specs:
                chart_payload = diagnostic_payload.get(payload_key)
                if not isinstance(chart_payload, dict):
                    continue
                metadata = chart_payload.get("metadata")
                if not isinstance(metadata, dict):
                    continue
                if bool(metadata.get("is_valid", True)):
                    continue
                error_text = str(metadata.get("error", "")).strip()
                if not error_text:
                    continue
                base_chart_title = get_pptx_chart_title_fn(chart_id)
                resolved_chart_title = (
                    f"{feature_label} | {base_chart_title}"
                    if feature_label
                    else base_chart_title
                )
                diagnostics.append(
                    {
                        "feature_label": feature_label,
                        "summary": (
                            f"[{feature_label}] {summary_text}"
                            if feature_label
                            else summary_text
                        ),
                        "rule_id": f"{payload_key}_data_unavailable",
                        "priority": "medium",
                        "severity": "warning",
                        "observable_charts": [base_chart_title],
                        "chart_title": resolved_chart_title,
                        "chart_bytes": None,
                        "chart_missing_reason": get_no_chart_reason_fn(chart_id, diagnostic_payload),
                        "evidence_type": "未納入：資料缺失",
                        "evidence_lines": [f"Reason: {error_text}"],
                        "ipc_lines": [],
                        "recommended_actions": collect_actions_fn(
                            diagnostic_payload,
                            rule_id=None,
                            limit=2,
                        )[:2],
                    }
                )
                break

    diagnostics.sort(
        key=lambda item: (
            0
            if str(item.get("severity", "")).strip().lower() == "error"
            else 1
            if str(item.get("severity", "")).strip().lower() == "warning"
            else 2
        )
    )
    return diagnostics
