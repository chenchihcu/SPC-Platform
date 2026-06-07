"""
Process diagnosis DTO: pattern / scope / distribution shape + explainable pattern_logic.

Heuristic mapping layered on summary.dashboard_layers and statistical_signals;
does not override SPC_RULES.md formulas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, cast
from app.analytics.ooc_utils import first_group_share

DIAGNOSIS_ENGINE_SCHEMA_VERSION = "1.0.0"

ProcessPattern = Literal[
    "Drift",
    "Shift",
    "LocalIssue",
    "ComponentIssue",
    "VariationIncrease",
    "Mixing",
    "AlignmentIssue",
    "CapabilityIssue",
]

Scope = Literal["Global", "Local", "Component"]

DistributionShape = Literal["Normal", "Skew", "Bimodal", "Non-normal"]


def _scope_from_layers(l4: Dict[str, Any], total_oos: int) -> Scope:
    dpat = str(l4.get("defect_pattern") or "")
    top_r = l4.get("top_oos_refdes") or []
    share = first_group_share(list(top_r) if isinstance(top_r, list) else [], total_oos)
    cluster_ratio = _safe_float(l4.get("cluster_ratio"))
    if dpat in ("same_component",) or (share is not None and share >= 0.5):
        return "Component"
    if dpat in ("same_location", "same_panel_area", "step_stencil_area", "local_cluster") or (
        cluster_ratio is not None and cluster_ratio > 0.05
    ):
        return "Local"
    return "Global"


def _distribution_shape(sig_dist: Dict[str, Any], layer5: Dict[str, Any]) -> DistributionShape:
    if sig_dist.get("bimodal_hint") is True:
        return "Bimodal"
    if sig_dist.get("is_normal") is False:
        return "Non-normal"
    if sig_dist.get("is_normal") is True:
        return "Normal"
    verdict = str(layer5.get("spec_tightness_level") or "")
    if verdict == "improvement_needed":
        return "Non-normal"
    return "Normal"


def _patterns_from_signals_and_layers(
    signals: Dict[str, Any],
    l1: Dict[str, Any],
    l8: Dict[str, Any],
    l5: Dict[str, Any],
) -> List[ProcessPattern]:
    out: List[ProcessPattern] = []
    drift: Dict[str, Any] = signals["drift"] if isinstance(signals.get("drift"), dict) else {}
    stab: Dict[str, Any] = signals["stability"] if isinstance(signals.get("stability"), dict) else {}
    dist: Dict[str, Any] = signals["distribution"] if isinstance(signals.get("distribution"), dict) else {}
    spat: Dict[str, Any] = signals["spatial"] if isinstance(signals.get("spatial"), dict) else {}
    cusum_peak_ratio = _safe_float(drift.get("cusum_peak_ratio"))
    max_drift_ratio = _safe_float(l1.get("max_drift_ratio"))
    ooc_ratio = _safe_float(stab.get("ooc_ratio"))
    cluster_ratio = _safe_float(spat.get("cluster_ratio"))

    if drift.get("ewma_trend") and str(drift.get("ewma_trend")).startswith("Alarm"):
        out.append("Drift")
    elif cusum_peak_ratio is not None and cusum_peak_ratio >= 0.8:
        out.append("Drift")
    elif max_drift_ratio is not None and max_drift_ratio >= 0.5:
        out.append("Drift")

    if ooc_ratio is not None and ooc_ratio > 0 and "Drift" not in out:
        out.append("Shift")

    if cluster_ratio is not None and cluster_ratio > 0.05:
        out.append("LocalIssue")

    issue = str(l8.get("issue_type") or "")
    if issue in ("local_cluster", "step_stencil"):
        out.append("LocalIssue")
    if issue in ("variation_too_large", "variation_problem"):
        out.append("VariationIncrease")
    if issue == "process_offset":
        out.append("AlignmentIssue")
    _cpk = _safe_float(l5.get("cpk"))
    if issue in ("variation_problem",) or (_cpk is not None and _cpk < 1.0):
        out.append("CapabilityIssue")

    if dist.get("bimodal_hint") is True or dist.get("is_normal") is False:
        if "Mixing" not in out:
            out.append("Mixing")

    # Deduplicate preserving order
    seen: set[str] = set()
    uniq: List[ProcessPattern] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    if not uniq:
        legacy_map: Dict[str, ProcessPattern] = {
            "process_center_shift": "Shift",
            "variation_too_large": "VariationIncrease",
            "local_cluster": "LocalIssue",
            "step_stencil": "LocalIssue",
            "process_offset": "AlignmentIssue",
            "variation_problem": "CapabilityIssue",
            "spec_too_tight": "CapabilityIssue",
            "mixed": "VariationIncrease",
        }
        it = str(l8.get("issue_type") or "")
        if it in legacy_map:
            uniq.append(legacy_map[it])
        elif (_safe_float(l5.get("cpk")) or 99) < 1.33:
            uniq.append(cast(ProcessPattern, "CapabilityIssue"))
    return uniq


def _safe_float(x: Any) -> Optional[float]:
    from app.utils.numeric_utils import safe_float
    return safe_float(x)


def build_diagnosis_engine(
    statistical_signals: Dict[str, Any],
    summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Build diagnosis_engine DTO for dashboard and reports."""
    sum_d: Dict[str, Any] = summary if isinstance(summary, dict) else {}
    process: Dict[str, Any] = sum_d["process"] if isinstance(sum_d.get("process"), dict) else {}
    layers: Dict[str, Any] = (
        process["dashboard_layers"] if isinstance(process.get("dashboard_layers"), dict) else {}
    )
    l1: Dict[str, Any] = layers["layer_1_alarm"] if isinstance(layers.get("layer_1_alarm"), dict) else {}
    l4: Dict[str, Any] = (
        layers["layer_4_defect_structure"]
        if isinstance(layers.get("layer_4_defect_structure"), dict)
        else {}
    )
    l5: Dict[str, Any] = (
        layers["layer_5_spec_analysis"] if isinstance(layers.get("layer_5_spec_analysis"), dict) else {}
    )
    l8: Dict[str, Any] = (
        layers["layer_8_diagnosis"] if isinstance(layers.get("layer_8_diagnosis"), dict) else {}
    )

    total_oos = int(l5.get("oos_count") or 0)
    scope = _scope_from_layers(l4, total_oos)
    sig_dist: Dict[str, Any] = (
        statistical_signals["distribution"]
        if isinstance(statistical_signals.get("distribution"), dict)
        else {}
    )
    dist_shape = _distribution_shape(sig_dist, l5)
    patterns = _patterns_from_signals_and_layers(statistical_signals, l1, l8, l5)

    parts = [
        f"Scope={scope}",
        f"Distribution={dist_shape}",
        f"Patterns={','.join(patterns) if patterns else '—'}",
    ]
    if statistical_signals.get("drift"):
        parts.append(
            f"DriftSignals(ewma={((statistical_signals.get('drift') or {}).get('ewma_trend'))},cusum_r={((statistical_signals.get('drift') or {}).get('cusum_peak_ratio'))})"
        )
    if statistical_signals.get("stability"):
        parts.append(f"OOC_ratio={((statistical_signals.get('stability') or {}).get('ooc_ratio'))}")
    pattern_logic = "；".join(parts)

    return {
        "schema_version": DIAGNOSIS_ENGINE_SCHEMA_VERSION,
        "process_patterns": patterns,
        "primary_pattern": patterns[0] if patterns else None,
        "scope": scope,
        "distribution_shape": dist_shape,
        "pattern_logic": pattern_logic,
        "legacy_issue_type": l8.get("issue_type"),
        "legacy_layer_8": {
            "root_cause_zh": l8.get("root_cause_zh"),
            "recommended_action_zh": l8.get("recommended_action_zh"),
            "priority": l8.get("priority"),
        },
    }
