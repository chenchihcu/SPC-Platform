"""Combination evidence matrix for SMT SPI process diagnosis.

This module is a presentation/diagnosis aggregation layer.  It does not compute
SPC formulas or chart payloads; it expands the available chart registry into
feature/chart candidates, then summarizes existing payload evidence.
"""

from __future__ import annotations

from itertools import combinations
from math import isfinite
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app.analytics.chart_registry import (
    CHART_CATALOG,
    CHART_NEXT_STEP_BY_ID,
    CHART_ORDER,
    CHART_UI_GROUP_BY_ID,
    get_chart_display_name,
)
from app.services import multi_signal_diagnosis as _msd

DIAGNOSTIC_EVIDENCE_MATRIX_SCHEMA_VERSION = "1.0.0"

Availability = str
EvidenceState = str
Severity = str

STATUS_ANALYZED = "analyzed"
STATUS_AVAILABLE_NOT_SELECTED = "available-not-selected"
STATUS_UNAVAILABLE = "unavailable"
STATUS_NOT_APPLICABLE = "not-applicable"
STATUS_MISSING_DATA = "missing-data"

STATE_SUPPORT = "support"
STATE_REFUTE = "refute"
STATE_NEUTRAL = "neutral"
STATE_UNAVAILABLE = "unavailable"

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"

DIMENSION_ORDER = [
    "capability_risk",
    "center_shift",
    "variation",
    "stability_drift",
    "local_cluster",
    "distribution",
    "multi_feature_correlation",
    "data_confidence",
]

DIMENSION_LABELS = {
    "capability_risk": "能力/規格風險",
    "center_shift": "中心偏移",
    "variation": "變異放大",
    "stability_drift": "穩定性/漂移",
    "local_cluster": "局部/群聚",
    "distribution": "分布異常",
    "multi_feature_correlation": "多特徵連動",
    "data_confidence": "資料信心",
}

STATUS_LABELS = {
    STATUS_ANALYZED: "已分析",
    STATUS_AVAILABLE_NOT_SELECTED: "可用未選",
    STATUS_UNAVAILABLE: "不可用",
    STATUS_NOT_APPLICABLE: "不適用",
    STATUS_MISSING_DATA: "缺資料",
}

STATE_LABELS = {
    STATE_SUPPORT: "支持",
    STATE_REFUTE: "不支持此假設",
    STATE_NEUTRAL: "中性",
    STATE_UNAVAILABLE: "資料不足/不可判讀",
}

READABLE_TAB_KEYS = (
    "overview",
    "combination_matrix",
    "evidence_matrix",
    "correlation",
    "chart_linkage",
    "actions",
    "data_context",
)

READABLE_STATE_LABELS = {
    STATE_SUPPORT: "支持此假設",
    STATE_REFUTE: "不支持此假設",
    STATE_NEUTRAL: "尚未形成明確判斷",
    STATE_UNAVAILABLE: "資料不足/不可判讀",
}

SEVERITY_SCORE = {SEVERITY_INFO: 0, SEVERITY_WARNING: 1, SEVERITY_ERROR: 2}

DUAL_CHART_IDS = {
    "scatter_spec",
    "correlation_matrix",
    "correlation_heatmap",
    "quadrant",
    "bivariate_outlier",
}

TRIPLE_CHART_IDS = {
    "anomaly_3f",
    "consistency_3f",
    "parallel_coord",
    "pass_fail_matrix",
    "imr_3f",
    "run_chart_3f",
    "ewma_3f",
    "cusum_3f",
    "boxplot_3f",
}

PAYLOAD_KEY_BY_CHART: Dict[str, Tuple[str, ...]] = {}
for _entry in CHART_CATALOG:
    _cid = str(_entry.get("id") or "")
    _raw_key = _entry.get("payload_key")
    if isinstance(_raw_key, tuple):
        PAYLOAD_KEY_BY_CHART[_cid] = tuple(str(k) for k in _raw_key)
    elif _raw_key:
        PAYLOAD_KEY_BY_CHART[_cid] = (str(_raw_key),)

PAYLOAD_KEY_BY_CHART.update(
    {
        "imr": ("spc",),
        "histogram_spec": ("cap", "dist"),
        "boxplot": ("box",),
        "spatial_heatmap": ("spatial",),
    }
)

CHART_DIMENSIONS: Dict[str, Tuple[str, ...]] = {
    "histogram_spec": ("capability_risk", "distribution"),
    "pass_fail_matrix": ("capability_risk",),
    "normality": ("distribution",),
    "boxplot": ("variation",),
    "boxplot_3f": ("variation",),
    "imr": ("stability_drift",),
    "xbar_r": ("stability_drift", "center_shift"),
    "ooc_analysis": ("stability_drift",),
    "shift_detection": ("center_shift",),
    "drift_detection": ("stability_drift",),
    "run_chart": ("stability_drift",),
    "ewma": ("stability_drift", "center_shift"),
    "cusum": ("stability_drift",),
    "pattern_recognition": ("stability_drift",),
    "imr_3f": ("stability_drift",),
    "run_chart_3f": ("stability_drift",),
    "ewma_3f": ("stability_drift", "center_shift"),
    "cusum_3f": ("stability_drift",),
    "pareto": ("local_cluster",),
    "spatial_heatmap": ("local_cluster",),
    "repeated_offender": ("local_cluster",),
    "outlier_analysis": ("local_cluster",),
    "anomaly_3f": ("local_cluster", "multi_feature_correlation"),
    "consistency_3f": ("multi_feature_correlation",),
    "scatter_spec": ("multi_feature_correlation",),
    "correlation_matrix": ("multi_feature_correlation",),
    "correlation_heatmap": ("multi_feature_correlation",),
    "quadrant": ("multi_feature_correlation",),
    "bivariate_outlier": ("multi_feature_correlation", "local_cluster"),
    "parallel_coord": ("multi_feature_correlation",),
    "density": ("distribution",),
    "subgroup": ("variation",),
    "anova_parttype": ("variation",),
}


def _safe_float(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(out):
        return None
    return out


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _selected_features(payload: Mapping[str, Any]) -> List[str]:
    raw = payload.get("selected_features")
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def _chart_arity(chart_id: str) -> int:
    if chart_id in DUAL_CHART_IDS:
        return 2
    if chart_id in TRIPLE_CHART_IDS:
        return 3
    return 1


def _candidate_feature_sets(chart_id: str, selected_features: Sequence[str]) -> List[Tuple[str, ...]]:
    arity = _chart_arity(chart_id)
    selected = tuple(selected_features)
    if arity == 1:
        return [(feature,) for feature in selected] if selected else [()]
    if len(selected) < arity:
        return [selected]
    if arity == 2:
        return [tuple(pair) for pair in combinations(selected, 2)]
    return [selected[:3]]


def _is_applicable(chart_id: str, selected_features: Sequence[str]) -> bool:
    return len(selected_features) >= _chart_arity(chart_id)


def _path_get(mapping: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = mapping
    for part in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _pair_keys(feature_set: Sequence[str]) -> List[str]:
    if len(feature_set) != 2:
        return []
    a, b = feature_set[0], feature_set[1]
    return [f"{a}+{b}", f"{b}+{a}"]


def _payload_keys(chart_id: str) -> Tuple[str, ...]:
    return PAYLOAD_KEY_BY_CHART.get(chart_id, (chart_id,))


def _payload_status(value: Any) -> Tuple[Availability, str]:
    if value is None:
        return STATUS_MISSING_DATA, "payload missing"
    if not isinstance(value, dict):
        return STATUS_ANALYZED, ""
    if not value:
        return STATUS_MISSING_DATA, "payload empty"
    metadata = value.get("metadata")
    if isinstance(metadata, dict) and metadata.get("is_valid") is False:
        return STATUS_UNAVAILABLE, str(metadata.get("error") or "payload invalid")
    return STATUS_ANALYZED, ""


def _resolve_candidate_payload(
    payload: Mapping[str, Any],
    chart_id: str,
    feature_set: Sequence[str],
) -> Tuple[Any, str, Availability, str]:
    keys = _payload_keys(chart_id)
    source: Mapping[str, Any] = payload
    path_prefix = ""

    if len(feature_set) == 1:
        params = _as_dict(payload.get("parameters"))
        feature = feature_set[0] if feature_set else ""
        param_payload = _as_dict(params.get(feature))
        if param_payload:
            source = param_payload
            path_prefix = f"parameters.{feature}."
    elif len(feature_set) == 2:
        dual = _as_dict(payload.get("dual_parameters"))
        for pair_key in _pair_keys(feature_set):
            pair_payload = _as_dict(dual.get(pair_key))
            if pair_payload:
                source = pair_payload
                path_prefix = f"dual_parameters.{pair_key}."
                break
    elif len(feature_set) >= 3:
        triple = _as_dict(payload.get("triple_parameters"))
        if chart_id in triple:
            source = triple
            path_prefix = "triple_parameters."
        elif chart_id in {"imr_3f", "run_chart_3f", "ewma_3f", "cusum_3f", "boxplot_3f"}:
            params = _as_dict(payload.get("parameters"))
            if all(isinstance(params.get(feature), dict) for feature in feature_set[:3]):
                return params, "parameters", STATUS_ANALYZED, ""

    first_unavailable: Tuple[Any, str, Availability, str] | None = None
    for key in keys:
        value = source.get(key) if isinstance(source, Mapping) else None
        status, reason = _payload_status(value)
        if status == STATUS_ANALYZED:
            return value, f"{path_prefix}{key}".rstrip("."), status, reason
        if status == STATUS_UNAVAILABLE and first_unavailable is None:
            first_unavailable = (value, f"{path_prefix}{key}".rstrip("."), status, reason)
    if first_unavailable is not None:
        return first_unavailable
    key_s = "|".join(keys)
    return None, f"{path_prefix}{key_s}".rstrip("."), STATUS_MISSING_DATA, "payload missing"


def _capability_stats(
    payload: Mapping[str, Any],
    feature: Optional[str],
    chart_payload: Any,
) -> Dict[str, Any]:
    summary = _as_dict(payload.get("summary"))
    per_measure = _as_dict(summary.get("per_measure"))
    if feature and isinstance(per_measure.get(feature), dict):
        pm = _as_dict(per_measure.get(feature))
        cap = _as_dict(pm.get("cap"))
        stats = _as_dict(cap.get("statistics"))
        if stats:
            return stats
    if isinstance(chart_payload, dict):
        stats = _as_dict(chart_payload.get("statistics"))
        if stats:
            return stats
    signals = _as_dict(payload.get("statistical_signals"))
    caps = _as_dict(_as_dict(signals.get("capabilities")).get("per_feature"))
    if feature and isinstance(caps.get(feature), dict):
        return _as_dict(caps.get(feature))
    return {}


def _feature_has_capability_risk(payload: Mapping[str, Any], feature: str) -> bool:
    stats = _capability_stats(payload, feature, None)
    cpk = _safe_float(stats.get("cpk"))
    if cpk is not None and cpk < 1.33:
        return True
    return False


def _format_pct(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:.1%}"


def _metric_line(parts: Iterable[str]) -> str:
    clean = [p for p in parts if p and not p.endswith("=—")]
    return "；".join(clean) if clean else "—"


def _severity_from_ratio(ratio: Optional[float], warn: float, alarm: float) -> Tuple[Severity, EvidenceState]:
    if ratio is None:
        return SEVERITY_INFO, STATE_NEUTRAL
    if ratio >= alarm:
        return SEVERITY_ERROR, STATE_SUPPORT
    if ratio > warn:
        return SEVERITY_WARNING, STATE_SUPPORT
    return SEVERITY_INFO, STATE_REFUTE


def _ooc_metrics(chart_payload: Any) -> Tuple[Optional[int], Optional[float], Optional[int]]:
    if not isinstance(chart_payload, dict):
        return None, None, None
    stats = _as_dict(chart_payload.get("statistics"))
    data = _as_dict(chart_payload.get("data"))
    ooc_count = stats.get("ooc_count", data.get("ooc_count"))
    if ooc_count is None:
        indices = data.get("out_of_control_indices")
        if isinstance(indices, list):
            ooc_count = len(indices)
    n = stats.get("n", data.get("n"))
    ratio = _safe_float(stats.get("ooc_ratio", data.get("ooc_ratio")))
    ooc_n = int(ooc_count) if isinstance(ooc_count, int) else None
    n_i = int(n) if isinstance(n, int) else None
    if ratio is None and ooc_n is not None and n_i and n_i > 0:
        ratio = ooc_n / n_i
    return ooc_n, ratio, n_i


def _distribution_signal(chart_payload: Any) -> Tuple[Severity, EvidenceState, str]:
    if not isinstance(chart_payload, dict):
        return SEVERITY_INFO, STATE_NEUTRAL, "—"
    stats = _as_dict(chart_payload.get("statistics"))
    is_normal = stats.get("is_normal")
    p_value = _safe_float(stats.get("p_value"))
    if is_normal is False:
        severity = SEVERITY_ERROR if p_value is not None and p_value < 0.01 else SEVERITY_WARNING
        return severity, STATE_SUPPORT, _metric_line([f"normality p={p_value:.4g}" if p_value is not None else "normality=reject"])
    if is_normal is True:
        return SEVERITY_INFO, STATE_REFUTE, _metric_line([f"normality p={p_value:.4g}" if p_value is not None else "normality=pass"])
    return SEVERITY_INFO, STATE_NEUTRAL, "normality=unknown"


def _pass_fail_signal(chart_payload: Any) -> Tuple[Severity, EvidenceState, str]:
    data = _as_dict(chart_payload.get("data")) if isinstance(chart_payload, dict) else {}
    pass_rates = data.get("pass_rates")
    fail_counts = data.get("fail_counts")
    max_fail_rate: Optional[float] = None
    max_fail_count = 0
    if isinstance(pass_rates, list) and pass_rates:
        rates = [_safe_float(v) for v in pass_rates]
        valid = [r for r in rates if r is not None]
        if valid:
            max_fail_rate = max(0.0, 100.0 - min(valid))
    if isinstance(fail_counts, list) and fail_counts:
        max_fail_count = max(int(v) for v in fail_counts if isinstance(v, int)) if any(isinstance(v, int) for v in fail_counts) else 0
    if max_fail_rate is None and max_fail_count <= 0:
        return SEVERITY_INFO, STATE_NEUTRAL, "Pass/Fail=unknown"
    metric = _metric_line([
        f"max fail={max_fail_rate:.1f}%" if max_fail_rate is not None else "",
        f"fail count={max_fail_count}",
    ])
    if (max_fail_rate is not None and max_fail_rate >= 2.0) or max_fail_count >= 3:
        return SEVERITY_ERROR, STATE_SUPPORT, metric
    if (max_fail_rate is not None and max_fail_rate > 0.0) or max_fail_count > 0:
        return SEVERITY_WARNING, STATE_SUPPORT, metric
    return SEVERITY_INFO, STATE_REFUTE, metric


def _correlation_signal(
    payload: Mapping[str, Any],
    chart_payload: Any,
    feature_set: Sequence[str],
) -> Tuple[Severity, EvidenceState, str]:
    if not isinstance(chart_payload, dict):
        return SEVERITY_INFO, STATE_NEUTRAL, "corr=unknown"
    data = _as_dict(chart_payload.get("data"))
    pairs = data.get("pairs_ranked")
    best: Optional[Dict[str, Any]] = None
    if isinstance(pairs, list):
        wanted = set(feature_set)
        for item in pairs:
            if not isinstance(item, dict):
                continue
            pair_features = {str(item.get("left") or ""), str(item.get("right") or "")}
            if wanted and wanted.issubset(pair_features):
                best = item
                break
        if best is None and pairs and isinstance(pairs[0], dict):
            best = pairs[0]
    abs_corr = _safe_float(best.get("abs_corr")) if isinstance(best, dict) else None
    pair = str(best.get("pair") or "pair") if isinstance(best, dict) else "pair"
    has_risk_feature = any(_feature_has_capability_risk(payload, feature) for feature in feature_set)
    metric = f"{pair} |r|={abs_corr:.2f}" if abs_corr is not None else "corr=unknown"
    if abs_corr is not None and abs_corr >= 0.7 and has_risk_feature:
        return SEVERITY_WARNING, STATE_SUPPORT, metric
    if abs_corr is not None and abs_corr < 0.5:
        return SEVERITY_INFO, STATE_REFUTE, metric
    return SEVERITY_INFO, STATE_NEUTRAL, metric


def _local_signal(payload: Mapping[str, Any], chart_id: str, chart_payload: Any) -> Tuple[Severity, EvidenceState, str]:
    summary = _as_dict(payload.get("summary"))
    layers = _as_dict(_as_dict(summary.get("process")).get("dashboard_layers"))
    l4 = _as_dict(layers.get("layer_4_defect_structure"))
    cluster_ratio = _safe_float(l4.get("cluster_ratio"))
    top_ref = l4.get("top_oos_refdes")
    top_count = len(top_ref) if isinstance(top_ref, list) else 0
    metric = _metric_line([
        f"cluster={_format_pct(cluster_ratio)}",
        f"top refs={top_count}" if top_count else "",
    ])
    if cluster_ratio is not None and cluster_ratio > 0.05:
        return SEVERITY_WARNING, STATE_SUPPORT, metric
    if chart_id == "repeated_offender" and top_count > 0:
        return SEVERITY_WARNING, STATE_SUPPORT, metric
    if isinstance(chart_payload, dict):
        data = _as_dict(chart_payload.get("data"))
        count = data.get("outlier_count") or data.get("component_count")
        if isinstance(count, int) and count > 0:
            return SEVERITY_WARNING, STATE_SUPPORT, metric
    if cluster_ratio is not None:
        return SEVERITY_INFO, STATE_REFUTE, metric
    return SEVERITY_INFO, STATE_NEUTRAL, metric


def _variation_signal(payload: Mapping[str, Any], feature: Optional[str]) -> Tuple[Severity, EvidenceState, str]:
    summary = _as_dict(payload.get("summary"))
    layers = _as_dict(_as_dict(summary.get("process")).get("dashboard_layers"))
    l5 = _as_dict(layers.get("layer_5_spec_analysis"))
    cp = _safe_float(l5.get("cp"))
    std_spec_ratio = _safe_float(l5.get("std_spec_ratio"))
    if feature:
        stats = _capability_stats(payload, feature, None)
        feature_cp = _safe_float(stats.get("cp"))
        if feature_cp is not None:
            cp = feature_cp
    metric = _metric_line([
        f"Cp={cp:.2f}" if cp is not None else "",
        f"std/spec={std_spec_ratio:.2f}" if std_spec_ratio is not None else "",
    ])
    if (cp is not None and cp < 1.0) or (std_spec_ratio is not None and std_spec_ratio > 0.30):
        return SEVERITY_ERROR, STATE_SUPPORT, metric
    if cp is not None and cp < 1.33:
        return SEVERITY_WARNING, STATE_SUPPORT, metric
    if cp is not None:
        return SEVERITY_INFO, STATE_REFUTE, metric
    return SEVERITY_INFO, STATE_NEUTRAL, metric


def _evaluate_candidate(
    payload: Mapping[str, Any],
    chart_id: str,
    feature_set: Sequence[str],
    chart_payload: Any,
    availability: Availability,
    missing_reason: str,
) -> Dict[str, Any]:
    dimensions = list(CHART_DIMENSIONS.get(chart_id, ("data_confidence",)))
    primary_dimension = dimensions[0] if dimensions else "data_confidence"
    if availability in {STATUS_UNAVAILABLE, STATUS_MISSING_DATA}:
        return {
            "evidence_state": STATE_UNAVAILABLE,
            "severity": SEVERITY_INFO,
            "evidence_dimension": "data_confidence",
            "evidence_dimensions": ["data_confidence"],
            "metric_snapshot": missing_reason or STATUS_LABELS.get(availability, availability),
            "relevance": 0.0,
        }
    if availability == STATUS_NOT_APPLICABLE:
        return {
            "evidence_state": STATE_UNAVAILABLE,
            "severity": SEVERITY_INFO,
            "evidence_dimension": primary_dimension,
            "evidence_dimensions": dimensions,
            "metric_snapshot": "feature count not applicable",
            "relevance": 0.0,
        }

    feature = feature_set[0] if feature_set else None
    severity = SEVERITY_INFO
    state = STATE_NEUTRAL
    metric = "—"

    if chart_id == "histogram_spec":
        stats = _capability_stats(payload, feature, chart_payload)
        cpk = _safe_float(stats.get("cpk"))
        cp = _safe_float(stats.get("cp"))
        metric = _metric_line([
            f"Cpk={cpk:.2f}" if cpk is not None else "",
            f"Cp={cp:.2f}" if cp is not None else "",
        ])
        if cpk is not None and cpk < 1.0:
            severity, state = SEVERITY_ERROR, STATE_SUPPORT
        elif cpk is not None and cpk < 1.33:
            severity, state = SEVERITY_WARNING, STATE_SUPPORT
        elif cpk is not None:
            severity, state = SEVERITY_INFO, STATE_REFUTE
    elif chart_id == "pass_fail_matrix":
        severity, state, metric = _pass_fail_signal(chart_payload)
    elif chart_id == "normality":
        severity, state, metric = _distribution_signal(chart_payload)
    elif chart_id in {"imr", "xbar_r", "ooc_analysis", "shift_detection"}:
        ooc_count, ratio, n = _ooc_metrics(chart_payload)
        severity, state = _severity_from_ratio(ratio, 0.0, 0.10)
        metric = _metric_line([
            f"OOC={ooc_count}/{n}" if ooc_count is not None and n is not None else "",
            f"ratio={_format_pct(ratio)}",
        ])
    elif chart_id in {"drift_detection", "ewma", "cusum", "run_chart", "pattern_recognition", "imr_3f", "run_chart_3f", "ewma_3f", "cusum_3f"}:
        data = _as_dict(chart_payload.get("data")) if isinstance(chart_payload, dict) else {}
        stats = _as_dict(chart_payload.get("statistics")) if isinstance(chart_payload, dict) else {}
        trend = str(data.get("trend_level") or data.get("shift_level") or "")
        peak = _safe_float(stats.get("max_drift_ratio") or data.get("max_drift_ratio"))
        if "Alarm" in trend or (peak is not None and peak >= 1.0):
            severity, state = SEVERITY_ERROR, STATE_SUPPORT
        elif "Warning" in trend or (peak is not None and peak >= 0.8):
            severity, state = SEVERITY_WARNING, STATE_SUPPORT
        elif trend or peak is not None:
            severity, state = SEVERITY_INFO, STATE_REFUTE
        metric = _metric_line([
            f"trend={trend}" if trend else "",
            f"drift ratio={peak:.2f}" if peak is not None else "",
        ])
    elif chart_id in {"pareto", "spatial_heatmap", "repeated_offender", "outlier_analysis"}:
        severity, state, metric = _local_signal(payload, chart_id, chart_payload)
    elif chart_id in {"scatter_spec", "correlation_matrix", "correlation_heatmap", "quadrant", "bivariate_outlier", "parallel_coord", "consistency_3f"}:
        severity, state, metric = _correlation_signal(payload, chart_payload, feature_set)
    elif chart_id in {"anomaly_3f"}:
        stats = _as_dict(chart_payload.get("statistics")) if isinstance(chart_payload, dict) else {}
        max_score = _safe_float(stats.get("max_score"))
        if max_score is not None and max_score >= 2.0:
            severity, state = SEVERITY_WARNING, STATE_SUPPORT
        elif max_score is not None:
            severity, state = SEVERITY_INFO, STATE_REFUTE
        metric = f"max anomaly={max_score:.2f}" if max_score is not None else "anomaly=unknown"
    elif chart_id in {"boxplot", "boxplot_3f", "subgroup", "anova_parttype"}:
        severity, state, metric = _variation_signal(payload, feature)

    relevance = float(SEVERITY_SCORE.get(severity, 0))
    if state == STATE_SUPPORT:
        relevance += 1.0
    if availability == STATUS_AVAILABLE_NOT_SELECTED:
        relevance = max(0.0, relevance - 0.25)
    return {
        "evidence_state": state,
        "severity": severity,
        "evidence_dimension": primary_dimension,
        "evidence_dimensions": dimensions,
        "metric_snapshot": metric,
        "relevance": round(relevance, 2),
    }


def _availability_counts(candidates: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    out = {
        STATUS_ANALYZED: 0,
        STATUS_AVAILABLE_NOT_SELECTED: 0,
        STATUS_UNAVAILABLE: 0,
        STATUS_NOT_APPLICABLE: 0,
        STATUS_MISSING_DATA: 0,
    }
    for item in candidates:
        status = str(item.get("availability") or "")
        if status in out:
            out[status] += 1
    return out


def _coverage_summary(candidates: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    counts = _availability_counts(candidates)
    applicable_total = len(candidates) - counts[STATUS_NOT_APPLICABLE]
    covered = counts[STATUS_ANALYZED] + counts[STATUS_AVAILABLE_NOT_SELECTED]
    coverage_pct = (covered / applicable_total * 100.0) if applicable_total > 0 else 100.0
    return {
        "candidate_count": len(candidates),
        "applicable_candidate_count": applicable_total,
        "covered_candidate_count": covered,
        "coverage_pct": round(coverage_pct, 1),
        "availability_counts": counts,
    }


def _build_combination_summary(candidates: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    single_count = 0
    dual_count = 0
    triple_count = 0
    for item in candidates:
        arity = int(item.get("required_feature_count") or 0)
        if arity == 1:
            single_count += 1
        elif arity == 2:
            dual_count += 1
        elif arity == 3:
            triple_count += 1
    return {
        "single_feature_candidate_count": single_count,
        "dual_feature_candidate_count": dual_count,
        "triple_feature_candidate_count": triple_count,
        "formula_zh": "1F charts × features + 2F charts × feature pairs + 3F charts × triple set",
        "candidate_count": len(candidates),
    }


def _family_label(chart_id: str) -> str:
    return CHART_UI_GROUP_BY_ID.get(chart_id, "其他")


def _aggregate_cell(candidates: Sequence[Mapping[str, Any]], family: str, dimension: str) -> Dict[str, Any]:
    matched = [
        c for c in candidates
        if c.get("chart_family") == family and dimension in (c.get("evidence_dimensions") or [])
    ]
    if not matched:
        return {"state": STATE_NEUTRAL, "severity": SEVERITY_INFO, "count": 0, "top_sources": []}
    support = [c for c in matched if c.get("evidence_state") == STATE_SUPPORT]
    refute = [c for c in matched if c.get("evidence_state") == STATE_REFUTE]
    unavailable = [
        c for c in matched
        if c.get("evidence_state") == STATE_UNAVAILABLE
        or c.get("availability") in {STATUS_UNAVAILABLE, STATUS_MISSING_DATA}
    ]
    if support:
        state = STATE_SUPPORT
        top = sorted(support, key=lambda c: float(c.get("relevance") or 0), reverse=True)
    elif refute:
        state = STATE_REFUTE
        top = refute
    elif unavailable and len(unavailable) == len(matched):
        state = STATE_UNAVAILABLE
        top = unavailable
    else:
        state = STATE_NEUTRAL
        top = matched
    severity = max((str(c.get("severity") or SEVERITY_INFO) for c in top), key=lambda s: SEVERITY_SCORE.get(s, 0))
    return {
        "state": state,
        "severity": severity,
        "count": len(matched),
        "support_count": len(support),
        "top_sources": [
            {
                "chart_id": str(c.get("chart_id") or ""),
                "chart_name": str(c.get("chart_name") or ""),
                "feature_set": c.get("feature_set") or [],
                "metric_snapshot": str(c.get("metric_snapshot") or ""),
            }
            for c in top[:3]
        ],
    }


def _build_evidence_matrix(candidates: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    families = ["製程監控", "製程能力", "異常根源", "變數關係", "比較分析", "其他"]
    rows: List[Dict[str, Any]] = []
    for family in families:
        if not any(c.get("chart_family") == family for c in candidates):
            continue
        cells = {
            dim: _aggregate_cell(candidates, family, dim)
            for dim in DIMENSION_ORDER
        }
        rows.append({"chart_family": family, "cells": cells})
    return rows


def _matrix_cell_state(rows: Sequence[Mapping[str, Any]], dimension: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        cells = _as_dict(row.get("cells"))
        cell = _as_dict(cells.get(dimension))
        if cell.get("state") == STATE_SUPPORT:
            out.append({"family": row.get("chart_family"), **cell})
    return out


def _matrix_signals(candidates: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []
    for c in candidates:
        if c.get("evidence_state") != STATE_SUPPORT:
            continue
        chart_id = str(c.get("chart_id") or "")
        dim = str(c.get("evidence_dimension") or "")
        anomaly_type = "Shift"
        if dim == "stability_drift":
            anomaly_type = "Drift" if chart_id in {"cusum", "drift_detection", "run_chart", "cusum_3f", "run_chart_3f"} else "Shift"
        elif dim == "local_cluster":
            anomaly_type = "Local" if chart_id == "spatial_heatmap" else "Cluster"
        elif dim == "distribution":
            anomaly_type = "Non-normal"
        elif dim == "variation":
            anomaly_type = "Variation_increase"
        elif dim == "multi_feature_correlation":
            anomaly_type = "Cluster"
        elif dim == "center_shift":
            anomaly_type = "Shift"
        elif dim == "capability_risk":
            anomaly_type = "Variation_increase"
        signals.append(
            {
                "feature": " + ".join(str(x) for x in (c.get("feature_set") or [])),
                "rule_id": f"matrix_{chart_id}_{dim}",
                "severity": c.get("severity") or SEVERITY_WARNING,
                "chart_type": c.get("chart_name") or chart_id,
                "anomaly_type": anomaly_type,
                "anomaly_type_zh": _msd._ANOMALY_TYPE_ZH.get(anomaly_type, anomaly_type),  # noqa: SLF001
                "summary": c.get("metric_snapshot") or "",
            }
        )
    return signals


def _build_relation(candidates: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    signals = _matrix_signals(candidates)
    correlation = _msd.analyze_correlations(signals)
    causes = _msd.generate_cause_hypothesis(signals, correlation)
    check_items = _msd.generate_check_items(causes)
    supported_dimensions = sorted({
        str(c.get("evidence_dimension") or "")
        for c in candidates
        if c.get("evidence_state") == STATE_SUPPORT
    })
    capability_support = any(d == "capability_risk" for d in supported_dimensions)
    pass_fail_support = any(
        c.get("chart_id") == "pass_fail_matrix" and c.get("evidence_state") == STATE_SUPPORT
        for c in candidates
    )
    if capability_support and pass_fail_support:
        correlation["pattern_label"] = "規格/能力主導異常"
        correlation["pattern_detail"] = "能力指標與 Pass/Fail 矩陣同時支持規格失效，需先確認規格、中心與變異來源。"
    return {
        "signals": signals,
        "correlation": correlation,
        "cause_hypotheses": causes,
        "check_items": check_items,
        "supported_dimensions": supported_dimensions,
        "supporting_signal_count": len(signals),
    }


def _confidence(
    candidates: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
) -> Dict[str, Any]:
    support = [c for c in candidates if c.get("evidence_state") == STATE_SUPPORT]
    support_families = {str(c.get("chart_family") or "") for c in support}
    support_dimensions = {str(c.get("evidence_dimension") or "") for c in support}
    error_count = sum(1 for c in support if c.get("severity") == SEVERITY_ERROR)
    coverage_pct = _safe_float(coverage.get("coverage_pct")) or 0.0
    score = 0
    if support:
        score += 1
    if len(support_families) >= 2:
        score += 1
    if len(support_dimensions) >= 2:
        score += 1
    if error_count:
        score += 1
    if coverage_pct >= 70.0:
        score += 1
    if score >= 4:
        label = "高"
        level = "high"
    elif score >= 2:
        label = "中"
        level = "medium"
    elif support:
        label = "低"
        level = "low"
    else:
        label = "觀察"
        level = "observation"
    return {
        "level": level,
        "label_zh": label,
        "score": score,
        "support_family_count": len(support_families),
        "support_dimension_count": len(support_dimensions),
        "support_candidate_count": len(support),
        "error_candidate_count": error_count,
    }


def _top_evidence(candidates: Sequence[Mapping[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    support = [c for c in candidates if c.get("evidence_state") == STATE_SUPPORT]
    support.sort(key=lambda c: float(c.get("relevance") or 0), reverse=True)
    return [
        {
            "chart_id": c.get("chart_id"),
            "chart_name": c.get("chart_name"),
            "feature_set": c.get("feature_set"),
            "chart_family": c.get("chart_family"),
            "dimension": c.get("evidence_dimension"),
            "dimension_label": DIMENSION_LABELS.get(str(c.get("evidence_dimension") or ""), str(c.get("evidence_dimension") or "")),
            "severity": c.get("severity"),
            "metric_snapshot": c.get("metric_snapshot"),
            "payload_path": c.get("payload_path"),
        }
        for c in support[:limit]
    ]


def _conflicts(candidates: Sequence[Mapping[str, Any]]) -> List[str]:
    support_dims = {
        str(c.get("evidence_dimension") or "")
        for c in candidates
        if c.get("evidence_state") == STATE_SUPPORT
    }
    conflict_lines: List[str] = []
    if support_dims == {"capability_risk"}:
        conflict_lines.append("能力/規格風險目前缺少穩定性、分布或局部圖表佐證，根因信心不可升高。")
    if "multi_feature_correlation" in support_dims and "capability_risk" not in support_dims:
        conflict_lines.append("多特徵關聯需對照失效特徵或規格結果，強相關本身不等同製程異常。")
    return conflict_lines


def _next_chart_ids(top: Sequence[Mapping[str, Any]]) -> List[str]:
    out: List[str] = []
    for item in top:
        chart_id = str(item.get("chart_id") or "")
        for nxt in CHART_NEXT_STEP_BY_ID.get(chart_id, []):
            if nxt not in out:
                out.append(nxt)
    if not out:
        out = ["imr", "histogram_spec", "normality", "pareto", "correlation_matrix"]
    return out[:6]


def _readable_value(value: Any) -> str:
    if value in (None, "", []):
        return "—"
    return str(value)


def _readable_feature_set(value: Any) -> str:
    if isinstance(value, list):
        text = " + ".join(str(item) for item in value if str(item).strip())
        return text or "—"
    return _readable_value(value)


def _readable_dimension_label(matrix: Mapping[str, Any], dimension: Any) -> str:
    key = str(dimension or "")
    labels = _as_dict(matrix.get("dimension_labels"))
    return str(labels.get(key) or DIMENSION_LABELS.get(key) or key or "—")


def _readable_reason_text(reason: Any) -> str:
    raw = str(reason or "").strip()
    if not raw:
        return "未提供原因"
    if raw == "payload missing":
        return "沒有對應圖表 payload"
    if raw == "payload empty":
        return "對應圖表 payload 為空"
    if raw == "payload invalid":
        return "對應圖表 payload 無效"
    if raw.startswith("requires ") and "feature" in raw:
        return "目前選取特徵數不符合此圖表需求"
    if raw == "feature count not applicable":
        return "目前選取特徵數不適用"
    return raw


def _readable_state_result(candidate_or_cell: Mapping[str, Any]) -> str:
    availability = str(candidate_or_cell.get("availability") or "")
    if availability in {STATUS_MISSING_DATA, STATUS_UNAVAILABLE}:
        return "資料不足/不可判讀"
    if availability == STATUS_NOT_APPLICABLE:
        return "不適用"
    state = str(candidate_or_cell.get("evidence_state") or candidate_or_cell.get("state") or "")
    return READABLE_STATE_LABELS.get(state, _readable_value(state))


def _dimension_action(dimension: str, state: str = STATE_SUPPORT) -> str:
    if state == STATE_REFUTE:
        return "先降低此假設作為主因的優先度，改看目前支持訊號較強的圖表。"
    if state in {STATE_UNAVAILABLE, ""}:
        return "補齊資料或改選適用特徵後重跑診斷，不要把缺資料視為正常。"
    if state == STATE_NEUTRAL:
        return "與其他支持訊號交叉確認後再決定是否追查。"
    actions = {
        "capability_risk": "確認規格邊界、Cp/Cpk 與失效比例是否集中在此特徵。",
        "center_shift": "確認均值偏移是否連續發生，並回查對位、刮刀與印刷條件。",
        "variation": "確認變異放大是否來自設備、材料、鋼板或量測系統。",
        "stability_drift": "確認失控或漂移是否跨時間延續，避免只看單點異常。",
        "local_cluster": "回查 OOC/OOS 是否集中於特定位號、區域或 PCB 條件。",
        "distribution": "確認非常態或偏態是否影響能力判讀可信度。",
        "multi_feature_correlation": "確認特徵間連動是否對應相同製程來源。",
        "data_confidence": "補強資料完整性後再升高判讀信心。",
    }
    return actions.get(dimension, "回看此圖表以補強製程異常鏈判讀。")


def _next_chart_purpose(chart_id: str) -> str:
    purposes = {
        "imr": "確認失控點與移動極差是否同步異常。",
        "xbar_r": "確認平均值偏移與子群內變異是否同時出現。",
        "ooc_analysis": "定位違反管制規則的點數、比例與樣本區段。",
        "pattern_recognition": "確認是否符合連續點、趨勢或特殊原因規則。",
        "run_chart": "對齊異常開始時間、漂移方向與樣本序。",
        "histogram_spec": "確認分布、規格界線與 Cp/Cpk 是否合理。",
        "normality": "確認分布型態是否影響能力判讀。",
        "boxplot": "比較中位數、IQR 與離群點，確認變異來源。",
        "pareto": "定位主要位號、區域或缺陷貢獻。",
        "spatial_heatmap": "確認異常是否集中在 PCB 空間位置。",
        "repeated_offender": "確認是否有重複異常元件或位置。",
        "correlation_matrix": "確認特徵間是否同步變化。",
        "correlation_heatmap": "確認多特徵關聯強度與方向。",
        "bivariate_outlier": "確認雙變數離群點是否帶動異常判讀。",
        "anova_parttype": "確認異常是否集中在特定元件類別。",
        "scatter_spec": "確認兩特徵的聯動是否落在規格風險區。",
        "quadrant": "用四象限定位高風險組合區域。",
        "subgroup": "確認批次、群組或條件差異是否為來源。",
        "anomaly_3f": "確認三特徵異常是否同步發生。",
        "consistency_3f": "確認三特徵一致性是否破壞。",
        "run_chart_3f": "對齊三特徵在同一樣本序的變化。",
        "imr_3f": "確認三特徵失控型態是否同步。",
        "cusum": "確認小幅偏移是否持續累積。",
        "cusum_3f": "確認三特徵小幅偏移是否同步累積。",
        "drift_detection": "確認漂移幅度與方向是否達警示。",
        "shift_detection": "確認中心是否發生階段性位移。",
    }
    return purposes.get(chart_id, "確認此圖表是否能補強或排除目前假設。")


def _readable_sources(sources: Any) -> str:
    if not isinstance(sources, list):
        return "矩陣彙整"
    lines: List[str] = []
    for source in sources[:3]:
        item = _as_dict(source)
        if not item:
            continue
        lines.append(
            f"{_readable_value(item.get('chart_name'))} / "
            f"{_readable_feature_set(item.get('feature_set'))}: "
            f"{_readable_value(item.get('metric_snapshot'))}"
        )
    return "；".join(lines) if lines else "矩陣彙整"


def _readable_row(
    *,
    title: str,
    result_zh: str,
    reason_zh: str,
    evidence_zh: str,
    next_action_zh: str,
    source_zh: str,
) -> Dict[str, str]:
    return {
        "title": title,
        "result_zh": result_zh,
        "reason_zh": reason_zh,
        "evidence_zh": evidence_zh,
        "next_action_zh": next_action_zh,
        "source_zh": source_zh,
    }


def _readable_candidate_sort_key(candidate: Mapping[str, Any]) -> Tuple[int, int, float]:
    state_order = {STATE_SUPPORT: 0, STATE_REFUTE: 1, STATE_NEUTRAL: 2, STATE_UNAVAILABLE: 3}
    severity_order = {SEVERITY_ERROR: 0, SEVERITY_WARNING: 1, SEVERITY_INFO: 2}
    return (
        state_order.get(str(candidate.get("evidence_state") or ""), 4),
        severity_order.get(str(candidate.get("severity") or ""), 3),
        -float(candidate.get("relevance") or 0.0),
    )


def _readable_candidate_row(
    candidate: Mapping[str, Any],
    matrix: Mapping[str, Any],
    *,
    title: Optional[str] = None,
) -> Dict[str, str]:
    dimension = str(candidate.get("evidence_dimension") or "")
    dim_label = _readable_dimension_label(matrix, dimension)
    state = str(candidate.get("evidence_state") or "")
    metric = _readable_value(candidate.get("metric_snapshot"))
    chart = _readable_value(candidate.get("chart_name"))
    feature = _readable_feature_set(candidate.get("feature_set"))
    result = _readable_state_result(candidate)
    if state == STATE_SUPPORT:
        reason = f"{dim_label}有圖表訊號支持；關鍵數值為 {metric}。"
    elif state == STATE_REFUTE:
        reason = f"目前未看到足夠的{dim_label}異常訊號；{metric} 不支持把此假設列為主因。"
    elif state == STATE_NEUTRAL:
        reason = f"{dim_label}訊號尚未達到支持或排除條件；關鍵數值為 {metric}。"
    else:
        reason = (
            f"{dim_label}目前不能判讀，原因是"
            f"{_readable_reason_text(candidate.get('missing_reason') or candidate.get('metric_snapshot'))}。"
        )
    payload_path = str(candidate.get("payload_path") or "").strip()
    return _readable_row(
        title=title or f"{chart} / {feature}",
        result_zh=result,
        reason_zh=reason,
        evidence_zh=f"{chart} / {feature}；{dim_label}；{metric}",
        next_action_zh=_dimension_action(dimension, state),
        source_zh=payload_path or "候選組合",
    )


def _readable_overview_rows(matrix: Mapping[str, Any]) -> List[Dict[str, str]]:
    summary = _as_dict(matrix.get("summary"))
    coverage = _as_dict(matrix.get("coverage"))
    confidence = _as_dict(summary.get("confidence"))
    rows = [
        _readable_row(
            title="診斷結論",
            result_zh=f"信心：{_readable_value(confidence.get('label_zh'))}",
            reason_zh=_readable_value(summary.get("verdict_zh")),
            evidence_zh=_readable_value(summary.get("coverage_line_zh")),
            next_action_zh=(
                "依主要支持證據追查製程條件；若信心不足，先補強圖表連動與資料完整性。"
            ),
            source_zh="diagnostic_evidence_matrix.summary",
        )
    ]
    top = [item for item in _as_list(summary.get("top_evidence")) if isinstance(item, dict)]
    for item in top[:3]:
        dimension = str(item.get("dimension") or "")
        dim_label = _readable_dimension_label(matrix, dimension)
        rows.append(
            _readable_row(
                title=f"{_readable_value(item.get('chart_name'))} / {_readable_feature_set(item.get('feature_set'))}",
                result_zh=READABLE_STATE_LABELS[STATE_SUPPORT],
                reason_zh=f"{dim_label}是目前排序靠前的支持證據。",
                evidence_zh=_readable_value(item.get("metric_snapshot")),
                next_action_zh=_dimension_action(dimension, STATE_SUPPORT),
                source_zh=_readable_value(item.get("payload_path")),
            )
        )
    if len(rows) == 1 and not coverage:
        rows[0]["reason_zh"] = "目前沒有足夠資料形成可讀診斷。"
    return rows


def _readable_combination_rows(matrix: Mapping[str, Any]) -> List[Dict[str, str]]:
    candidates = [item for item in _as_list(matrix.get("candidates")) if isinstance(item, dict)]
    candidates.sort(key=_readable_candidate_sort_key)
    return [_readable_candidate_row(candidate, matrix) for candidate in candidates[:24]]


def _readable_evidence_rows(matrix: Mapping[str, Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for row in _as_list(matrix.get("evidence_matrix")):
        item = _as_dict(row)
        family = _readable_value(item.get("chart_family"))
        cells = _as_dict(item.get("cells"))
        for dimension in DIMENSION_ORDER:
            cell = _as_dict(cells.get(dimension))
            if not cell:
                continue
            count = int(cell.get("support_count") or cell.get("count") or 0)
            if count <= 0:
                continue
            dim_label = _readable_dimension_label(matrix, dimension)
            state = str(cell.get("state") or STATE_NEUTRAL)
            if state == STATE_SUPPORT:
                reason = f"{family}有 {count} 項候選支持{dim_label}，可作為目前證據鏈的一部分。"
            elif state == STATE_REFUTE:
                reason = f"{family}有 {count} 項候選不支持{dim_label}，目前不宜把此假設列為主要原因。"
            elif state == STATE_UNAVAILABLE:
                reason = f"{family}在{dim_label}資料不足或不可判讀，不能當成正常或異常證據。"
            else:
                reason = f"{family}在{dim_label}尚未形成明確方向，需搭配其他圖表。"
            rows.append(
                _readable_row(
                    title=f"{family} / {dim_label}",
                    result_zh=READABLE_STATE_LABELS.get(state, _readable_value(state)),
                    reason_zh=reason,
                    evidence_zh=_readable_sources(cell.get("top_sources")),
                    next_action_zh=_dimension_action(dimension, state),
                    source_zh="evidence_matrix.cells",
                )
            )
    return rows


def _readable_correlation_rows(matrix: Mapping[str, Any]) -> List[Dict[str, str]]:
    relation = _as_dict(matrix.get("relation"))
    summary = _as_dict(matrix.get("summary"))
    corr = _as_dict(relation.get("correlation"))
    rows: List[Dict[str, str]] = []
    if corr:
        rows.append(
            _readable_row(
                title="關聯模式",
                result_zh=_readable_value(corr.get("pattern_label")),
                reason_zh=_readable_value(corr.get("pattern_detail")),
                evidence_zh=f"支持訊號數：{_readable_value(relation.get('supporting_signal_count'))}",
                next_action_zh="確認模式是否由多圖表共同支持，不以單一相關係數直接定根因。",
                source_zh="relation.correlation",
            )
        )
    for cause in _as_list(relation.get("cause_hypotheses"))[:4]:
        item = _as_dict(cause)
        if item:
            rows.append(
                _readable_row(
                    title=_readable_value(item.get("category")),
                    result_zh="根因假設",
                    reason_zh=_readable_value(item.get("description")),
                    evidence_zh="由支持訊號與多圖表關聯推導",
                    next_action_zh="依對策建議分頁逐項現場確認。",
                    source_zh="relation.cause_hypotheses",
                )
            )
    for conflict in _as_list(summary.get("conflicts")):
        rows.append(
            _readable_row(
                title="信心限制",
                result_zh="需要補強",
                reason_zh=_readable_value(conflict),
                evidence_zh="衝突或缺口訊號",
                next_action_zh="先補足缺口圖表或資料，再升高根因信心。",
                source_zh="summary.conflicts",
            )
        )
    return rows


def _readable_chart_linkage_rows(matrix: Mapping[str, Any]) -> List[Dict[str, str]]:
    summary = _as_dict(matrix.get("summary"))
    top = [item for item in _as_list(summary.get("top_evidence")) if isinstance(item, dict)]
    next_ids = [str(item) for item in _as_list(summary.get("next_chart_ids")) if str(item).strip()]
    rows: List[Dict[str, str]] = []
    for chart_id in next_ids[:6]:
        trigger = next(
            (
                item
                for item in top
                if chart_id in CHART_NEXT_STEP_BY_ID.get(str(item.get("chart_id") or ""), [])
            ),
            {},
        )
        chart_name = get_chart_display_name(chart_id, "zh_only")
        if trigger:
            trigger_chart = _readable_value(trigger.get("chart_name"))
            trigger_feature = _readable_feature_set(trigger.get("feature_set"))
            trigger_dim = _readable_dimension_label(matrix, trigger.get("dimension"))
            reason = (
                f"由 {trigger_chart} / {trigger_feature} 的{trigger_dim}支持訊號觸發，"
                f"需要用{chart_name}確認是否屬於同一異常鏈。"
            )
            evidence = _readable_value(trigger.get("metric_snapshot"))
            source = f"{trigger_chart} / {trigger_feature}"
        else:
            reason = f"目前證據鏈需要補強，建議查看{chart_name}以確認或排除相關假設。"
            evidence = "下一步圖表規則"
            source = "summary.next_chart_ids"
        rows.append(
            _readable_row(
                title=chart_name,
                result_zh="建議補強判讀",
                reason_zh=reason,
                evidence_zh=evidence,
                next_action_zh=_next_chart_purpose(chart_id),
                source_zh=source,
            )
        )
    return rows


def _readable_action_rows(matrix: Mapping[str, Any]) -> List[Dict[str, str]]:
    relation = _as_dict(matrix.get("relation"))
    rows: List[Dict[str, str]] = []
    for item in _as_list(relation.get("check_items")):
        check = _as_dict(item)
        if not check:
            continue
        items = [str(x) for x in _as_list(check.get("items")) if str(x).strip()]
        rows.append(
            _readable_row(
                title=_readable_value(check.get("category")),
                result_zh="需要確認",
                reason_zh="；".join(items[:3]) if items else "依支持證據回查現場條件。",
                evidence_zh="關聯判讀與支持訊號",
                next_action_zh="完成現場確認後重新匯入或重跑診斷，確認信心是否收斂。",
                source_zh="relation.check_items",
            )
        )
    if rows:
        return rows[:8]
    candidates = [item for item in _as_list(matrix.get("candidates")) if isinstance(item, dict)]
    support = [item for item in candidates if item.get("evidence_state") == STATE_SUPPORT]
    support.sort(key=_readable_candidate_sort_key)
    return [
        _readable_candidate_row(
            item,
            matrix,
            title=f"優先回查：{_readable_value(item.get('chart_name'))}",
        )
        for item in support[:5]
    ]


def _readable_data_context_rows(matrix: Mapping[str, Any]) -> List[Dict[str, str]]:
    coverage = _as_dict(matrix.get("coverage"))
    scope = _as_dict(matrix.get("filter_scope"))
    counts = _as_dict(coverage.get("availability_counts"))
    rows = [
        _readable_row(
            title="資料範圍",
            result_zh=_readable_value(scope.get("scope_zh") or "全批/全元件"),
            reason_zh="此範圍決定矩陣候選圖表與證據覆蓋率。",
            evidence_zh=(
                f"產品={_readable_value(scope.get('product'))}；"
                f"線別={_readable_value(scope.get('line'))}；"
                f"時間={_readable_value(scope.get('time_start'))}~{_readable_value(scope.get('time_end'))}"
            ),
            next_action_zh="若範圍不是現場要判讀的批次或元件，先調整篩選後重跑。",
            source_zh="filter_scope",
        ),
        _readable_row(
            title="覆蓋狀態",
            result_zh=_readable_value(coverage.get("coverage_pct")) + "%",
            reason_zh=(
                f"已覆蓋 {coverage.get('covered_candidate_count', 0)}/"
                f"{coverage.get('applicable_candidate_count', 0)} 個適用候選。"
            ),
            evidence_zh=f"候選總數={coverage.get('candidate_count', 0)}",
            next_action_zh="優先補齊缺資料與不可用圖表，避免信心被資料缺口拉低。",
            source_zh="coverage",
        ),
        _readable_row(
            title="資料缺口",
            result_zh="資料不足/不可判讀",
            reason_zh=(
                f"缺資料 {counts.get(STATUS_MISSING_DATA, 0)}；"
                f"不可用 {counts.get(STATUS_UNAVAILABLE, 0)}；"
                f"不適用 {counts.get(STATUS_NOT_APPLICABLE, 0)}。"
            ),
            evidence_zh="availability_counts",
            next_action_zh="缺資料與不可用只代表無法判讀，不得當作正常證據。",
            source_zh="coverage.availability_counts",
        ),
    ]
    return rows


def build_readable_diagnostic_tabs(matrix: Mapping[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    """Translate diagnostic matrix internals into user-readable tab rows.

    This presenter preserves the internal support/refute/neutral/unavailable
    values and only changes visible wording for UI, Excel, and PPTX output.
    """
    if not isinstance(matrix, Mapping) or not matrix:
        return {}
    tabs = {
        "overview": _readable_overview_rows(matrix),
        "combination_matrix": _readable_combination_rows(matrix),
        "evidence_matrix": _readable_evidence_rows(matrix),
        "correlation": _readable_correlation_rows(matrix),
        "chart_linkage": _readable_chart_linkage_rows(matrix),
        "actions": _readable_action_rows(matrix),
        "data_context": _readable_data_context_rows(matrix),
    }
    for key in READABLE_TAB_KEYS:
        if not tabs.get(key):
            tabs[key] = [
                _readable_row(
                    title="目前無可判讀內容",
                    result_zh="資料不足/不可判讀",
                    reason_zh="此分頁目前沒有足夠資料形成白話判讀。",
                    evidence_zh="—",
                    next_action_zh="補齊資料或重跑分析後再查看。",
                    source_zh=key,
                )
            ]
    return tabs


def _scope_context(payload: Mapping[str, Any], filter_context: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    ctx = dict(filter_context or {})
    batch = str(ctx.get("batch") or payload.get("_ctx_batch") or "").strip()
    refdes = str(ctx.get("refdes") or payload.get("_ctx_refdes") or "").strip()
    part_type = str(ctx.get("part_type") or payload.get("_ctx_part_type") or "").strip()
    product = str(ctx.get("product") or "").strip()
    line = str(ctx.get("line") or "").strip()
    time_start = str(ctx.get("time_start") or "").strip()
    time_end = str(ctx.get("time_end") or "").strip()
    scope_parts: List[str] = []
    if refdes and refdes != "全部 (All)":
        scope_parts.append(f"元件={refdes}")
    if part_type and part_type != "全部 (All)":
        scope_parts.append(f"類別={part_type}")
    if batch and batch != "全部 (All)":
        scope_parts.append(f"範圍={batch}")
    if product:
        scope_parts.append(f"產品={product}")
    if line:
        scope_parts.append(f"線別={line}")
    if time_start or time_end:
        scope_parts.append(f"時間={time_start or '—'}~{time_end or '—'}")
    return {
        "batch": batch,
        "refdes": refdes,
        "part_type": part_type,
        "product": product,
        "line": line,
        "time_start": time_start,
        "time_end": time_end,
        "scope_zh": "；".join(scope_parts) if scope_parts else "全批/全元件",
    }


def _build_summary(
    candidates: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
    relation: Mapping[str, Any],
) -> Dict[str, Any]:
    top = _top_evidence(candidates)
    conf = _confidence(candidates, coverage)
    correlation = _as_dict(relation.get("correlation"))
    conflicts = _conflicts(candidates)
    support_family_count = int(conf.get("support_family_count") or 0)
    support_dimension_count = int(conf.get("support_dimension_count") or 0)
    if not top:
        verdict = "目前未形成可支持製程異常的組合證據。"
    elif support_family_count < 2 and support_dimension_count < 2:
        verdict = "已有單點異常訊號，但不足以單獨定根因。"
    elif conf.get("level") == "high":
        verdict = "多圖表證據已形成高信心製程異常鏈。"
    elif conf.get("level") == "medium":
        verdict = "已形成部分組合證據，需依關聯圖表補強判讀。"
    else:
        verdict = "已有單點異常訊號，但不足以單獨定根因。"
    next_ids = _next_chart_ids(top)
    return {
        "verdict_zh": verdict,
        "confidence": conf,
        "pattern_label": correlation.get("pattern_label") or "—",
        "pattern_detail": correlation.get("pattern_detail") or "",
        "top_evidence": top,
        "conflicts": conflicts,
        "next_chart_ids": next_ids,
        "next_chart_names": [get_chart_display_name(cid, "zh_only") for cid in next_ids],
        "coverage_line_zh": (
            f"組合覆蓋 {coverage.get('covered_candidate_count', 0)}/"
            f"{coverage.get('applicable_candidate_count', 0)} "
            f"({coverage.get('coverage_pct', 0)}%)"
        ),
    }


def _candidate_line(candidate: Mapping[str, Any]) -> str:
    fset = " + ".join(str(x) for x in (candidate.get("feature_set") or [])) or "—"
    dim = DIMENSION_LABELS.get(str(candidate.get("evidence_dimension") or ""), str(candidate.get("evidence_dimension") or ""))
    state = STATE_LABELS.get(str(candidate.get("evidence_state") or ""), str(candidate.get("evidence_state") or ""))
    status = STATUS_LABELS.get(str(candidate.get("availability") or ""), str(candidate.get("availability") or ""))
    return (
        f"{fset} | {candidate.get('chart_name')} | {status} | {dim}:{state} | "
        f"{candidate.get('metric_snapshot') or '—'}"
    )


def _build_tabs(
    result: Mapping[str, Any],
    scope_context: Mapping[str, str],
) -> Dict[str, List[str]]:
    summary = _as_dict(result.get("summary"))
    coverage = _as_dict(result.get("coverage"))
    relation = _as_dict(result.get("relation"))
    candidates = result.get("candidates")
    cand_list = candidates if isinstance(candidates, list) else []
    top_raw = summary.get("top_evidence")
    top: List[Any] = top_raw if isinstance(top_raw, list) else []
    conflicts_raw = summary.get("conflicts")
    conflicts: List[Any] = conflicts_raw if isinstance(conflicts_raw, list) else []
    next_names_raw = summary.get("next_chart_names")
    next_names: List[Any] = next_names_raw if isinstance(next_names_raw, list) else []
    evidence_rows = result.get("evidence_matrix")
    rows = evidence_rows if isinstance(evidence_rows, list) else []

    matrix_lines: List[str] = []
    for row in rows:
        cells = _as_dict(row.get("cells")) if isinstance(row, dict) else {}
        supported = [
            DIMENSION_LABELS.get(dim, dim)
            for dim, cell in cells.items()
            if isinstance(cell, dict) and cell.get("state") == STATE_SUPPORT
        ]
        unavailable = [
            DIMENSION_LABELS.get(dim, dim)
            for dim, cell in cells.items()
            if isinstance(cell, dict) and cell.get("state") == STATE_UNAVAILABLE
        ]
        matrix_lines.append(
            f"{row.get('chart_family', '—')}: 支持={ '、'.join(supported) if supported else '—' }；"
            f"不可判={ '、'.join(unavailable[:3]) if unavailable else '—' }"
        )

    top_lines = [
        f"{item.get('chart_name')} / {' + '.join(str(x) for x in (item.get('feature_set') or []))}: {item.get('metric_snapshot')}"
        for item in top[:5]
        if isinstance(item, dict)
    ]
    support_candidates = [
        c for c in cand_list
        if isinstance(c, dict) and c.get("evidence_state") == STATE_SUPPORT
    ]
    support_candidates.sort(key=lambda c: float(c.get("relevance") or 0), reverse=True)

    corr = _as_dict(relation.get("correlation"))
    causes_raw = relation.get("cause_hypotheses")
    causes: List[Any] = causes_raw if isinstance(causes_raw, list) else []
    checks_raw = relation.get("check_items")
    checks: List[Any] = checks_raw if isinstance(checks_raw, list) else []
    cause_lines: List[str] = []
    for c in causes[:4]:
        if isinstance(c, dict):
            cause_lines.append(str(c.get("category", "—")) + "：" + str(c.get("description", "—")))
    action_lines: List[str] = []
    for item in checks[:5]:
        if not isinstance(item, dict):
            continue
        items = item.get("items")
        item_list = items if isinstance(items, list) else []
        action_lines.append(
            f"{item.get('category', '—')}：{'；'.join(str(x) for x in item_list[:3])}"
        )

    return {
        "overview": [
            f"結論：{summary.get('verdict_zh', '—')}",
            f"信心：{_as_dict(summary.get('confidence')).get('label_zh', '—')}",
            str(summary.get("coverage_line_zh") or ""),
            f"範圍：{scope_context.get('scope_zh', '全批/全元件')}",
            *(top_lines[:3] or ["主要證據：—"]),
        ],
        "combination_matrix": [
            str(_candidate_line(c)) for c in cand_list[:40] if isinstance(c, dict)
        ],
        "evidence_matrix": matrix_lines or ["—"],
        "correlation": [
            f"模式：{corr.get('pattern_label', '—')}",
            f"說明：{corr.get('pattern_detail', '—')}",
            *cause_lines,
            *(f"衝突：{line}" for line in conflicts),
        ],
        "chart_linkage": [
            f"下一步圖表：{ '、'.join(str(x) for x in next_names) if next_names else '—' }",
            *(str(_candidate_line(c)) for c in support_candidates[:6]),
        ],
        "actions": action_lines or ["依矩陣支持證據先確認最高風險圖表，再回查對應製程條件。"],
        "data_context": [
            f"候選組合：{coverage.get('candidate_count', 0)}",
            f"適用組合：{coverage.get('applicable_candidate_count', 0)}",
            f"已覆蓋：{coverage.get('covered_candidate_count', 0)}",
            f"缺資料/不可用：{_as_dict(coverage.get('availability_counts')).get(STATUS_MISSING_DATA, 0)} / {_as_dict(coverage.get('availability_counts')).get(STATUS_UNAVAILABLE, 0)}",
        ],
    }


def build_diagnostic_evidence_matrix(
    payload: Mapping[str, Any],
    *,
    selected_chart_ids: Optional[Sequence[str]] = None,
    filter_context: Optional[Mapping[str, Any]] = None,
    display_mode: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the full diagnostic combination/evidence matrix from existing payload data."""
    if not isinstance(payload, Mapping):
        return {}
    features = _selected_features(payload)
    selected_set = {str(x).strip() for x in (selected_chart_ids or []) if str(x).strip()}
    scope_context = _scope_context(payload, filter_context)
    display_ctx = dict(display_mode or {})

    candidates: List[Dict[str, Any]] = []
    for chart_id in CHART_ORDER:
        applicable = _is_applicable(chart_id, features)
        feature_sets = _candidate_feature_sets(chart_id, features)
        for feature_set in feature_sets:
            chart_name = get_chart_display_name(chart_id, "zh_only")
            chart_family = _family_label(chart_id)
            required = _chart_arity(chart_id)
            if not applicable:
                availability = STATUS_NOT_APPLICABLE
                chart_payload: Any = None
                payload_path = ""
                reason = f"requires {required} feature(s)"
            else:
                chart_payload, payload_path, availability, reason = _resolve_candidate_payload(
                    payload,
                    chart_id,
                    feature_set,
                )
                if availability == STATUS_ANALYZED and selected_set and chart_id not in selected_set:
                    availability = STATUS_AVAILABLE_NOT_SELECTED
            eval_result = _evaluate_candidate(
                payload,
                chart_id,
                feature_set,
                chart_payload,
                availability,
                reason,
            )
            candidates.append(
                {
                    "feature_set": list(feature_set),
                    "chart_id": chart_id,
                    "chart_name": chart_name,
                    "chart_family": chart_family,
                    "required_feature_count": required,
                    "filter_scope": scope_context,
                    "display_mode": display_ctx,
                    "availability": availability,
                    "availability_label_zh": STATUS_LABELS.get(availability, availability),
                    "payload_path": payload_path,
                    "missing_reason": reason,
                    **eval_result,
                }
            )

    coverage = _coverage_summary(candidates)
    evidence_matrix = _build_evidence_matrix(candidates)
    relation = _build_relation(candidates)
    summary = _build_summary(candidates, coverage, relation)
    result: Dict[str, Any] = {
        "schema_version": DIAGNOSTIC_EVIDENCE_MATRIX_SCHEMA_VERSION,
        "selected_features": features,
        "selected_feature_count": len(features),
        "filter_scope": scope_context,
        "display_mode": display_ctx,
        "coverage": coverage,
        "combination_summary": _build_combination_summary(candidates),
        "dimension_order": DIMENSION_ORDER,
        "dimension_labels": DIMENSION_LABELS,
        "candidates": candidates,
        "evidence_matrix": evidence_matrix,
        "relation": relation,
        "summary": summary,
    }
    result["tabs"] = _build_tabs(result, scope_context)
    return result
