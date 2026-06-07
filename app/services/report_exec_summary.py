from __future__ import annotations

import html
from typing import Any, Callable, Dict, List, Optional


def _try_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_executive_summary_html(
    hints: List[Dict[str, Any]],
    ro_payload: Dict[str, Any],
    summary_data: Dict[str, Any],
    total_n: int,
    batch_qty: Any,
    *,
    batch_no: Any = None,
    supplier_work_order_no: Any = None,
    outsource_work_order_no: Any = None,
    compute_risk_level_fn: Callable[..., str],
    primary_feature: Optional[str] = None,
    diagnostics: Optional[List[Dict[str, Any]]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
    decision_narrative: Optional[Dict[str, str]] = None,
) -> str:
    """Build the top-of-report Executive Summary block."""
    risk = str((risk_assessment or {}).get("level", "")).strip().upper()
    if risk not in {"HIGH", "MEDIUM", "LOW"}:
        risk = compute_risk_level_fn(
            hints,
            process=summary_data.get("process", {}),
            diagnostics=diagnostics,
        )
    risk_badge = {
        "HIGH": "<span class='risk-badge risk-high'>🔴 HIGH 高風險</span>",
        "MEDIUM": "<span class='risk-badge risk-medium'>🟡 MEDIUM 中風險</span>",
        "LOW": "<span class='risk-badge risk-low'>🟢 LOW 低風險</span>",
    }.get(risk, "")

    process = summary_data.get("process", {})
    min_cpk = _try_float(process.get("min_cpk"))
    min_cpk_measure = process.get("min_cpk_measure", "")
    overall_yield = _try_float(process.get("overall_yield_pct"))
    verdict = process.get("verdict", "—")

    parts = [
        "<div id='exec-summary' class='exec-summary'>",
        f"<h2 style='margin-top:0;color:#0B3C5D;'>⚡ 執行摘要 (Executive Summary)&nbsp;&nbsp;{risk_badge}</h2>",
        "<div class='kpi-grid'>",
    ]
    cpk_str = f"{min_cpk:.3f} ({min_cpk_measure})" if min_cpk is not None and min_cpk_measure else (
        f"{min_cpk:.3f}" if min_cpk is not None else "—"
    )
    kpis = [
        ("樣本總數", f"{total_n:,}" if total_n else "—"),
        ("供應商製令工單", str(supplier_work_order_no) if supplier_work_order_no else "—"),
        (
            "醫電製令工單",
            str(outsource_work_order_no) if outsource_work_order_no else (str(batch_no) if batch_no else "—"),
        ),
        ("批量（片）", str(batch_qty) if batch_qty else "—"),
        ("整體良率", f"{overall_yield:.1f}%" if overall_yield is not None else "—"),
        ("最低 Cpk", cpk_str),
        ("製程判定", verdict),
    ]
    for label, value in kpis:
        parts.append(
            f"<div class='kpi-item'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'>{value}</div>"
            f"</div>"
        )
    parts.append("</div>")

    dn = decision_narrative if isinstance(decision_narrative, dict) else {}
    core_dn = str(dn.get("core_diagnosis_zh") or "").strip()
    risk_dn = str(dn.get("risk_paragraph_zh") or "").strip()
    action_dn = str(dn.get("action_hint_zh") or "").strip()
    if core_dn or risk_dn or action_dn:
        parts.append(
            "<div class='decision-narrative' "
            "style='margin-top:14px;padding:12px 14px;background:#F8FBFF;"
            "border:1px solid #B3CDDF;border-radius:6px;'>"
        )
        parts.append(
            "<h3 style='margin-top:0;color:#0B3C5D;'>"
            "🧭 製程語言摘要（Decision narrative）</h3>"
        )
        if core_dn:
            parts.append(
                "<p style='margin:6px 0;font-size:13px;'>"
                f"<strong>核心診斷：</strong>{html.escape(core_dn)}</p>"
            )
        if risk_dn:
            parts.append(
                "<p style='margin:6px 0;font-size:13px;'>"
                f"<strong>風險研判：</strong>{html.escape(risk_dn)}</p>"
            )
        if action_dn:
            parts.append(
                "<p style='margin:6px 0;font-size:13px;'>"
                f"<strong>行動提示：</strong>{html.escape(action_dn)}</p>"
            )
        parts.append("</div>")

    if hints:
        priority_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
        sorted_hints = sorted(hints, key=lambda h: priority_order.get(h.get("priority", "info"), 3))
        severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}
        parts.append("<h3 style='margin-top:14px;'>📋 主要根因觀察（TOP 3）</h3><ol style='margin:4px 0 0 16px;'>")
        for hint in sorted_hints[:3]:
            icon = severity_icon.get(hint.get("severity", "info"), "🔵")
            hint_text = str(hint.get("hint", ""))
            short = hint_text[:180] + ("…" if len(hint_text) > 180 else "")
            charts = hint.get("observable_charts", [])
            chart_tag = (
                f" <span style='font-size:11px;color:#5B6770;'>→ 見：{', '.join(charts[:2])}</span>"
                if charts else ""
            )
            parts.append(f"<li style='margin-bottom:4px;'>{icon}&nbsp;{short}{chart_tag}</li>")
        parts.append("</ol>")

    if ro_payload and ro_payload.get("metadata", {}).get("is_valid"):
        labels = ro_payload.get("data", {}).get("labels", [])
        counts = ro_payload.get("data", {}).get("counts", [])
        if labels:
            parts.append(
                "<h3 style='margin-top:14px;'>🎯 TOP5 重複異常元件（Volume OOS 違規次數）</h3>"
                "<table style='width:auto;min-width:420px;'>"
                "<tr><th>排名</th><th>元件 (RefDes)</th><th>違規次數</th><th>跳轉</th></tr>"
            )
            ro_chart_anchor = f"ro-{primary_feature.lower()}" if primary_feature else "ro-volume"
            for index, (label, count) in enumerate(zip(labels[:5], counts[:5]), 1):
                parts.append(
                    f"<tr>"
                    f"<td style='text-align:center;font-weight:bold;'>#{index}</td>"
                    f"<td><strong>{label}</strong></td>"
                    f"<td style='text-align:center;'>{count}</td>"
                    f"<td style='font-size:11px;'><a href='#{ro_chart_anchor}'>Repeated Offender 圖</a></td>"
                    f"</tr>"
                )
            parts.append("</table>")

    parts.append("</div>")
    return "\n".join(parts)


def build_executive_summary_pptx_data(
    summary_data: Dict[str, Any],
    diagnostics: Optional[List[Dict[str, Any]]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
    *,
    generate_one_liner_fn: Callable[..., str],
    generate_risk_sentence_fn: Callable[..., str],
    derive_stability_verdict_fn: Callable[..., tuple],
    requires_immediate_action_fn: Callable[..., bool],
    anomaly_type_label_fn: Callable[[str], str],
    derive_process_state_fn: Optional[Callable[..., str]] = None,
    derive_problem_type_fn: Optional[Callable[..., str]] = None,
    problem_type_zh_fn: Optional[Callable[[str], str]] = None,
    generate_spi_narrative_fn: Optional[Callable[..., str]] = None,
    decision_narrative: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Compute structured data for the PPTX Executive Summary slide.

    Returns a dict with keys used directly by _build_slide_executive_summary()
    and _build_slide_core_diagnosis() in pptx_report_builder.
    """
    process = summary_data.get("process", {}) if isinstance(summary_data, dict) else {}
    diags = diagnostics if isinstance(diagnostics, list) else []
    ra = risk_assessment if isinstance(risk_assessment, dict) else {}

    verdict = str(process.get("verdict", "—") or "—")
    risk_level = str(ra.get("level", "LOW") or "LOW").upper()
    risk_display = str(ra.get("level_display", risk_level) or risk_level)
    error_count = int(ra.get("error_count", 0) or 0)

    stability_verdict, drift_feature, ooc_ratio = derive_stability_verdict_fn(diags)

    # Normality: check evidence_lines for "Is Normal: False"
    normality_passed = True
    for diag in diags:
        rule_id = str(diag.get("rule_id", "") or "").lower()
        if "normal" in rule_id:
            for ev_line in (diag.get("evidence_lines") or []):
                if "false" in str(ev_line).lower() and "normal" in str(ev_line).lower():
                    normality_passed = False
                    break
        if not normality_passed:
            break

    # Primary anomaly
    primary_diag = diags[0] if diags else {}
    primary_feature = str(
        primary_diag.get("feature_label", "")
        or drift_feature
        or ""
    ).strip()
    primary_rule_id = str(primary_diag.get("rule_id", "") or "").lower()
    anomaly_type = anomaly_type_label_fn(primary_rule_id)

    one_liner = generate_one_liner_fn(
        verdict=verdict,
        risk_level=risk_level,
        stability_verdict=stability_verdict,
        primary_feature=primary_feature,
        primary_rule_id=primary_rule_id,
    )

    risk_sentence = generate_risk_sentence_fn(
        verdict=verdict,
        risk_level=risk_level,
        stability_verdict=stability_verdict,
        normality_passed=normality_passed,
        primary_feature=primary_feature,
    )

    needs_action = requires_immediate_action_fn(
        risk_level=risk_level,
        stability_verdict=stability_verdict,
        error_count=error_count,
    )

    # Priority check directions: top 3 deduplicated actions from leading diagnostics
    check_dirs: List[str] = []
    seen_dirs: set = set()
    for diag in diags[:3]:
        for action in (diag.get("recommended_actions") or [])[:2]:
            text = str(action or "").strip()
            if text and text not in seen_dirs:
                check_dirs.append(text)
                seen_dirs.add(text)
            if len(check_dirs) >= 3:
                break
        if len(check_dirs) >= 3:
            break

    # Min Cpk string
    min_cpk_raw = _try_float(process.get("min_cpk"))
    min_cpk_measure = str(process.get("min_cpk_measure", "") or "").strip()
    if min_cpk_raw is not None:
        min_cpk_str = (
            f"{min_cpk_measure} / Cpk={min_cpk_raw:.3f}"
            if min_cpk_measure
            else f"Cpk={min_cpk_raw:.3f}"
        )
    else:
        min_cpk_str = "—"

    # ── SMT SPI process state & problem type (new fields) ───────────────────
    process_state = "穩定"
    if derive_process_state_fn is not None:
        process_state = derive_process_state_fn(
            diags, stability_verdict=stability_verdict
        )

    problem_type = "Unknown"
    if derive_problem_type_fn is not None:
        problem_type = derive_problem_type_fn(diags)

    problem_type_label = problem_type_zh_fn(problem_type) if problem_type_zh_fn else problem_type

    spi_narrative = ""
    if generate_spi_narrative_fn is not None:
        spi_narrative = generate_spi_narrative_fn(
            process_state=process_state,
            problem_type=problem_type,
            primary_feature=primary_feature,
            risk_level=risk_level,
            ooc_ratio=ooc_ratio,
        )

    dn = decision_narrative if isinstance(decision_narrative, dict) else {}
    core_dn = str(dn.get("core_diagnosis_zh") or "").strip()
    if core_dn:
        spi_narrative = f"{core_dn}\n\n{spi_narrative}".strip() if spi_narrative else core_dn
    risk_dn = str(dn.get("risk_paragraph_zh") or "").strip()
    if risk_dn:
        risk_sentence = risk_dn
    action_dn = str(dn.get("action_hint_zh") or "").strip()
    if action_dn:
        check_dirs.insert(0, action_dn[:280])

    return {
        "one_liner": one_liner,
        "verdict": verdict,
        "risk_level": risk_level,
        "risk_display": risk_display,
        "requires_action": needs_action,
        "primary_feature": primary_feature,
        "anomaly_type": anomaly_type,
        "stability_verdict": stability_verdict,
        "ooc_ratio": ooc_ratio,
        "risk_sentence": risk_sentence,
        "check_directions": check_dirs,
        "min_cpk_str": min_cpk_str,
        "normality_passed": normality_passed,
        "error_count": error_count,
        "warning_count": int(ra.get("warning_count", 0) or 0),
        # SMT SPI specific
        "process_state": process_state,
        "problem_type": problem_type,
        "problem_type_label": problem_type_label,
        "spi_narrative": spi_narrative,
    }
