"""
Summary engine: aggregates per-measure (Volume/Area/Height) statistics,
cross-measure relations (correlations, volume/area vs height), and process verdict.
Used by the process dashboard (`DiagnosticPage`) and reports via `payload["summary"]`.
"""
import math
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple

from app.analytics.pearson_utils import pearson_r_safe
from app.analytics.capability_engine import CapabilityEngine
from app.analytics.distribution_engine import DistributionEngine
from app.analytics.normality_engine import NormalityEngine
from app.analytics.spc_engine import SPCEngine
from app.utils.numeric_utils import safe_float
from app.analytics.cusum_engine import CUSUMEngine
from app.analytics.ooc_utils import count_contiguous_ooc_clusters
from app.analytics.process_diagnosis_engine import run_process_diagnosis
import scipy.stats as stats  # type: ignore[import-untyped]


MEASURE_COLS = ["Volume", "Area", "Height"]
SPEC_KEY_TO_COL = {"volume": "Volume", "area": "Area", "height": "Height"}
COL_TO_SPEC_KEY = {v: k for k, v in SPEC_KEY_TO_COL.items()}

_WORKORDER_CONTEXT_KEYS = (
    "product_name",
    "model_name",
    "work_order_no",
    "supplier_work_order_no",
    "outsource_work_order_no",
    "batch_no",
    "batch_qty",
    "pcb_size",
    "pcb_layer",
    "stencil_thickness",
    "stencil_type",
    "step_stencil",
    "step_thickness",
    "pad_type",
    "pad_size",
    "aperture_type",
    "aperture_ratio",
    "spec_source",
    "critical_component",
)
CPK_CI_ALPHA = 0.05
CPK_CI_METHOD = "Bissell approximation (NIST/AIAG convention, two-sided 95%)"


def _maybe_float(value: Any) -> Optional[float]:
    """Best-effort numeric parsing for spec values from session payload."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return None
        try:
            return float(text)
        except (TypeError, ValueError):
            return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_spec(spec: Optional[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Parse workorder_spec entry (usl, lsl, target as strings). Returns (usl, lsl, target) or (None, None, None)."""
    if not spec or not isinstance(spec, dict):
        return None, None, None
    usl = _maybe_float(spec.get("usl"))
    lsl = _maybe_float(spec.get("lsl"))
    target = _maybe_float(spec.get("target"))
    return usl, lsl, target


def _yield_pct(data: pd.Series, usl: float, lsl: float) -> Optional[float]:
    """In-spec proportion as percentage. Returns None if invalid."""
    if usl is None or lsl is None or data is None or data.empty:
        return None
    valid = data.replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) == 0:
        return None
    in_spec = ((valid >= lsl) & (valid <= usl)).sum()
    return float(in_spec / len(valid) * 100.0)


def _count_defects(data: pd.Series, usl: float, lsl: float) -> Tuple[int, int, int, int]:
    """Return (below_lsl, above_usl, total_defect, n_valid)."""
    valid = data.replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) == 0:
        return 0, 0, 0, 0
    below = int((valid < lsl).sum())
    above = int((valid > usl).sum())
    total = below + above
    return below, above, total, int(len(valid))


def _to_ppm(defect_count: int, n_valid: int) -> Optional[float]:
    if n_valid <= 0:
        return None
    return float(defect_count / n_valid * 1_000_000.0)


def _infer_board_n(df: pd.DataFrame, fallback_n: int) -> int:
    """Infer board count from board-like id columns; fallback to provided n."""
    for col in ("BoardNo", "PanelId"):
        if col in df.columns:
            non_null = df[col].dropna()
            if len(non_null) > 0:
                return int(non_null.nunique())
    return int(fallback_n)


def _to_dpmo(defect_count: int, opportunity_count: int) -> Optional[float]:
    """Defects per million opportunities."""
    if opportunity_count <= 0:
        return None
    return float(defect_count / opportunity_count * 1_000_000.0)


def _normalize_ooc_ratio(ooc_count: int, n_valid: int) -> Optional[float]:
    if n_valid <= 0:
        return None
    return float(ooc_count / n_valid)


def _zbench_from_defect_rate(defect_rate: Optional[float]) -> Optional[float]:
    """One-tail defect rate to Zbench; returns None when undefined."""
    if defect_rate is None:
        return None
    if defect_rate <= 0.0:
        # Avoid inf in UI; cap at practical ceiling.
        return 6.0
    if defect_rate >= 1.0:
        return None
    return float(stats.norm.ppf(1.0 - defect_rate))


def _zbench_st_lt_from_cap(cap_stats: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Derive ST/LT Zbench via defect-rate path from Cpk/Ppk.
    This preserves ST/LT semantics without changing SPC formulas.
    """
    cpk = cap_stats.get("cpk")
    ppk = cap_stats.get("ppk")
    z_st = None
    z_lt = None
    if cpk is not None:
        # Bench-style one-sided tail probability keeps p in [0, 1] even for negative Cpk.
        p_st = float(1.0 - stats.norm.cdf(3.0 * float(cpk)))
        z_st = _zbench_from_defect_rate(p_st)
    if ppk is not None:
        p_lt = float(1.0 - stats.norm.cdf(3.0 * float(ppk)))
        z_lt = _zbench_from_defect_rate(p_lt)
    return z_st, z_lt


def _cpk_95ci_text(cpk: Optional[float], n_valid: int, alpha: float = CPK_CI_ALPHA) -> str:
    """Bissell approximation for two-sided Cpk confidence interval."""
    if cpk is None or n_valid < 2:
        return "N/A"
    cpk_f = float(cpk)
    z = float(stats.norm.ppf(1.0 - alpha / 2.0))
    se = math.sqrt((1.0 / (9.0 * n_valid)) + (cpk_f * cpk_f / (2.0 * (n_valid - 1))))
    lo = max(0.0, cpk_f - z * se)
    hi = cpk_f + z * se
    return f"[{lo:.3f}, {hi:.3f}]"


def _avg(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return float(sum(values) / len(values))


def _max_or_none(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return float(max(values))


def _top_oos_groups(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    usl: float,
    lsl: float,
    *,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """Rank groups by count of OOS rows (USL/LSL) for value_col."""
    if group_col not in df.columns or value_col not in df.columns:
        return []
    sub = df[[group_col, value_col]].replace([np.inf, -np.inf], np.nan).dropna()
    if sub.empty:
        return []
    bad = (sub[value_col] < lsl) | (sub[value_col] > usl)
    if not bad.any():
        return []
    agg = (
        sub.loc[bad]
        .groupby(group_col, dropna=False)
        .size()
        .sort_values(ascending=False)
        .head(top_n)
    )
    return [{"id": str(k), "oos_count": int(v)} for k, v in agg.items()]


def _spec_tightness_level(cpk: Optional[float]) -> Optional[str]:
    if cpk is None:
        return None
    c = float(cpk)
    if c >= 1.67:
        return "high_capability"
    if c >= 1.33:
        return "typical"
    return "improvement_needed"


def _state_from_value(value: Optional[float], *, warning: float, alarm: float, reverse: bool = False) -> str:
    """Map numeric KPI to Normal/Warning/Alarm state.

    reverse=False: higher is worse (e.g. OOC rate).
    reverse=True: lower is worse (e.g. Cpk).
    """
    if value is None:
        return "Info"
    if reverse:
        if value < alarm:
            return "Alarm"
        if value < warning:
            return "Warning"
        return "Normal"
    if value >= alarm:
        return "Alarm"
    if value >= warning:
        return "Warning"
    return "Normal"


def compute_summary(
    filtered_df: pd.DataFrame,
    workorder_spec: Optional[Dict[str, Any]],
    *,
    primary_feature: Optional[str] = None,
    workorder_master: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build summary for the integrated statistics table.
    Inputs:
      - filtered_df: same filter as analyze() (batch/refdes/part_type).
      - workorder_spec: from SessionStore, e.g. {"volume": {"usl","lsl","target"}, ...}, values are strings.
      - primary_feature: optional UI-selected measure (Volume/Area/Height) for Layer 5/7 focus.
      - workorder_master: optional work order / stencil context for Layer 6/7.
    Returns:
      - per_measure: { "Volume": { "cap", "dist", "normality", "yield_pct" }, ... }
      - relation: { "corr_vol_area", "corr_vol_height", "corr_area_height", "vol_area_mean", "vol_area_vs_height_diff" }
      - process: { "min_cpk", "min_cpk_measure", "overall_yield_pct", "verdict" }
    """
    per_measure: Dict[str, Dict[str, Any]] = {}
    workorder_spec = workorder_spec or {}
    workorder_master = workorder_master or {}
    series_by_measure: Dict[str, pd.Series] = {}
    spc_by_measure: Dict[str, Dict[str, Any]] = {}
    cusum_by_measure: Dict[str, Dict[str, Any]] = {}

    for spec_key, col in SPEC_KEY_TO_COL.items():
        if col not in filtered_df.columns:
            continue
        series = filtered_df[col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(series) < 2:
            continue
        series_by_measure[col] = series

        spec_entry = workorder_spec.get(spec_key)
        usl, lsl, target = _parse_spec(spec_entry)

        dist = DistributionEngine.compute_histogram(series)
        cap = None
        if usl is not None and lsl is not None:
            cap = CapabilityEngine.compute_capability(series, usl, lsl)
        normality = NormalityEngine.compute_normality(series)
        spc = SPCEngine.compute_imr(series, col)
        cusum = CUSUMEngine.compute_cusum(series, col, target=target, usl=usl, lsl=lsl)
        spc_by_measure[col] = spc
        cusum_by_measure[col] = cusum
        yield_pct = _yield_pct(series, usl, lsl) if (usl is not None and lsl is not None) else None
        defect: Dict[str, Any] = {
            "ppm_below_lsl": None,
            "ppm_above_usl": None,
            "ppm_total": None,
            "dpmo_feature": None,
            "zbench_st": None,
            "zbench_lt": None,
            "cpk_ci": "N/A",
            "cpk_ci_method": "N/A",
        }
        if usl is not None and lsl is not None:
            below, above, total, n_valid = _count_defects(series, usl, lsl)
            defect["ppm_below_lsl"] = _to_ppm(below, n_valid)
            defect["ppm_above_usl"] = _to_ppm(above, n_valid)
            defect["ppm_total"] = _to_ppm(total, n_valid)
            defect["dpmo_feature"] = _to_dpmo(total, n_valid)
            cap_stats = (cap or {}).get("statistics") or {}
            z_st, z_lt = _zbench_st_lt_from_cap(cap_stats)
            if (z_st is None or z_lt is None) and n_valid > 0:
                observed_defect_rate = float(total / n_valid)
                observed_z = _zbench_from_defect_rate(observed_defect_rate)
                if z_st is None:
                    z_st = observed_z
                if z_lt is None:
                    z_lt = observed_z
            defect["zbench_st"] = z_st
            defect["zbench_lt"] = z_lt
            defect["cpk_ci"] = _cpk_95ci_text(cap_stats.get("cpk"), n_valid)
            if defect["cpk_ci"] != "N/A":
                defect["cpk_ci_method"] = CPK_CI_METHOD

        per_measure[col] = {
            "cap": cap,
            "dist": dist,
            "normality": normality,
            "yield_pct": yield_pct,
            "target": target,
            "n": len(series),
            "defect": defect,
        }

    # --- Relations (only when both columns exist) ---
    relation: Dict[str, Any] = {}
    if "Volume" in filtered_df.columns and "Area" in filtered_df.columns:
        common = filtered_df[["Volume", "Area"]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(common) >= 2:
            relation["corr_vol_area"] = pearson_r_safe(common["Volume"], common["Area"])
    if "Volume" in filtered_df.columns and "Height" in filtered_df.columns:
        common = filtered_df[["Volume", "Height"]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(common) >= 2:
            relation["corr_vol_height"] = pearson_r_safe(common["Volume"], common["Height"])
    if "Area" in filtered_df.columns and "Height" in filtered_df.columns:
        common = filtered_df[["Area", "Height"]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(common) >= 2:
            relation["corr_area_height"] = pearson_r_safe(common["Area"], common["Height"])

    if "Volume" in filtered_df.columns and "Area" in filtered_df.columns:
        va = (filtered_df["Volume"] / filtered_df["Area"]).replace([np.inf, -np.inf], np.nan).dropna()
        if len(va) > 0:
            relation["vol_area_mean"] = float(va.mean())
            if "Height" in filtered_df.columns:
                common = filtered_df[["Volume", "Area", "Height"]].replace([np.inf, -np.inf], np.nan).dropna()
                common = common.loc[(common["Volume"] / common["Area"]).replace([np.inf, -np.inf], np.nan).notna()]
                if len(common) > 0:
                    va_mean = (common["Volume"] / common["Area"]).mean()
                    h_mean = common["Height"].mean()
                    relation["vol_area_vs_height_diff"] = float(va_mean - h_mean)
                else:
                    relation["vol_area_vs_height_diff"] = None
            else:
                relation["vol_area_vs_height_diff"] = None
        else:
            relation["vol_area_mean"] = None
            relation["vol_area_vs_height_diff"] = None
    else:
        relation["vol_area_mean"] = None
        relation["vol_area_vs_height_diff"] = None

    # --- Process summary ---
    min_cpk: Optional[float] = None
    min_cpk_measure: Optional[str] = None
    for col in MEASURE_COLS:
        pm = per_measure.get(col)
        if not isinstance(pm, dict):
            continue
        pm_cap = pm.get("cap")
        if not isinstance(pm_cap, dict):
            continue
        stats = pm_cap.get("statistics", {})
        cpk = stats.get("cpk")
        if cpk is not None and (min_cpk is None or cpk < min_cpk):
            min_cpk = float(cpk)
            min_cpk_measure = col

    # Overall yield: rows where every measure with spec is in spec
    cols_with_spec = []
    specs_by_col = {}
    for spec_key, col in SPEC_KEY_TO_COL.items():
        if col not in filtered_df.columns:
            continue
        spec_entry = workorder_spec.get(spec_key)
        usl, lsl = _parse_spec(spec_entry)[:2]
        if usl is not None and lsl is not None:
            cols_with_spec.append(col)
            specs_by_col[col] = (usl, lsl)
    if cols_with_spec:
        sub = filtered_df[cols_with_spec].replace([np.inf, -np.inf], np.nan).dropna()
        if len(sub) > 0:
            mask = pd.Series(True, index=sub.index)
            for col in cols_with_spec:
                usl, lsl = specs_by_col[col]
                mask &= (sub[col] >= lsl) & (sub[col] <= usl)
            overall_yield_pct = float(mask.sum() / len(sub) * 100.0)
        else:
            overall_yield_pct = None
    else:
        overall_yield_pct = None

    defect_combined: Dict[str, Any] = {
        "dpmo_combined_event": None,
        "dpmo_combined_board": None,
        "combined_defect_event_count": None,
        "combined_defect_board_count": None,
        "board_n": None,
        "opportunity_per_board": len(cols_with_spec) if cols_with_spec else 3,
        "opportunity_count_feature": None,
        "opportunity_count_combined_event": None,
        "opportunity_count_combined_board": None,
    }
    if cols_with_spec:
        sub = filtered_df[cols_with_spec].replace([np.inf, -np.inf], np.nan).dropna()
        board_n = _infer_board_n(filtered_df.loc[sub.index], len(sub))
        if len(sub) > 0 and board_n > 0:
            fail_mask = pd.DataFrame(index=sub.index)
            for col in cols_with_spec:
                usl, lsl = specs_by_col[col]
                fail_mask[col] = (sub[col] < lsl) | (sub[col] > usl)
            row_event_counts = fail_mask.sum(axis=1)
            event_count = int(row_event_counts.sum())
            board_count = int((row_event_counts > 0).sum())
            combined_event_opportunities = int(len(sub) * len(cols_with_spec))
            combined_board_opportunities = int(board_n)
            defect_combined = {
                "dpmo_combined_event": _to_dpmo(event_count, combined_event_opportunities),
                "dpmo_combined_board": _to_dpmo(board_count, combined_board_opportunities),
                "combined_defect_event_count": int(event_count),
                "combined_defect_board_count": int(board_count),
                "board_n": int(board_n),
                "opportunity_per_board": len(cols_with_spec),
                "opportunity_count_feature": int(len(sub)),
                "opportunity_count_combined_event": combined_event_opportunities,
                "opportunity_count_combined_board": combined_board_opportunities,
            }

    # --- Engineering Dashboard Layers ---
    alarm_rows: Dict[str, Dict[str, Any]] = {}
    ooc_rates: list[float] = []
    drift_ratios: list[float] = []
    cluster_counts: list[float] = []
    cpk_values: list[float] = []
    ppk_values: list[float] = []
    z_values: list[float] = []
    low_cpk_count = 0
    for col, pm in per_measure.items():
        cap_stats = ((pm.get("cap") or {}).get("statistics") or {})
        cpk = cap_stats.get("cpk")
        ppk = cap_stats.get("ppk")
        if cpk is not None:
            cpk_values.append(float(cpk))
            if float(cpk) < 1.33:
                low_cpk_count += 1
        if ppk is not None:
            ppk_values.append(float(ppk))

        defect = pm.get("defect") or {}
        z_lt = defect.get("zbench_lt")
        z_st = defect.get("zbench_st")
        if z_lt is not None:
            z_values.append(float(z_lt))
        elif z_st is not None:
            z_values.append(float(z_st))

        spc = spc_by_measure.get(col, {})
        spc_stats = spc.get("statistics") or {}
        spc_data = spc.get("data") or {}
        ooc_count = int(len(spc_data.get("out_of_control_indices") or []))
        spc_n = int(spc_stats.get("n") or pm.get("n") or 0)
        ooc_rate = _normalize_ooc_ratio(ooc_count, spc_n)
        if ooc_rate is not None:
            ooc_rates.append(ooc_rate)
        ooc_clusters = count_contiguous_ooc_clusters(spc_data.get("out_of_control_indices") or [])
        cluster_counts.append(float(ooc_clusters))

        cusum = cusum_by_measure.get(col, {})
        cusum_data = cusum.get("data") or {}
        cusum_stats = cusum.get("statistics") or {}
        cp_values = [float(v) for v in (cusum_data.get("values") or [])]
        cm_values = [float(v) for v in (cusum_data.get("values_cm") or [])]
        h_sigma = _maybe_float(cusum_stats.get("h_sigma"))
        max_drift_ratio = None
        if h_sigma is not None and h_sigma > 0 and (cp_values or cm_values):
            peak_cp = max(cp_values) if cp_values else 0.0
            peak_cm = max(cm_values) if cm_values else 0.0
            raw_ratio = max(abs(peak_cp), abs(peak_cm)) / h_sigma
            # Cap extreme ratios (e.g. 190,000%) to prevent UI eyesore while maintaining alarm state
            max_drift_ratio = min(10.0, float(raw_ratio))
            drift_ratios.append(max_drift_ratio)

        alarm_rows[col] = {
            "ooc_rate": ooc_rate,
            "ooc_count": ooc_count,
            "sample_n": spc_n if spc_n > 0 else None,
            "max_drift_ratio": max_drift_ratio,
            "anomaly_cluster_count": ooc_clusters,
            "cpk": float(cpk) if cpk is not None else None,
            "ppk": float(ppk) if ppk is not None else None,
        }

    alarm_ooc_rate = _max_or_none(ooc_rates)
    alarm_max_drift_ratio = _max_or_none(drift_ratios)
    alarm_cluster_count = _max_or_none(cluster_counts)

    driver_feature = min_cpk_measure
    if not driver_feature:
        for candidate in MEASURE_COLS:
            if candidate in per_measure:
                driver_feature = candidate
                break
    driver_pm = per_measure.get(driver_feature, {}) if driver_feature else {}
    driver_cap = (driver_pm.get("cap") or {}).get("statistics") or {}
    driver_dist = (driver_pm.get("dist") or {}).get("statistics") or {}

    info_sample_size = driver_pm.get("n")
    info_mean = driver_dist.get("mean")
    info_std = driver_cap.get("sigma_lt")
    if info_std is None:
        info_std = driver_dist.get("std")
    info_range = None
    if driver_dist.get("min") is not None and driver_dist.get("max") is not None:
        info_range = float(driver_dist["max"] - driver_dist["min"])

    layer_1_alarm = {
        "ooc_rate": alarm_ooc_rate,
        "ooc_rate_state": _state_from_value(alarm_ooc_rate, warning=0.001, alarm=0.1),
        "cpk_below_133_count": int(low_cpk_count),
        "cpk_below_133_state": "Alarm" if low_cpk_count > 0 else "Normal",
        "max_drift_ratio": alarm_max_drift_ratio,
        "max_drift_ratio_state": _state_from_value(alarm_max_drift_ratio, warning=0.8, alarm=1.0),
        "anomaly_cluster_count": int(alarm_cluster_count) if alarm_cluster_count is not None else None,
        "anomaly_cluster_state": _state_from_value(alarm_cluster_count, warning=1.0, alarm=3.0),
    }

    layer_2_kpi = {
        "avg_cpk": _avg(cpk_values),
        "avg_ppk": _avg(ppk_values),
        "yield_pct": overall_yield_pct,
        "dpmo": defect_combined.get("dpmo_combined_event"),
        "sigma_level": _avg(z_values),
    }

    layer_3_info = {
        "driver_feature": driver_feature,
        "sample_size": int(info_sample_size) if info_sample_size is not None else None,
        "mean": float(info_mean) if info_mean is not None else None,
        "std": float(info_std) if info_std is not None else None,
        "range": float(info_range) if info_range is not None else None,
    }

    info_col = primary_feature if (primary_feature and primary_feature in per_measure) else driver_feature
    info_sk = COL_TO_SPEC_KEY.get(info_col) if info_col else None
    info_usl: Optional[float] = None
    info_lsl: Optional[float] = None
    info_target: Optional[float] = None
    if info_sk:
        info_usl, info_lsl, info_target = _parse_spec(workorder_spec.get(info_sk))

    top_oos_refdes: List[Dict[str, Any]] = []
    top_oos_pad: List[Dict[str, Any]] = []
    if (
        info_col
        and info_col in filtered_df.columns
        and info_usl is not None
        and info_lsl is not None
    ):
        if "RefDes" in filtered_df.columns:
            top_oos_refdes = _top_oos_groups(filtered_df, info_col, "RefDes", info_usl, info_lsl)
        pad_col = next(
            (c for c in ("PadName", "Pad", "Footprint") if c in filtered_df.columns),
            None,
        )
        if pad_col:
            top_oos_pad = _top_oos_groups(filtered_df, info_col, pad_col, info_usl, info_lsl)

    cluster_ratio: Optional[float] = None
    if (
        alarm_cluster_count is not None
        and info_sample_size is not None
        and int(info_sample_size) > 0
    ):
        cluster_ratio = float(alarm_cluster_count) / float(info_sample_size)

    layer_4_defect_structure: Dict[str, Any] = {
        "top_oos_refdes": top_oos_refdes,
        "top_oos_pad": top_oos_pad,
        "abnormal_cluster_location": None,
        "cluster_ratio": cluster_ratio,
        "step_stencil_area_oos_rate": None,
    }

    layer_5_spec_analysis: Dict[str, Any] = {}
    if info_col and info_col in per_measure and info_usl is not None and info_lsl is not None:
        pm_i = per_measure[info_col]
        dist_i = (pm_i.get("dist") or {}).get("statistics") or {}
        cap_i = (pm_i.get("cap") or {}).get("statistics") or {}
        mean_i = dist_i.get("mean")
        std_i = cap_i.get("sigma_lt")
        if std_i is None:
            std_i = dist_i.get("std")
        
        f_usl = float(info_usl)
        f_lsl = float(info_lsl)
        f_target = safe_float(info_target)
        
        spec_width = f_usl - f_lsl
        mean_shift_pct: Optional[float] = None
        if mean_i is not None and f_target is not None and spec_width > 0:
            mean_shift_pct = float((float(mean_i) - f_target) / spec_width * 100.0)
        std_spec_ratio: Optional[float] = None
        if std_i is not None and spec_width > 0:
            std_spec_ratio = float(std_i) / spec_width
        ser = series_by_measure.get(info_col)
        oos_n = 0
        n_spec = 0
        oos_rate_spec: Optional[float] = None
        if ser is not None:
            _b, _a, tot, n_spec = _count_defects(ser, f_usl, f_lsl)
            oos_n = int(tot)
            if n_spec > 0:
                oos_rate_spec = float(tot) / float(n_spec)
        cpk_i = cap_i.get("cpk")
        if spec_width > 0:
            layer_5_spec_analysis = {
                "feature": info_col,
                "target": f_target,
                "spec_range": spec_width,
                "usl": f_usl,
                "lsl": f_lsl,
                "mean_shift_pct": mean_shift_pct,
                "std_spec_ratio": std_spec_ratio,
                "cp": cap_i.get("cp"),
                "cpk": cpk_i,
                "oos_count": oos_n,
                "oos_rate": oos_rate_spec,
                "spec_tightness_level": _spec_tightness_level(safe_float(cpk_i)),
            }

    _oos_n_spec = int(layer_5_spec_analysis.get("oos_count") or 0) if layer_5_spec_analysis else 0
    _diag = run_process_diagnosis(
        {
            "mean_shift_pct": layer_5_spec_analysis.get("mean_shift_pct") if layer_5_spec_analysis else None,
            "std_spec_ratio": layer_5_spec_analysis.get("std_spec_ratio") if layer_5_spec_analysis else None,
            "cp": layer_5_spec_analysis.get("cp") if layer_5_spec_analysis else None,
            "cpk": layer_5_spec_analysis.get("cpk") if layer_5_spec_analysis else None,
            "oos_rate": layer_5_spec_analysis.get("oos_rate") if layer_5_spec_analysis else None,
            "cluster_ratio": cluster_ratio,
            "step_stencil_oos_rate": layer_4_defect_structure.get("step_stencil_area_oos_rate"),
            "top_oos_refdes": top_oos_refdes,
            "top_oos_pad": top_oos_pad,
            "total_oos_count": _oos_n_spec,
            "abnormal_cluster_location": layer_4_defect_structure.get("abnormal_cluster_location"),
        }
    )
    layer_1_alarm["issue_type"] = _diag["issue_type"]
    layer_1_alarm["issue_type_display_zh"] = _diag["issue_type_display_zh"]
    layer_4_defect_structure["defect_pattern"] = _diag["defect_pattern"]
    layer_4_defect_structure["defect_pattern_zh"] = _diag["defect_pattern_zh"]
    layer_5_spec_analysis["process_diagnosis"] = dict(_diag["process_diagnosis_flags"])
    layer_8_diagnosis = {
        "issue_type": _diag["issue_type"],
        "issue_type_display_zh": _diag["issue_type_display_zh"],
        "root_cause_zh": _diag["root_cause_zh"],
        "recommended_action_zh": _diag["recommended_action_zh"],
        "priority": _diag["priority"],
        "process_diagnosis_flags": dict(_diag["process_diagnosis_flags"]),
        "thresholds_version": _diag["thresholds_version"],
    }

    layer_6_product_context = {
        k: workorder_master.get(k)
        for k in _WORKORDER_CONTEXT_KEYS
        if k in workorder_master
    }

    layer_7_engineering_info = {
        "sample_size": layer_3_info["sample_size"],
        "mean": layer_3_info["mean"],
        "std": layer_3_info["std"],
        "range": layer_3_info["range"],
        "usl": float(info_usl) if info_usl is not None else None,
        "lsl": float(info_lsl) if info_lsl is not None else None,
        "selected_feature": info_col,
        "stencil_thickness": workorder_master.get("stencil_thickness"),
    }

    if min_cpk is None:
        verdict = "—"
    elif min_cpk < 1.0:
        verdict = "不可接受"
    elif min_cpk >= 1.33:
        verdict = "可接受"
    else:
        verdict = "待改善"

    process = {
        "min_cpk": min_cpk,
        "min_cpk_measure": min_cpk_measure,
        "overall_yield_pct": overall_yield_pct,
        "verdict": verdict,
        "defect_combined": defect_combined,
        "dashboard_layers": {
            "layer_1_alarm": layer_1_alarm,
            "layer_2_kpi": layer_2_kpi,
            "layer_3_info": layer_3_info,
            "layer_4_defect_structure": layer_4_defect_structure,
            "layer_5_spec_analysis": layer_5_spec_analysis,
            "layer_6_product_context": layer_6_product_context,
            "layer_7_engineering_info": layer_7_engineering_info,
            "layer_8_diagnosis": layer_8_diagnosis,
            "per_feature_alarm": alarm_rows,
        },
    }

    return {
        "per_measure": per_measure,
        "relation": relation,
        "process": process,
    }
