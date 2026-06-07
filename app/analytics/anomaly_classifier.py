"""
Anomaly classifier: maps SPC patterns, heatmap clustering, correlation and trend
to suggested failure modes or labels for engineering diagnostics.
Reads from analysis payload only; does not modify import/report pipeline.
"""
from typing import Dict, Any, List


def classify_anomalies(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Classify process anomalies using SPC, heatmap, correlation and trend from payload.
    Returns list of { label, confidence, indicators, suggested_failure_mode_id }.
    """
    if not payload:
        return []
    suggestions: List[Dict[str, Any]] = []
    spc = payload.get("spc") or {}
    spatial = payload.get("spatial") or {}
    run_chart = payload.get("run_chart") or {}
    statistics = spc.get("statistics", {})
    ooc = (spc.get("data") or {}).get("out_of_control_indices", [])
    n_ooc = len(ooc) if ooc else 0
    n = statistics.get("n") or 0
    if n > 0 and n_ooc / n > 0.05:
        suggestions.append({
            "label": "管制界線違反偏高",
            "confidence": min(0.9, 0.5 + n_ooc / n),
            "indicators": ["I-MR OOC rate"],
            "suggested_failure_mode_id": "instability",
        })
    modes = (spatial.get("modes") or {}).get("oos_density", {})
    oos_vals = modes.get("values", [])
    if oos_vals and sum(oos_vals) > 0:
        suggestions.append({
            "label": "空間 OOS 聚集",
            "confidence": 0.7,
            "indicators": ["spatial OOS density"],
            "suggested_failure_mode_id": "spatial_oos",
        })

    # Paste drying risk: volume decreasing along board sequence (run chart trend)
    run_data = run_chart.get("data", {})
    values = run_data.get("values", [])
    if isinstance(values, list) and len(values) >= 10:
        third = max(1, len(values) // 3)
        first_third_mean = sum(values[:third]) / third
        last_third_mean = sum(values[-third:]) / third
        if first_third_mean > 0 and last_third_mean < first_third_mean * 0.95:
            suggestions.append({
                "label": "Volume 隨板序下降，疑似錫膏乾涸",
                "confidence": 0.7,
                "indicators": ["run chart decline"],
                "suggested_failure_mode_id": "paste_drying",
            })

    # Footprint variance imbalance: large spread difference across same footprint / RefDes groups
    box_stats = (
        (payload.get("box") or {})
        .get("statistics", {})
        .get("variance_by_label", {})
    )
    if isinstance(box_stats, dict) and len(box_stats) >= 2:
        vars_list = [v for v in box_stats.values() if isinstance(v, (int, float)) and v >= 0]
        if len(vars_list) >= 2:
            max_var = max(vars_list)
            min_var = min(vars_list)
            if min_var > 0 and max_var > 2 * min_var:
                suggestions.append({
                    "label": "同足印/元件位置間變異差異大",
                    "confidence": 0.6,
                    "indicators": ["footprint variance imbalance"],
                    "suggested_failure_mode_id": "aperture_mismatch",
                })

    return suggestions
