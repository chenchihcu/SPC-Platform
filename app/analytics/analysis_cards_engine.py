"""Analysis-card engines for OOC/Shift/Drift/Outlier summaries."""

from __future__ import annotations

from typing import Any, Dict, List
from app.utils.numeric_utils import safe_float


def _safe_float(value: Any) -> float | None:
    return safe_float(value)


def _normalize_ooc_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator / denominator)


def compute_ooc_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    spc = payload.get("spc") or {}
    data = spc.get("data") or {}
    stats = spc.get("statistics") or {}
    ooc = list(data.get("out_of_control_indices") or [])
    n = int(stats.get("n") or len(data.get("values") or []) or 0)
    ratio = _normalize_ooc_ratio(len(ooc), n)
    severity = "Normal"
    if ratio is not None:
        if ratio >= 0.1:
            severity = "Alarm"
        elif ratio > 0:
            severity = "Warning"
    return {
        "chart_type": "OOCAnalysis",
        "data": {
            "ooc_count": len(ooc),
            "n": n,
            "ooc_ratio": ratio,
            "severity": severity,
            "summary_lines": [
                f"OOC Count: {len(ooc)} / {n}" if n else "OOC Count: UNKNOWN/VERIFY",
                f"OOC Ratio: {ratio:.1%}" if ratio is not None else "OOC Ratio: UNKNOWN/VERIFY",
                "Threshold: warning > 0%, alarm >= 10%",
            ],
        },
        "statistics": {"ooc_count": len(ooc), "n": n, "ooc_ratio": ratio},
        "metadata": {"is_valid": True, "error": ""},
    }


def compute_shift_detection(payload: Dict[str, Any]) -> Dict[str, Any]:
    cusum = payload.get("cusum") or {}
    cusum_stats = cusum.get("statistics") or {}
    cusum_data = cusum.get("data") or {}
    n = int(cusum_stats.get("n") or 0)
    ooc_count = int(cusum_stats.get("ooc_count") or len(cusum_data.get("out_of_control_indices") or []))
    ratio = _normalize_ooc_ratio(ooc_count, n)
    level = "None"
    if ratio is not None:
        if ratio >= 0.1:
            level = "Persistent Shift"
        elif ratio > 0:
            level = "Local Shift"
    return {
        "chart_type": "ShiftDetection",
        "data": {
            "shift_level": level,
            "ooc_count": ooc_count,
            "n": n,
            "ooc_ratio": ratio,
            "summary_lines": [
                f"Shift Level: {level}",
                f"CUSUM OOC: {ooc_count}/{n}" if n else "CUSUM OOC: UNKNOWN/VERIFY",
                f"CUSUM OOC Ratio: {ratio:.1%}" if ratio is not None else "CUSUM OOC Ratio: UNKNOWN/VERIFY",
            ],
        },
        "statistics": {"ooc_count": ooc_count, "n": n, "ooc_ratio": ratio},
        "metadata": {"is_valid": True, "error": ""},
    }


def compute_drift_detection(payload: Dict[str, Any]) -> Dict[str, Any]:
    ewma = payload.get("ewma") or {}
    data = ewma.get("data") or {}
    stats = ewma.get("statistics") or {}
    values_raw = data.get("values") or []
    values: List[float] = []
    for v in values_raw:
        fv = safe_float(v)
        if fv is not None:
            values.append(fv)
    if not values:
        return {
            "chart_type": "DriftDetection",
            "data": {},
            "statistics": {},
            "metadata": {"is_valid": False, "error": "缺少 EWMA 資料。"},
        }
    cl = _safe_float(stats.get("cl"))
    drift = None
    if cl is not None:
        drift = float(max(abs(v - cl) for v in values))
    trend = "Stable"
    if drift is not None and cl is not None:
        denom = abs(cl) if abs(cl) > 1e-9 else 1.0
        rel = drift / denom
        if rel >= 0.2:
            trend = "Alarm Drift"
        elif rel >= 0.1:
            trend = "Warning Drift"
    return {
        "chart_type": "DriftDetection",
        "data": {
            "drift_abs": drift,
            "cl": cl,
            "trend_level": trend,
            "summary_lines": [
                f"Drift Level: {trend}",
                f"Max |EWMA-CL|: {drift:.4f}" if drift is not None else "Max |EWMA-CL|: UNKNOWN/VERIFY",
                f"Center Line: {cl:.4f}" if cl is not None else "Center Line: UNKNOWN/VERIFY",
            ],
        },
        "statistics": {"drift_abs": drift, "cl": cl},
        "metadata": {"is_valid": True, "error": ""},
    }


def compute_outlier_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    bivariate = payload.get("bivariate_outlier") or {}
    data = bivariate.get("data") or {}
    is_outlier = list(data.get("is_outlier") or [])
    if is_outlier:
        total = len(is_outlier)
        outlier_count = int(sum(1 for x in is_outlier if bool(x)))
    else:
        # Fallback: when dual-feature outlier input is unavailable, use SPC OOC count as proxy.
        spc = payload.get("spc") or {}
        spc_data = spc.get("data") or {}
        spc_stats = spc.get("statistics") or {}
        outlier_idx = list(spc_data.get("out_of_control_indices") or [])
        total = int(spc_stats.get("n") or len(spc_data.get("values") or []) or 0)
        outlier_count = len(outlier_idx)
    ratio = _normalize_ooc_ratio(outlier_count, total)
    rank = "Normal"
    if ratio is not None:
        if ratio >= 0.1:
            rank = "Alarm"
        elif ratio > 0.03:
            rank = "Warning"
    return {
        "chart_type": "OutlierAnalysis",
        "data": {
            "outlier_count": outlier_count,
            "total_n": total,
            "outlier_ratio": ratio,
            "level": rank,
            "summary_lines": [
                f"Outlier Level: {rank}",
                f"Outliers: {outlier_count}/{total}" if total else "Outliers: UNKNOWN/VERIFY",
                f"Outlier Ratio: {ratio:.1%}" if ratio is not None else "Outlier Ratio: UNKNOWN/VERIFY",
            ],
        },
        "statistics": {"outlier_count": outlier_count, "n": total, "outlier_ratio": ratio},
        "metadata": {"is_valid": True, "error": ""},
    }
