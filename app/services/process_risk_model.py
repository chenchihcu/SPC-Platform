"""
Process risk = f(Capability, Stability, Distribution) with short Chinese rationale.

Complements diagnostic severity counts in report_risk; does not replace them.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


def _tier_cpk(cpk: Optional[float]) -> int:
    if cpk is None:
        return 1
    if cpk < 1.0:
        return 2
    if cpk < 1.33:
        return 1
    return 0


def _tier_ooc(ooc_ratio: Optional[float]) -> int:
    if ooc_ratio is None:
        return 0
    if ooc_ratio >= 0.05:
        return 2
    if ooc_ratio > 0:
        return 1
    return 0


def _tier_distribution(
    shape: str,
    is_normal: Optional[bool],
    bimodal: Optional[bool],
) -> int:
    if bimodal is True:
        return 2
    if shape in ("Bimodal", "Non-normal"):
        return 2
    if is_normal is False:
        return 1
    return 0


def compute_process_risk(
    statistical_signals: Dict[str, Any],
    diagnosis_engine: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Triad-based risk with rationale_zh for PPTX / decision layer.

    When capability is OK but stability or distribution is poor → elevated risk
    (per engineering interpretation; not a single Cpk gate).
    """
    cap_agg = (statistical_signals.get("capabilities") or {}).get("aggregate") or {}
    min_cpk = cap_agg.get("min_cpk")
    try:
        cpk_f = float(min_cpk) if min_cpk is not None else None
    except (TypeError, ValueError):
        cpk_f = None

    stab = statistical_signals.get("stability") or {}
    ooc_ratio = stab.get("ooc_ratio")
    try:
        ooc_f = float(ooc_ratio) if ooc_ratio is not None else None
    except (TypeError, ValueError):
        ooc_f = None

    dist_sig = statistical_signals.get("distribution") or {}
    is_normal = dist_sig.get("is_normal")
    bimodal = dist_sig.get("bimodal_hint")
    shape = str(diagnosis_engine.get("distribution_shape") or "Normal")

    tc = _tier_cpk(cpk_f)
    ts = _tier_ooc(ooc_f)
    td = _tier_distribution(shape, is_normal if isinstance(is_normal, bool) else None, bimodal if isinstance(bimodal, bool) else None)

    score = tc + ts + td
    patterns = diagnosis_engine.get("process_patterns") or []
    if isinstance(patterns, list) and "Drift" in patterns:
        score += 1
    scope = str(diagnosis_engine.get("scope") or "Global")
    if scope in ("Local", "Component"):
        score += 0

    if score >= 5 or tc >= 2:
        level: RiskLevel = "HIGH"
    elif score >= 2:
        level = "MEDIUM"
    else:
        level = "LOW"

    rationale_parts: List[str] = []
    if tc >= 2:
        rationale_parts.append("製程能力不足（Cpk 偏低），不良風險高。")
    elif tc == 1:
        rationale_parts.append("能力尚可但未達標竿區間，建議持續監控。")
    if ts >= 2:
        rationale_parts.append("管制圖 OOC 比例偏高，穩定性不足。")
    elif ts == 1:
        rationale_parts.append("出現零星 OOC，需確認是否為可歸因原因。")
    if td >= 2:
        rationale_parts.append("分布呈雙峰或非常態，顯示可能混線或異常製程狀態。")
    elif td == 1:
        rationale_parts.append("常態性檢定拒絕，分布與假設有差異。")
    if "Drift" in (patterns if isinstance(patterns, list) else []):
        rationale_parts.append("存在漂移訊號，屬系統性變化風險。")
    if not rationale_parts:
        rationale_parts.append("綜合能力、穩定性與分布訊號，目前風險可控。")

    return {
        "level": level,
        "score": int(score),
        "dimensions": {
            "capability_tier": tc,
            "stability_tier": ts,
            "distribution_tier": td,
            "min_cpk": cpk_f,
            "ooc_ratio": ooc_f,
            "distribution_shape": shape,
        },
        "rationale_zh": "".join(rationale_parts),
    }


def merge_risk_level(
    diagnostic_level: str,
    triad_level: str,
) -> str:
    """Combine PPTX diagnostic-based level with triad level (max severity)."""
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    a = order.get(str(diagnostic_level).upper().replace(" ", ""), 0)
    b = order.get(str(triad_level).upper().replace(" ", ""), 0)
    mx = max(a, b)
    return "HIGH" if mx >= 2 else "MEDIUM" if mx == 1 else "LOW"
