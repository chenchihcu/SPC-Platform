"""
Structured SPI knowledge inference (Steps 1–6) aligned with statistical_signals + diagnosis_engine.

Uses the same JSON bundle as multi_signal_diagnosis; does not re-parse Excel at runtime.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

INFERENCE_SCHEMA_VERSION = "1.0.0"

# Vol–Area / Vol–Height correlation hints (absolute value thresholds, engineering default)
_CORR_STRONG = 0.55


def _corr_strength(x: Optional[float]) -> str:
    if x is None:
        return "unknown"
    ax = abs(float(x))
    if ax >= _CORR_STRONG:
        return "strong"
    if ax >= 0.35:
        return "moderate"
    return "weak"


def _dfm_hint(scope: str, l4: Dict[str, Any], *, total_oos_fallback: int) -> str:
    raw = (l4 or {}).get("total_oos_count")
    total_oos = int(raw) if raw is not None else int(total_oos_fallback)
    top = l4.get("top_oos_refdes") or []
    share = 0.0
    if isinstance(top, list) and top and total_oos > 0:
        try:
            share = int(top[0].get("oos_count", 0)) / float(total_oos)
        except (TypeError, ValueError, ZeroDivisionError):
            share = 0.0
    if scope in ("Component", "Local") and (share >= 0.5 or total_oos > 0):
        return "DFM_preferred"
    return "process"


def run_knowledge_inference(
    statistical_signals: Dict[str, Any],
    diagnosis_engine: Dict[str, Any],
    summary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Steps 1–6 snapshot for reports and downstream narrative.

    Step 4 maps correlation triples to stencil / squeegee / support hints (qualitative).
    """
    sum_d: Dict[str, Any] = summary if isinstance(summary, dict) else {}
    process: Dict[str, Any] = sum_d["process"] if isinstance(sum_d.get("process"), dict) else {}
    layers: Dict[str, Any] = (
        process["dashboard_layers"] if isinstance(process.get("dashboard_layers"), dict) else {}
    )
    l4: Dict[str, Any] = (
        layers["layer_4_defect_structure"]
        if isinstance(layers.get("layer_4_defect_structure"), dict)
        else {}
    )
    l5: Dict[str, Any] = (
        layers["layer_5_spec_analysis"] if isinstance(layers.get("layer_5_spec_analysis"), dict) else {}
    )
    l7: Dict[str, Any] = (
        layers["layer_7_engineering_info"] if isinstance(layers.get("layer_7_engineering_info"), dict) else {}
    )

    scope = str(diagnosis_engine.get("scope") or "Global")
    patterns = diagnosis_engine.get("process_patterns") or []
    dist_shape = str(diagnosis_engine.get("distribution_shape") or "Normal")

    corr: Dict[str, Any] = (
        statistical_signals["correlation"]
        if isinstance(statistical_signals.get("correlation"), dict)
        else {}
    )
    c_va = corr.get("corr_vol_area")
    c_vh = corr.get("corr_vol_height")
    c_ah = corr.get("corr_area_height")

    step4: Dict[str, Any] = {
        "corr_vol_area": c_va,
        "corr_vol_height": c_vh,
        "corr_area_height": c_ah,
        "vol_area_strength": _corr_strength(float(c_va)) if c_va is not None else "unknown",
        "vol_height_strength": _corr_strength(float(c_vh)) if c_vh is not None else "unknown",
        "qualitative_hints_zh": [],
    }
    hints: List[str] = []
    if c_va is not None and abs(float(c_va)) >= _CORR_STRONG:
        hints.append("Volume–Area 高度相關：優先檢視鋼網開口／aperture 與轉印面積設計（IPC-7525 / land pattern）。")
    if c_vh is not None and abs(float(c_vh)) >= _CORR_STRONG:
        hints.append("Volume–Height 高度相關：優先檢視刮刀壓力、脫模與錫膏黏度（製程參數）。")
    if c_ah is not None and abs(float(c_ah)) < 0.25 and (patterns and "VariationIncrease" in patterns):
        hints.append("高度變異與面積脫鉤時，留意 PCB 支撐／翹曲與印刷間隙。")
    step4["qualitative_hints_zh"] = hints

    oos_n = int(l5.get("oos_count") or 0)
    hypo = _dfm_hint(scope, l4, total_oos_fallback=oos_n)
    step5_causes: List[str] = []
    for p in patterns if isinstance(patterns, list) else []:
        step5_causes.append(str(p))
    step6_processes: List[str] = ["Stencil", "Squeegee", "Solder Paste", "PCB", "Alignment", "Environment"]
    if hypo == "DFM_preferred":
        step6_processes = ["PCB", "Stencil", "Alignment", "Squeegee", "Solder Paste", "Environment"]

    return {
        "schema_version": INFERENCE_SCHEMA_VERSION,
        "hypothesis_domain": hypo,
        "steps": {
            "1_scope": scope,
            "2_patterns": patterns,
            "3_distribution": dist_shape,
            "4_correlation": step4,
            "5_pattern_tags": step5_causes,
            "6_process_family_order": step6_processes,
        },
        "height_std_hint": l7.get("std"),
        "notes": "Qualitative; confirm with SPI_製程對應知識庫_v1 JSON rules in multi_signal_diagnosis.",
    }
