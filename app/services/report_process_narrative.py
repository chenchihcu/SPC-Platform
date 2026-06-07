"""Process-language narrative lines for decision layer (not raw statistic dumps)."""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.diagnostic_evidence_matrix import build_readable_diagnostic_tabs


def build_decision_narrative(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Build short Chinese narratives from diagnosis_engine + process_risk + knowledge_inference.

    Returns keys: core_diagnosis_zh, risk_paragraph_zh, action_hint_zh
    """
    sum_d: Dict[str, Any] = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    process: Dict[str, Any] = sum_d["process"] if isinstance(sum_d.get("process"), dict) else {}
    de: Dict[str, Any] = (
        process["diagnosis_engine"] if isinstance(process.get("diagnosis_engine"), dict) else {}
    )
    pr: Dict[str, Any] = (
        process["process_risk"] if isinstance(process.get("process_risk"), dict) else {}
    )
    kinf: Dict[str, Any] = (
        payload["knowledge_inference"]
        if isinstance(payload.get("knowledge_inference"), dict)
        else {}
    )

    scope = str(de.get("scope") or "Global")
    patterns = de.get("process_patterns") or []
    dist = str(de.get("distribution_shape") or "Normal")
    level = str(pr.get("level") or "LOW")
    rationale = str(pr.get("rationale_zh") or "")

    pat_zh = "、".join(str(p) for p in patterns) if patterns else "未分類"

    core = (
        f"影響範圍判定為【{scope}】；製程型態訊號包含【{pat_zh}】；"
        f"分布型態為【{dist}】。"
    )
    risk_p = f"製程風險等級：{level}。{rationale}"

    hints: List[str] = []
    steps = kinf.get("steps")
    step4 = steps.get("4_correlation") if isinstance(steps, dict) else {}
    if isinstance(step4, dict):
        for line in step4.get("qualitative_hints_zh") or []:
            if isinstance(line, str) and line.strip():
                hints.append(line.strip())
    hypo = str(kinf.get("hypothesis_domain") or "process")
    if hypo == "DFM_preferred":
        hints.insert(0, "異常集中於特定元件或焊墊時，宜同步檢視焊墊／開口設計與 IPC land pattern 合理性。")

    action = "；".join(hints[:4]) if hints else "依儀表板建議行動與優先檢查項目執行排查。"

    return {
        "core_diagnosis_zh": core,
        "risk_paragraph_zh": risk_p,
        "action_hint_zh": action,
    }


def build_process_diagnosis_report_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fixed four-layer structure for PPTX「製程診斷報告」semantics (A–D).

    Evidence (C) and raw data (D) remain primarily in existing gallery / spec slides;
    this payload supplies concise bridge text.
    """
    if not isinstance(payload.get("summary"), dict):
        return {}
    sum_d: Dict[str, Any] = payload["summary"]
    process: Dict[str, Any] = sum_d["process"] if isinstance(sum_d.get("process"), dict) else {}
    de: Dict[str, Any] = (
        process["diagnosis_engine"] if isinstance(process.get("diagnosis_engine"), dict) else {}
    )
    pr: Dict[str, Any] = (
        process["process_risk"] if isinstance(process.get("process_risk"), dict) else {}
    )
    kinf: Dict[str, Any] = (
        payload["knowledge_inference"]
        if isinstance(payload.get("knowledge_inference"), dict)
        else {}
    )
    matrix: Dict[str, Any] = (
        payload["diagnostic_evidence_matrix"]
        if isinstance(payload.get("diagnostic_evidence_matrix"), dict)
        else {}
    )
    if not de and not pr and not matrix:
        return {}

    verdict = str(process.get("verdict") or "—")
    narrative = build_decision_narrative(payload)
    matrix_summary: Dict[str, Any] = (
        matrix["summary"] if isinstance(matrix.get("summary"), dict) else {}
    )
    coverage: Dict[str, Any] = (
        matrix["coverage"] if isinstance(matrix.get("coverage"), dict) else {}
    )
    combo: Dict[str, Any] = (
        matrix["combination_summary"]
        if isinstance(matrix.get("combination_summary"), dict)
        else {}
    )
    top_evidence = (
        matrix_summary["top_evidence"]
        if isinstance(matrix_summary.get("top_evidence"), list)
        else []
    )
    readable_tabs = build_readable_diagnostic_tabs(matrix) if matrix else {}
    readable_evidence = [
        *readable_tabs.get("overview", [])[:3],
        *readable_tabs.get("chart_linkage", [])[:3],
    ][:6]

    return {
        "schema_version": "1.1.0",
        "A_decision": {
            "process_verdict": verdict,
            "core_diagnosis_zh": narrative.get("core_diagnosis_zh", ""),
            "risk_level": str(pr.get("level") or "LOW"),
            "risk_rationale_zh": str(pr.get("rationale_zh") or ""),
            "pattern_logic": str(de.get("pattern_logic") or ""),
        },
        "B_diagnosis": {
            "scope": str(de.get("scope") or "Global"),
            "process_patterns": de.get("process_patterns") or [],
            "distribution_shape": str(de.get("distribution_shape") or "Normal"),
            "hypothesis_domain": str(kinf.get("hypothesis_domain") or "process"),
            "inference_steps": kinf.get("steps") if isinstance(kinf.get("steps"), dict) else {},
        },
        "C_evidence": {
            "bridge_zh": str(
                matrix_summary.get("verdict_zh")
                or "圖表依用途分類之證據見「Chart Evidence Gallery」與異常診斷詳頁；請對照 Statistical Signals 之 evidence_refs。"
            ),
            "combination_coverage_zh": str(matrix_summary.get("coverage_line_zh") or ""),
            "candidate_count": combo.get("candidate_count"),
            "applicable_candidate_count": coverage.get("applicable_candidate_count"),
            "covered_candidate_count": coverage.get("covered_candidate_count"),
            "coverage_pct": coverage.get("coverage_pct"),
            "top_evidence": top_evidence[:5],
            "readable_evidence": readable_evidence,
            "readable_tabs": readable_tabs,
        },
        "D_data": {
            "bridge_zh": "產品／工單／管制規格與統計摘要見本報告資料章節與附錄。",
        },
    }
