from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.process_risk_model import merge_risk_level
_log = logging.getLogger(__name__)


def normalize_pptx_severity(value: Any, *, priority: Any = None) -> str:
    """Normalize heterogeneous severity labels into error/warning/info."""
    raw = str(value or "").strip().lower()
    alias_map = {
        "critical": "error",
        "high": "error",
        "warn": "warning",
        "medium": "warning",
        "med": "warning",
        "low": "info",
    }
    normalized = alias_map.get(raw, raw or "info")
    if normalized in {"error", "warning", "info"}:
        return normalized
    priority_raw = str(priority or "").strip().lower()
    if priority_raw == "high":
        return "error"
    if priority_raw == "medium":
        return "warning"
    return "info"


def normalize_process_verdict(value: Any) -> str:
    """Normalize process verdict into ACCEPTABLE / IMPROVEMENT / UNACCEPTABLE / UNKNOWN."""
    raw = str(value or "").strip().lower()
    if raw in {"不可接受", "unacceptable", "reject", "not acceptable"}:
        return "UNACCEPTABLE"
    if raw in {"待改善", "需改善", "needs improvement", "improvement"}:
        return "IMPROVEMENT"
    if raw in {"可接受", "acceptable", "accept"}:
        return "ACCEPTABLE"
    return "UNKNOWN"


def risk_level_display(level: str) -> str:
    return {
        "HIGH": "高風險 (High)",
        "MEDIUM": "中風險 (Medium)",
        "LOW": "低風險 (Low)",
    }.get(level, "低風險 (Low)")


def summarize_risk_signals(
    hints: Optional[List[Dict[str, Any]]] = None,
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, int]:
    """
    Summarize error/warning signal counts for risk scoring.

    Diagnostics are preferred when provided because they are the final PPTX-visible
    anomaly set after normalization and filtering.
    """
    source: List[Dict[str, Any]] = []
    if isinstance(diagnostics, list) and diagnostics:
        source = [item for item in diagnostics if isinstance(item, dict)]
    elif isinstance(hints, list):
        source = [item for item in hints if isinstance(item, dict)]

    high_priority_count = sum(
        1 for item in source if str(item.get("priority", "")).strip().lower() == "high"
    )

    error_count = 0
    warning_count = 0
    for item in source:
        severity = normalize_pptx_severity(
            item.get("severity", "info"),
            priority=item.get("priority"),
        )
        if severity == "error":
            error_count += 1
        elif severity == "warning":
            warning_count += 1

    return {
        "error_count": error_count,
        "warning_count": warning_count,
        "total_count": len(source),
        "high_priority_count": high_priority_count,
    }


def compute_risk_level(
    hints: List[Dict[str, Any]],
    *,
    process: Optional[Dict[str, Any]] = None,
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Derive overall risk level (HIGH / MEDIUM / LOW) from signals + process verdict."""
    signal_summary = summarize_risk_signals(hints=hints, diagnostics=diagnostics)
    error_count = signal_summary["error_count"]
    warning_count = signal_summary["warning_count"]
    high_priority_count = signal_summary["high_priority_count"]

    if error_count > 0 or high_priority_count >= 2:
        level = "HIGH"
    elif warning_count > 0 or high_priority_count >= 1:
        level = "MEDIUM"
    else:
        level = "LOW"

    verdict_bucket = normalize_process_verdict((process or {}).get("verdict"))
    if verdict_bucket == "UNACCEPTABLE":
        return "HIGH"
    if verdict_bucket == "IMPROVEMENT" and level == "LOW":
        return "MEDIUM"
    return level


def build_risk_assessment(
    *,
    process: Optional[Dict[str, Any]] = None,
    hints: Optional[List[Dict[str, Any]]] = None,
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a normalized risk snapshot used across HTML/PPTX report outputs."""
    process_dict = process if isinstance(process, dict) else {}
    hints_list = hints if isinstance(hints, list) else []
    signal_summary = summarize_risk_signals(hints=hints_list, diagnostics=diagnostics)
    level = compute_risk_level(
        hints_list,
        process=process_dict,
        diagnostics=diagnostics,
    )
    triad = process_dict.get("process_risk")
    triad_level: Optional[str] = None
    triad_rationale = ""
    if isinstance(triad, dict):
        raw_tl = triad.get("level")
        if raw_tl is not None:
            triad_level = str(raw_tl).strip().upper()
        triad_rationale = str(triad.get("rationale_zh") or "")
    if triad_level:
        level = merge_risk_level(level, triad_level)

    out: Dict[str, Any] = {
        "level": level,
        "level_display": risk_level_display(level),
        "error_count": int(signal_summary.get("error_count", 0)),
        "warning_count": int(signal_summary.get("warning_count", 0)),
        "total_count": int(signal_summary.get("total_count", 0)),
        "high_priority_count": int(signal_summary.get("high_priority_count", 0)),
        "verdict": process_dict.get("verdict"),
    }
    if isinstance(triad, dict):
        out["process_risk_triad"] = triad
        if triad_rationale:
            out["triad_rationale_zh"] = triad_rationale
    return out


# ── Diagnostic text generation (Priority 1/2 refactor) ──────────────────────

_ANOMALY_TYPE_LABELS: Dict[str, str] = {
    "cusum": "系統性漂移",
    "drift_detection": "製程漂移",
    "drift": "製程漂移",
    "ewma": "製程偏移",
    "shift_detection": "均值突變",
    "shift": "均值突變",
    "normality": "分布異常",
    "normal": "分布異常",
    "ooc": "超規異常",
    "oos": "超規異常",
    "spatial": "空間群聚異常",
    "edge": "邊緣異常",
    "run_rule": "連續趨勢觸發",
    "run": "連續趨勢觸發",
}


def anomaly_type_label(rule_id: str) -> str:
    """Translate a rule_id keyword into a Chinese anomaly type label."""
    lower = str(rule_id or "").lower()
    for key, label in _ANOMALY_TYPE_LABELS.items():
        if key in lower:
            return label
    return "製程異常"


def derive_stability_verdict(
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> tuple:
    """
    Derive stability verdict from PPTX diagnostic dicts.

    Returns:
        (verdict, drift_feature, ooc_ratio)
        verdict: "失控" / "警示" / "受控"
        drift_feature: feature_label of the drifting feature, or None
        ooc_ratio: float OOC ratio if parsed, or None
    """
    if not isinstance(diagnostics, list) or not diagnostics:
        return "受控", None, None

    # Pass 1: look for CUSUM error → 失控
    for diag in diagnostics:
        if not isinstance(diag, dict):
            continue
        rule_id = str(diag.get("rule_id", "") or "").lower()
        severity = str(diag.get("severity", "") or "").lower()
        feature = str(diag.get("feature_label", "") or "").strip()
        # Parse OOC Ratio from evidence_lines (e.g. "OOC Ratio: 96.4%")
        ooc_ratio: Optional[float] = None
        for line in (diag.get("evidence_lines") or []):
            line_lower = str(line).lower()
            if "ooc ratio" in line_lower:
                import re as _re
                m = _re.search(r"(\d+\.?\d*)\s*%?", str(line).split(":")[-1])
                if m:
                    try:
                        raw = float(m.group(1))
                        ooc_ratio = raw / 100.0 if raw > 1.0 else raw
                    except ValueError:
                        _log.warning(
                            "Unable to parse OOC ratio from evidence line: %r",
                            line,
                            exc_info=True,
                        )
                break
        if "cusum" in rule_id and (severity == "error" or (ooc_ratio is not None and ooc_ratio >= 0.10)):
            return "失控", feature or None, ooc_ratio

    # Pass 2: look for EWMA / shift / run → 警示
    for diag in diagnostics:
        if not isinstance(diag, dict):
            continue
        rule_id = str(diag.get("rule_id", "") or "").lower()
        severity = str(diag.get("severity", "") or "").lower()
        feature = str(diag.get("feature_label", "") or "").strip()
        if any(k in rule_id for k in ("ewma", "shift", "run", "drift")) or severity == "warning":
            return "警示", feature or None, None

    return "受控", None, None


def requires_immediate_action(
    risk_level: str,
    stability_verdict: str,
    error_count: int = 0,
) -> bool:
    """Return True if the batch requires immediate engineering action."""
    return (
        str(risk_level or "").upper() == "HIGH"
        or stability_verdict == "失控"
        or int(error_count or 0) >= 1
    )


def generate_one_liner(
    verdict: str,
    risk_level: str,
    stability_verdict: str,
    primary_feature: str = "",
    primary_rule_id: str = "",
) -> str:
    """
    Generate a single-sentence diagnostic conclusion for the Executive Summary.
    Priority order matches the engineering report requirement:
    capability-vs-stability conflict must be explicitly called out.
    """
    verdict_norm = normalize_process_verdict(verdict)
    risk_upper = str(risk_level or "").upper()
    feat = str(primary_feature or "").strip() or "量測特徵"
    atype = anomaly_type_label(primary_rule_id)

    # Scenario A: ability OK but stability out-of-control (critical conflict)
    if verdict_norm == "ACCEPTABLE" and stability_verdict == "失控" and risk_upper == "HIGH":
        return (
            f"{feat} 出現{atype}，能力指標雖可接受，"
            f"但製程穩定性失控，整體屬高風險，建議立即啟動調查。"
        )
    # Scenario B: all clear
    if verdict_norm == "ACCEPTABLE" and risk_upper == "LOW" and stability_verdict == "受控":
        return "本批製程穩定受控，能力充足，無需立即處置，維持常規監控。"
    # Scenario C: capability needs improvement
    if verdict_norm == "IMPROVEMENT":
        return (
            f"{feat} 製程能力需改善（Cpk 偏低），"
            f"建議確認製程參數並啟動短期改善計畫。"
        )
    # Scenario D: unacceptable
    if verdict_norm == "UNACCEPTABLE":
        return (
            f"{feat} 製程能力不可接受，本批存在重大品質風險，"
            f"建議立即停產調查並執行隔離。"
        )
    # Scenario E: stability warning only
    if stability_verdict == "警示":
        return (
            f"{feat} 出現{atype}警示訊號，"
            f"建議設定短期監控門檻並追蹤趨勢變化。"
        )
    # Scenario F: generic HIGH
    if risk_upper == "HIGH":
        return (
            f"本批製程出現高風險訊號（{atype}），"
            f"建議優先確認 {feat} 異常根因，必要時啟動調查。"
        )
    # Scenario G: MEDIUM
    if risk_upper == "MEDIUM":
        return (
            f"本批製程存在中風險警示（{feat} {atype}），"
            f"建議持續追蹤並評估是否需要調整製程參數。"
        )
    return "本批製程存在警示訊號，建議進一步觀察並持續追蹤。"


def generate_risk_sentence(
    verdict: str,
    risk_level: str,
    stability_verdict: str,
    normality_passed: bool = True,
    primary_feature: str = "",
) -> str:
    """
    Generate a combined risk verdict sentence that explicitly calls out
    the capability-vs-stability conflict per engineering report requirements.
    Example output:
      "製程能力可接受，但穩定性失控，分布偏離常態，
       因此整體仍屬高風險，建議啟動調查與追蹤。"
    """
    verdict_norm = normalize_process_verdict(verdict)
    risk_upper = str(risk_level or "").upper()

    cap_text = {
        "ACCEPTABLE": "製程能力可接受",
        "IMPROVEMENT": "製程能力需改善",
        "UNACCEPTABLE": "製程能力不可接受",
    }.get(verdict_norm, "製程能力未知")

    stability_text = {
        "失控": "但穩定性失控",
        "警示": "穩定性出現警示訊號",
        "受控": "製程穩定受控",
    }.get(stability_verdict, "製程穩定受控")

    normality_suffix = (
        "；分布偏離常態，能力指標可能低估實際風險"
        if not normality_passed else ""
    )

    risk_conclusion = {
        "HIGH": "因此整體仍屬高風險，建議啟動調查與追蹤。",
        "MEDIUM": "整體屬中風險，建議設定監控門檻，密切觀察趨勢。",
        "LOW": "整體風險低，維持常規 SPC 監控即可。",
    }.get(risk_upper, "請結合實際製程狀況判斷。")

    return f"{cap_text}，{stability_text}{normality_suffix}，{risk_conclusion}"


# ── SMT SPI process-state & problem-type classification ──────────────────────

def derive_process_state(
    diagnostics: Optional[List[Dict[str, Any]]] = None,
    stability_verdict: str = "受控",
) -> str:
    """
    Classify the overall SMT SPI process state for the diagnosis header.

    Returns one of:
      "穩定"     — no significant anomaly
      "警示"     — minor warning, not yet out-of-control
      "漂移"     — gradual systematic drift (CUSUM)
      "偏移"     — sudden step-change in mean (EWMA/shift)
      "局部群聚" — spatially clustered defects (component/area issue)
      "失控"     — multiple/severe OOC violations
    """
    if not isinstance(diagnostics, list) or not diagnostics:
        return "穩定" if stability_verdict == "受控" else "警示"

    has_cusum_error = any(
        "cusum" in str(d.get("rule_id", "")).lower()
        and str(d.get("severity", "")).lower() == "error"
        for d in diagnostics if isinstance(d, dict)
    )
    has_drift = any(
        any(k in str(d.get("rule_id", "")).lower() for k in ("cusum", "drift"))
        for d in diagnostics if isinstance(d, dict)
    )
    has_shift = any(
        any(k in str(d.get("rule_id", "")).lower() for k in ("shift", "ewma"))
        for d in diagnostics if isinstance(d, dict)
    )
    has_cluster = any(
        any(k in str(d.get("rule_id", "")).lower() for k in ("spatial", "cluster", "edge"))
        for d in diagnostics if isinstance(d, dict)
    )

    if stability_verdict == "失控" or has_cusum_error:
        return "失控"
    if has_drift:
        return "漂移"
    if has_shift:
        return "偏移"
    if has_cluster:
        return "局部群聚"
    if stability_verdict == "警示":
        return "警示"
    return "穩定"


def derive_problem_type(
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Classify the dominant problem type from primary diagnostic.

    Returns: "Drift" / "Shift" / "Cluster" / "Local" / "Global" / "Trend" / "Unknown"
    """
    if not isinstance(diagnostics, list) or not diagnostics:
        return "Unknown"
    primary_rule = str(
        (diagnostics[0] if diagnostics else {}).get("rule_id", "")
    ).lower()

    if "cusum" in primary_rule or "drift" in primary_rule:
        return "Drift"
    if "shift" in primary_rule or "ewma" in primary_rule:
        return "Shift"
    if "spatial" in primary_rule or "cluster" in primary_rule or "edge" in primary_rule:
        return "Cluster"
    if "run" in primary_rule:
        return "Trend"
    if "normal" in primary_rule or "normality" in primary_rule:
        return "Global"
    if "ooc" in primary_rule or "oos" in primary_rule:
        return "Local"
    return "Unknown"


_PROBLEM_TYPE_ZH: Dict[str, str] = {
    "Drift":   "漸進漂移 Drift",
    "Shift":   "突發偏移 Shift",
    "Cluster": "空間群聚 Cluster",
    "Local":   "局部異常 Local",
    "Global":  "全局偏移 Global",
    "Trend":   "趨勢變化 Trend",
    "Unknown": "型態未知",
}


def problem_type_zh(problem_type: str) -> str:
    """Return Chinese+English label for problem type."""
    return _PROBLEM_TYPE_ZH.get(problem_type, problem_type)


_PROCESS_STATE_SEVERITY: Dict[str, str] = {
    "穩定":     "ok",
    "警示":     "warning",
    "偏移":     "warning",
    "漂移":     "error",
    "局部群聚": "warning",
    "失控":     "error",
}


def process_state_severity(state: str) -> str:
    """Return ok / warning / error for a process state label."""
    return _PROCESS_STATE_SEVERITY.get(state, "warning")


# ── SMT SPI engineering narrative generator ───────────────────────────────────

_SPI_CAUSE_HINTS: Dict[str, List[str]] = {
    "Drift": [
        "鋼網磨損或開口逐漸堵塞",
        "刮刀壓力/速度隨時間偏移",
        "錫膏黏度因溫濕度漂移而改變",
        "PCB 支撐治具鬆動造成漸進下沉",
    ],
    "Shift": [
        "錫膏批次更換或開封後特性變化",
        "鋼網更換（新舊鋼網厚度/開口差異）",
        "設備保養或配方變更後未重新驗證",
        "作業人員換班後操作條件改變",
    ],
    "Cluster": [
        "鋼網特定區域開口堵塞或變形",
        "PCB 翹曲導致局部印刷壓力不均",
        "治具夾持問題造成特定位置離版不良",
        "元件在 PCB 邊緣受刮刀力學影響",
    ],
    "Trend": [
        "製程中某個參數在批次間持續單向變化",
        "環境條件（溫濕度）在生產期間持續改變",
    ],
    "Local": [
        "特定 RefDes/Pad 的開口問題",
        "個別元件位置的量測偏差",
    ],
    "Global": [
        "整批錫膏分布異常，可能為材料批次問題",
        "全板印刷條件異常（配方設定錯誤）",
    ],
}

_SPI_STATE_LEAD: Dict[str, str] = {
    "失控":     "{feat} 的印刷製程已失控，OOC 比例極高，製程中心持續偏移，屬系統性異常而非隨機波動。",
    "漂移":     "{feat} 的印刷體積/高度呈系統性漂移，製程中心已偏離目標，且漂移持續累積。",
    "偏移":     "{feat} 出現突發性均值偏移，製程在某個時間點發生了明顯改變。",
    "局部群聚": "{feat} 呈現空間群聚異常，問題集中於 PCB 特定區域或元件，具有位置相依性。",
    "警示":     "{feat} 出現製程警示訊號，尚未失控但趨勢需要密切關注。",
    "穩定":     "{feat} 製程目前穩定受控，無顯著漂移或偏移訊號。",
}

_SPI_RISK_CONSEQUENCE: Dict[str, str] = {
    "HIGH":   "若不即時介入，後續批次不合格風險將持續升高，建議立即查明根因。",
    "MEDIUM": "目前尚未對產品品質造成立即影響，但應在本批結束前完成原因確認。",
    "LOW":    "製程狀態良好，維持現有管控條件，下批前確認無異常即可。",
}


def generate_spi_narrative(
    process_state: str,
    problem_type: str,
    primary_feature: str,
    risk_level: str,
    ooc_ratio: Optional[float] = None,
) -> str:
    """
    Generate a 2-3 sentence SMT SPI engineering narrative.
    Translates statistical findings into actionable process-language.
    """
    feat = str(primary_feature or "量測特徵").strip()
    risk_upper = str(risk_level or "").upper()

    # Sentence 1: process state lead
    lead_template = _SPI_STATE_LEAD.get(process_state, _SPI_STATE_LEAD["警示"])
    sentence1 = lead_template.format(feat=feat)

    # Add OOC quantification if available
    if ooc_ratio is not None and ooc_ratio >= 0.10:
        pct = ooc_ratio * 100 if ooc_ratio <= 1.0 else ooc_ratio
        sentence1 += f"（OOC 比例：{pct:.0f}%）"

    # Sentence 2: possible causes hint
    causes = _SPI_CAUSE_HINTS.get(problem_type, [])
    if causes:
        sentence2 = f"常見可能原因包括：{causes[0]}、{causes[1]}。" if len(causes) >= 2 else f"常見可能原因：{causes[0]}。"
    else:
        sentence2 = "建議確認鋼網、刮刀、錫膏及設備參數是否有異常變化。"

    # Sentence 3: risk consequence
    sentence3 = _SPI_RISK_CONSEQUENCE.get(risk_upper, "請依現場情況進行評估與追蹤。")

    return f"{sentence1}\n{sentence2}\n{sentence3}"
