"""
Versioned Statistical Signals — single DTO assembled from existing engine payloads.

Formulas remain in capability/spc/normality engines and summary_engine; this module
only normalizes paths and evidence refs for diagnosis / risk / reports.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

STATISTICAL_SIGNALS_SCHEMA_VERSION = "1.0.0"


def _ref(chart_id: str, payload_path: str) -> Dict[str, str]:
    return {"chart_id": chart_id, "payload_path": payload_path}


def _safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def _bimodal_hint_from_histogram(dist_payload: Dict[str, Any]) -> Optional[bool]:
    """Heuristic: two separated peaks in histogram counts (engineering hint only)."""
    data = (dist_payload or {}).get("data") or {}
    counts = data.get("counts")
    if not isinstance(counts, list) or len(counts) < 5:
        return None
    vals = [float(c) for c in counts if c is not None]
    if len(vals) < 5 or max(vals) <= 0:
        return None
    # Find local maxima (strict)
    peaks: List[int] = []
    for i in range(1, len(vals) - 1):
        if vals[i] > vals[i - 1] and vals[i] > vals[i + 1] and vals[i] >= max(vals) * 0.25:
            peaks.append(i)
    if len(peaks) >= 2:
        return True
    return False


def _run_chart_slope(run_payload: Dict[str, Any]) -> Optional[float]:
    """OLS slope vs sequence index (normalized by std of x) as trend strength hint."""
    data = (run_payload or {}).get("data") or {}
    values = data.get("values")
    if not isinstance(values, list) or len(values) < 5:
        return None
    y_raw = [_safe_float(v) for v in values]
    y_vals: List[float] = [v for v in y_raw if v is not None]
    n = len(y_vals)
    if n < 5:
        return None
    x_mean = (n - 1) / 2.0
    y_mean = sum(y_vals) / n
    sxx = sum((i - x_mean) ** 2 for i in range(n))
    sxy = sum((i - x_mean) * (y_vals[i] - y_mean) for i in range(n))
    if sxx <= 0:
        return None
    return float(sxy / sxx)


def build_statistical_signals(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build statistical signals from a chart analysis payload and embedded summary.

    Works for n==1 (rich top-level charts) and n>=2 (summary + parameters only).
    """
    summary: Dict[str, Any] = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    relation: Dict[str, Any] = (
        summary["relation"] if isinstance(summary.get("relation"), dict) else {}
    )
    process: Dict[str, Any] = (
        summary["process"] if isinstance(summary.get("process"), dict) else {}
    )
    layers: Dict[str, Any] = (
        process["dashboard_layers"] if isinstance(process.get("dashboard_layers"), dict) else {}
    )
    per_measure: Dict[str, Any] = (
        summary["per_measure"] if isinstance(summary.get("per_measure"), dict) else {}
    )

    primary = None
    sf = payload.get("selected_features")
    if isinstance(sf, list) and sf:
        primary = str(sf[0])

    # --- Capability / defect (from summary per_measure) ---
    capabilities: Dict[str, Any] = {"per_feature": {}, "aggregate": {}}
    for col, pm in per_measure.items():
        if not isinstance(pm, dict):
            continue
        cap = pm.get("cap") or {}
        cap_stats = (cap.get("statistics") or {}) if isinstance(cap, dict) else {}
        defect = pm.get("defect") or {}
        capabilities["per_feature"][col] = {
            "cp": cap_stats.get("cp"),
            "cpk": cap_stats.get("cpk"),
            "pp": cap_stats.get("pp"),
            "ppk": cap_stats.get("ppk"),
            "mean": cap_stats.get("mean"),
            "sigma_st": cap_stats.get("sigma_st"),
            "sigma_lt": cap_stats.get("sigma_lt"),
            "yield_pct": pm.get("yield_pct"),
            "ppm_total": defect.get("ppm_total"),
            "dpmo_feature": defect.get("dpmo_feature"),
            "cpk_ci": defect.get("cpk_ci"),
            "cpk_ci_method": defect.get("cpk_ci_method"),
            "n": pm.get("n"),
            "evidence_refs": [_ref("capability", f"summary.per_measure.{col}.cap")],
        }
    capabilities["aggregate"]["min_cpk"] = process.get("min_cpk")
    capabilities["aggregate"]["min_cpk_measure"] = process.get("min_cpk_measure")
    capabilities["aggregate"]["overall_yield_pct"] = process.get("overall_yield_pct")
    capabilities["aggregate"]["defect_combined"] = process.get("defect_combined")

    # --- Correlation (summary relation) ---
    correlation: Dict[str, Any] = {
        "corr_vol_area": relation.get("corr_vol_area"),
        "corr_vol_height": relation.get("corr_vol_height"),
        "corr_area_height": relation.get("corr_area_height"),
        "vol_area_mean": relation.get("vol_area_mean"),
        "vol_area_vs_height_diff": relation.get("vol_area_vs_height_diff"),
        "evidence_refs": [_ref("correlation_matrix", "summary.relation")],
    }

    # --- Primary feature deep signals (single-feature payload) ---
    stability: Dict[str, Any] = {}
    drift: Dict[str, Any] = {}
    distribution: Dict[str, Any] = {}
    variation: Dict[str, Any] = {}
    spatial: Dict[str, Any] = {}

    if primary:
        _spc_raw = payload.get("spc")
        spc: Dict[str, Any] = _spc_raw if isinstance(_spc_raw, dict) else {}
        spc_data: Any = spc.get("data") or {}
        spc_stats: Any = spc.get("statistics") or {}
        ooc_idx = spc_data.get("out_of_control_indices") or []
        n_spc = int(spc_stats.get("n") or 0)
        ooc_ratio = (len(ooc_idx) / n_spc) if n_spc > 0 else None
        stability["primary_feature"] = primary
        stability["chart_family"] = "I-MR"
        stability["ooc_count"] = len(ooc_idx)
        stability["ooc_ratio"] = ooc_ratio
        _pr_raw = payload.get("pattern_recognition")
        _pr = _pr_raw if isinstance(_pr_raw, dict) else {}
        _prd_raw = _pr.get("data")
        _pr_data: Dict[str, Any] = _prd_raw if isinstance(_prd_raw, dict) else {}
        stability["nelson_rule_hits"] = len(_pr_data.get("rule_hits") or [])
        stability["evidence_refs"] = [
            _ref("imr", "spc"),
            _ref("pattern_recognition", "pattern_recognition"),
        ]

        _xbr_raw = payload.get("xbar_r")
        xbr: Dict[str, Any] = _xbr_raw if isinstance(_xbr_raw, dict) else {}
        _xbr_meta = xbr.get("metadata")
        if isinstance(_xbr_meta, dict) and _xbr_meta.get("is_valid"):
            stability["xbar_r_valid"] = True
            stability["evidence_refs"].append(_ref("xbar_r", "xbar_r"))

        _cus = payload.get("cusum")
        _cus_stats = _cus.get("statistics") if isinstance(_cus, dict) else {}
        drift["cusum_peak_ratio"] = _cus_stats.get("max_drift_ratio") if isinstance(_cus_stats, dict) else None
        _dd = payload.get("drift_detection")
        if isinstance(_dd, dict):
            _dd_data = _dd.get("data")
            drift["ewma_trend"] = _dd_data.get("trend_level") if isinstance(_dd_data, dict) else None
        else:
            drift["ewma_trend"] = None
        _rc = payload.get("run_chart")
        drift["run_chart_slope"] = _run_chart_slope(_rc if isinstance(_rc, dict) else {})
        drift["evidence_refs"] = [_ref("cusum", "cusum"), _ref("ewma", "ewma"), _ref("run_chart", "run_chart")]

        _norm_raw = payload.get("normality")
        norm: Dict[str, Any] = _norm_raw if isinstance(_norm_raw, dict) else {}
        nstats: Any = norm.get("statistics") or {}
        _dist_raw = payload.get("dist")
        dist_pl: Dict[str, Any] = _dist_raw if isinstance(_dist_raw, dict) else {}
        distribution["is_normal"] = nstats.get("is_normal")
        distribution["normality_p_value"] = nstats.get("p_value")
        distribution["bimodal_hint"] = _bimodal_hint_from_histogram(dist_pl)
        distribution["evidence_refs"] = [_ref("normality", "normality"), _ref("histogram_spec", "dist")]

        _box_raw = payload.get("box")
        box: Dict[str, Any] = _box_raw if isinstance(_box_raw, dict) else {}
        variation["box_grouping"] = box.get("_grouping_mode")
        _anova_raw = payload.get("anova_parttype")
        _anova: Dict[str, Any] = _anova_raw if isinstance(_anova_raw, dict) else {}
        _anova_stats = _anova.get("statistics")
        variation["anova_p"] = (
            _anova_stats.get("p_value") if isinstance(_anova_stats, dict) else None
        )
        variation["evidence_refs"] = [_ref("boxplot", "box"), _ref("anova_parttype", "anova_parttype")]

        _spat_raw = payload.get("spatial")
        spat: Dict[str, Any] = _spat_raw if isinstance(_spat_raw, dict) else {}
        _spat_meta = spat.get("metadata")
        spatial["heatmap_valid"] = _spat_meta.get("is_valid") if isinstance(_spat_meta, dict) else None
        _l4 = layers.get("layer_4_defect_structure")
        _l4d: Dict[str, Any] = _l4 if isinstance(_l4, dict) else {}
        spatial["cluster_ratio"] = _l4d.get("cluster_ratio")
        spatial["edge_vs_center_hint"] = _l4d.get("abnormal_cluster_location")
        spatial["evidence_refs"] = [_ref("spatial_heatmap", "spatial")]

    return {
        "schema_version": STATISTICAL_SIGNALS_SCHEMA_VERSION,
        "primary_feature": primary,
        "capabilities": capabilities,
        "correlation": correlation,
        "stability": stability,
        "drift": drift,
        "distribution": distribution,
        "variation": variation,
        "spatial": spatial,
    }
