import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from PySide6.QtCore import QObject, Signal

from app.analytics.spc_engine import SPCEngine
from app.analytics.capability_engine import CapabilityEngine
from app.analytics.distribution_engine import DistributionEngine
from app.analytics.pareto_engine import ParetoEngine
from app.analytics.spatial_engine import SpatialEngine
from app.analytics.comparison_engine import ComparisonEngine
from app.analytics.summary_engine import compute_summary
from app.analytics.scatter_engine import ScatterEngine
from app.analytics.quadrant_engine import QuadrantEngine
from app.analytics.bivariate_outlier_engine import BivariateOutlierEngine
from app.analytics.anomaly_3f_engine import Anomaly3FEngine
from app.analytics.consistency_3f_engine import Consistency3FEngine
from app.analytics.ewma_engine import EWMAEngine
from app.analytics.cusum_engine import CUSUMEngine
from app.analytics.run_chart_engine import RunChartEngine
from app.analytics.subgroup_engine import SubgroupEngine
from app.analytics.repeated_offender_engine import RepeatedOffenderEngine
from app.analytics.density_engine import DensityEngine
from app.analytics.xbar_r_engine import XbarREngine
from app.analytics.anova_engine import AnovaEngine
from app.analytics.pattern_recognition_engine import PatternRecognitionEngine
from app.analytics.correlation_matrix_engine import CorrelationMatrixEngine
from app.analytics.analysis_cards_engine import (
    compute_ooc_analysis,
    compute_shift_detection,
    compute_drift_detection,
    compute_outlier_analysis,
)
from app.analytics.parallel_coord_engine import ParallelCoordEngine
from app.analytics.pass_fail_engine import PassFailEngine
from app.data.session_store import SessionStore, _analysis_cache_key, filter_analysis_df
from app.analytics.analysis_payload_finalize import enrich_analysis_payload
from app.analytics.chart_registry import get_incompatible_reason
from app.utils.dataframe_utils import detect_order_col

logger = logging.getLogger(__name__)

SPEC_KEY_BY_COL = {"Volume": "volume", "Area": "area", "Height": "height"}
SINGLE_FEATURE_CHART_IDS = ["imr", "histogram_spec", "capability", "boxplot", "normality", "spatial_heatmap", "pareto"]
SUMMARY_MODE_MANAGER = "manager"
SUMMARY_MODE_ENGINEER = "engineer"
SUMMARY_MODES = {SUMMARY_MODE_MANAGER, SUMMARY_MODE_ENGINEER}

# 模式名稱映射 (Single source of truth for display labels)
MODE_LABELS = {
    SUMMARY_MODE_MANAGER: "管理版",
    SUMMARY_MODE_ENGINEER: "工程版",
}


def _board_ids_for_cusum(df: pd.DataFrame) -> Optional[pd.Series]:
    """Ordered board id series for CUSUM board-boundary reset; None if no board column."""
    board_col = next((c for c in ("BoardNo", "PanelId") if c in df.columns), None)
    if not board_col:
        return None
    order_col = detect_order_col(df)
    sorted_df = df.sort_values(order_col) if order_col else df
    return sorted_df[board_col]


def _pareto_with_parttype_fallback(
    df: pd.DataFrame,
    target_col: str,
    *,
    ucl: Optional[float],
    lcl: Optional[float],
    usl: Optional[float],
    lsl: Optional[float],
) -> Dict[str, Any]:
    if "PartType" in df.columns and (ucl is not None or lcl is not None or (usl and lsl)):
        pareto = ParetoEngine.compute_component_pareto(
            df, target_col, group_col="PartType",
            ucl=ucl, lcl=lcl, usl=usl, lsl=lsl,
        )
        if not (pareto.get("metadata", {}).get("is_valid") and pareto.get("data", {}).get("component_ids")):
            pareto = ParetoEngine.compute_pareto(df, target_col, usl=usl, lsl=lsl)
    else:
        pareto = ParetoEngine.compute_pareto(df, target_col, usl=usl, lsl=lsl)
    return pareto


def _incompatible_chart_payload(reason: str) -> Dict[str, Any]:
    return {
        "metadata": {"is_valid": False, "incompatible": True, "error": reason},
        "analysis_context": {},
    }


def _parse_workorder_spec_entry(spec: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return dict with usl, lsl, target as floats if parseable; else None."""
    if not spec or not isinstance(spec, dict):
        return None
    try:
        usl = float(spec.get("usl", "")) if spec.get("usl") else None
        lsl = float(spec.get("lsl", "")) if spec.get("lsl") else None
        target = None
        if spec.get("target"):
            try:
                target = float(spec["target"])
            except (TypeError, ValueError):
                pass
        return {"usl": usl, "lsl": lsl, "target": target}
    except (TypeError, ValueError):
        return None


def _compute_single_feature_analysis(
    df: pd.DataFrame,
    target_col: str,
    usl: Optional[float],
    lsl: Optional[float],
) -> Dict[str, Any]:
    """Compute SPC, Capability, Distribution for a single feature."""
    _order_col = detect_order_col(df)
    _df = df.sort_values(_order_col) if _order_col else df
    data_series = _df[target_col]

    spc = SPCEngine.compute_imr(data_series, target_col)
    cap = CapabilityEngine.compute_capability(data_series, usl, lsl)
    dist = DistributionEngine.compute_histogram(data_series)

    return {
        "spc": spc,
        "cap": cap,
        "dist": dist,
        "data_series": data_series,
    }


def _engine_failure_payload(chart_type: str, error: Exception) -> Dict[str, Any]:
    """Return a visible invalid payload so UI shows error instead of empty output."""
    return {
        "chart_type": chart_type,
        "data": {},
        "statistics": {},
        "metadata": {
            "is_valid": False,
            "error": f"計算失敗: {error}",
        },
        "analysis_context": {},
    }


def _compute_boxplot_for_df(df: pd.DataFrame, target_col: str) -> Dict[str, Any]:
    """Select the appropriate boxplot grouping strategy for ``df``.

    Decision logic:
    1. **Single RefDes** (sidebar filtered to one component): compare across
       boards (``BoardNo`` / ``PanelId``) to show cross-board variation.
    2. **Fallback**: group by ``RefDes``.

    PartType (足印) filtering is handled entirely by the sidebar 「元件類型」
    filter before analysis runs; no in-chart Part Type selector is needed.
    """
    board_col: Optional[str] = next(
        (c for c in ("BoardNo", "PanelId") if c in df.columns), None
    )
    refdes_unique: List[str] = (
        df["RefDes"].dropna().unique().tolist() if "RefDes" in df.columns else []
    )

    if len(refdes_unique) <= 1 and board_col is not None:
        # Filtered to a single component — show board-level variation instead
        result = ComparisonEngine.compute_boxplot(df, target_col, group_col=board_col)
        result["_grouping_mode"] = "board"
        result["_group_col"] = board_col
        return result

    group_col: str = "RefDes" if "RefDes" in df.columns else (board_col or "RefDes")
    result = ComparisonEngine.compute_boxplot(df, target_col, group_col=group_col)
    result["_grouping_mode"] = "refdes"
    result["_group_col"] = group_col
    return result


def _safe_compute_chart(
    chart_type: str,
    fn,
    *args,
    **kwargs,
) -> Dict[str, Any]:
    """Compute one chart safely; return invalid payload on failure."""
    try:
        result = fn(*args, **kwargs)
        if isinstance(result, dict):
            return result
        raise TypeError(f"{chart_type} 回傳型別錯誤: {type(result)}")
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
        logger.warning("%s computation failed: %s", chart_type, e)
        return _engine_failure_payload(chart_type, e)


class _AnalysisCancelled(Exception):
    """Raised internally when cancel_fn() returns True mid-computation."""


def _build_feature_parameters(
    filtered_df: pd.DataFrame,
    feature_cols: List[str],
    workorder_spec: Dict[str, Any],
    cancel_fn: Optional[Callable[[], bool]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    precomputed_parameters: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Build per-feature analysis bundles for chart-page feature switching."""
    from app.analytics.normality_engine import NormalityEngine

    parameters: Dict[str, Dict[str, Any]] = {}
    precomputed_parameters = precomputed_parameters or {}

    _board_ids = _board_ids_for_cusum(filtered_df)

    for i, col in enumerate(feature_cols):
        if progress_callback:
            progress_callback(60 + int((i / len(feature_cols)) * 30), f"分析輔助特徵: {col}")
        if col in precomputed_parameters:
            parameters[col] = precomputed_parameters[col]
            continue
        col_spec = _parse_workorder_spec_entry(
            workorder_spec.get(SPEC_KEY_BY_COL.get(col, col.lower()))
        )
        col_usl = col_spec.get("usl") if col_spec else None
        col_lsl = col_spec.get("lsl") if col_spec else None
        col_target = col_spec.get("target") if col_spec else None

        param_analysis = _compute_single_feature_analysis(filtered_df, col, col_usl, col_lsl)
        param_spc = param_analysis["spc"]
        param_cap = param_analysis["cap"]
        param_dist = param_analysis["dist"]
        param_spc["analysis_context"] = {"target_col": col, "unit": None}
        param_cap["analysis_context"] = {"target_col": col, "unit": None}
        param_dist["analysis_context"] = {"target_col": col, "unit": None}

        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_box = _compute_boxplot_for_df(filtered_df, col)
        param_box["analysis_context"] = {"target_col": col, "unit": None}

        param_data_series = param_analysis["data_series"]
        param_ucl = (param_spc.get("statistics") or {}).get("ucl")
        param_lcl = (param_spc.get("statistics") or {}).get("lcl")
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_normality = _safe_compute_chart(
            "Normality", NormalityEngine.compute_normality, param_data_series
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_density = _safe_compute_chart(
            "Density", DensityEngine.compute_univariate_density, param_data_series, col
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_ewma = _safe_compute_chart(
            "EWMA", EWMAEngine.compute_ewma, param_data_series, col
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_cusum = _safe_compute_chart(
            "CUSUM", CUSUMEngine.compute_cusum,
            param_data_series, col, board_ids=_board_ids,
            target=col_target, usl=col_usl, lsl=col_lsl,
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_run_chart = _safe_compute_chart(
            "RunChart", RunChartEngine.compute_run_chart, param_data_series, col
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_xbar_r = _safe_compute_chart(
            "XbarR", XbarREngine.compute_xbar_r, filtered_df, col
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_anova = _safe_compute_chart(
            "ANOVA", AnovaEngine.compute_one_way, filtered_df, col, group_col="PartType"
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_pattern = _safe_compute_chart(
            "PatternRecognition", PatternRecognitionEngine.compute_nelson, param_data_series, col
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_subgroup = _safe_compute_chart(
            "Subgroup", SubgroupEngine.compute_subgroup,
            filtered_df, col, group_col="PartType", usl=col_usl, lsl=col_lsl,
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_repeated_offender = _safe_compute_chart(
            "RepeatedOffender", RepeatedOffenderEngine.compute_repeated_offender,
            filtered_df, col, usl=col_usl, lsl=col_lsl,
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_pareto = _safe_compute_chart(
            "Pareto", _pareto_with_parttype_fallback,
            filtered_df, col,
            ucl=param_ucl, lcl=param_lcl, usl=col_usl, lsl=col_lsl,
        )
        if cancel_fn and cancel_fn():
            raise _AnalysisCancelled()
        param_spatial = _safe_compute_chart(
            "Spatial", SpatialEngine.compute_heatmap,
            filtered_df, col, mode=SpatialEngine.MODE_VALUE,
            ucl=param_ucl, lcl=param_lcl, usl=col_usl, lsl=col_lsl,
        )
        feature_payload = {
            "spc": param_spc,
            "cusum": param_cusum,
            "ewma": param_ewma,
            "bivariate_outlier": {},
        }
        param_ooc_analysis = _safe_compute_chart(
            "OOCAnalysis", compute_ooc_analysis, feature_payload
        )
        param_shift_detection = _safe_compute_chart(
            "ShiftDetection", compute_shift_detection, feature_payload
        )
        param_drift_detection = _safe_compute_chart(
            "DriftDetection", compute_drift_detection, feature_payload
        )
        param_outlier_analysis = _safe_compute_chart(
            "OutlierAnalysis", compute_outlier_analysis, feature_payload
        )
        _ctx = {"target_col": col, "unit": None}
        for d in (
            param_normality,
            param_density,
            param_ewma,
            param_cusum,
            param_run_chart,
            param_xbar_r,
            param_anova,
            param_pattern,
            param_ooc_analysis,
            param_shift_detection,
            param_drift_detection,
            param_outlier_analysis,
            param_subgroup,
            param_repeated_offender,
            param_pareto,
            param_spatial,
        ):
            if isinstance(d, dict):
                d["analysis_context"] = _ctx
        parameters[col] = {
            "spc": param_spc,
            "xbar_r": param_xbar_r,
            "cap": param_cap,
            "dist": param_dist,
            "box": param_box,
            "normality": param_normality,
            "density": param_density,
            "ewma": param_ewma,
            "cusum": param_cusum,
            "run_chart": param_run_chart,
            "anova_parttype": param_anova,
            "pattern_recognition": param_pattern,
            "ooc_analysis": param_ooc_analysis,
            "shift_detection": param_shift_detection,
            "drift_detection": param_drift_detection,
            "outlier_analysis": param_outlier_analysis,
            "subgroup": param_subgroup,
            "repeated_offender": param_repeated_offender,
            "pareto": param_pareto,
            "spatial": param_spatial,
        }

    return parameters


def compute_analysis_payload(
    filtered_df: pd.DataFrame,
    selected_features: List[str],
    usl: float,
    lsl: float,
    target: float,
    workorder_spec: Optional[Dict[str, Any]] = None,
    workorder_master: Optional[Dict[str, Any]] = None,
    cancel_fn: Optional[Callable[[], bool]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Pure computation: build analysis payload from filtered dataframe and params.
    Returns (payload, None) on success, (None, error_message) on failure.
    Used by AnalysisWorker; does not touch SessionStore or emit signals.

    Multi-parameter support: When n==1, also analyze other available features
    (Volume/Area/Height) and store in payload["parameters"] for UI switching.
    """
    workorder_spec = workorder_spec or {}
    workorder_master = workorder_master or {}
    n = len(selected_features)
    primary_for_summary = selected_features[0] if selected_features else None
    try:
        payload: Dict[str, Any] = {
            "selected_features": selected_features,
            "summary": compute_summary(
                filtered_df,
                workorder_spec,
                primary_feature=primary_for_summary,
                workorder_master=workorder_master,
            ),
        }
        if progress_callback:
            progress_callback(10, "彙總核心數據...")
        if n == 1:
            target_col = selected_features[0]

            # Compute main analysis for selected feature
            main_analysis = _compute_single_feature_analysis(filtered_df, target_col, usl, lsl)
            spc = main_analysis["spc"]
            cap = main_analysis["cap"]
            dist = main_analysis["dist"]
            data_series = main_analysis["data_series"]
            ucl = (spc.get("statistics") or {}).get("ucl")
            lcl = (spc.get("statistics") or {}).get("lcl")
            pareto = _pareto_with_parttype_fallback(
                filtered_df, target_col,
                ucl=ucl, lcl=lcl, usl=usl, lsl=lsl,
            )
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            spatial = SpatialEngine.compute_heatmap(
                filtered_df, target_col,
                mode=SpatialEngine.MODE_VALUE,
                ucl=ucl, lcl=lcl, usl=usl, lsl=lsl,
            )
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            box = _compute_boxplot_for_df(filtered_df, target_col)
            from app.analytics.normality_engine import NormalityEngine
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            normality = NormalityEngine.compute_normality(data_series)
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            density = DensityEngine.compute_univariate_density(data_series, target_col)
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            ewma = EWMAEngine.compute_ewma(data_series, target_col)
            # Derive board_ids for CUSUM board-boundary reset
            _board_ids = _board_ids_for_cusum(filtered_df)
            # Resolve per-feature spec for CUSUM target (stencil thickness for Height, etc.)
            _cusum_spec = _parse_workorder_spec_entry(
                workorder_spec.get(SPEC_KEY_BY_COL.get(target_col, target_col.lower()))
            )
            _cusum_target = (_cusum_spec.get("target") if _cusum_spec else None) or target
            _cusum_usl = (_cusum_spec.get("usl") if _cusum_spec else None) or usl
            _cusum_lsl = (_cusum_spec.get("lsl") if _cusum_spec else None) or lsl
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            cusum = CUSUMEngine.compute_cusum(
                data_series, target_col, board_ids=_board_ids,
                target=_cusum_target, usl=_cusum_usl, lsl=_cusum_lsl,
            )
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            run_chart = RunChartEngine.compute_run_chart(data_series, target_col)
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            xbar_r = XbarREngine.compute_xbar_r(filtered_df, target_col)
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            anova_parttype = AnovaEngine.compute_one_way(filtered_df, target_col, group_col="PartType")
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            pattern_recognition = PatternRecognitionEngine.compute_nelson(data_series, target_col)
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            subgroup = SubgroupEngine.compute_subgroup(filtered_df, target_col, group_col="PartType", usl=usl, lsl=lsl)
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            repeated_offender = RepeatedOffenderEngine.compute_repeated_offender(filtered_df, target_col, usl=usl, lsl=lsl)
            feature_payload = {
                "spc": spc,
                "cusum": cusum,
                "ewma": ewma,
                "bivariate_outlier": {},
            }
            ooc_analysis = compute_ooc_analysis(feature_payload)
            shift_detection = compute_shift_detection(feature_payload)
            drift_detection = compute_drift_detection(feature_payload)
            outlier_analysis = compute_outlier_analysis(feature_payload)
            analysis_context = {"target_col": target_col, "unit": None}
            for d in (
                spc,
                xbar_r,
                cap,
                dist,
                pareto,
                spatial,
                box,
                normality,
                density,
                ewma,
                cusum,
                run_chart,
                anova_parttype,
                pattern_recognition,
                ooc_analysis,
                shift_detection,
                drift_detection,
                outlier_analysis,
                subgroup,
                repeated_offender,
            ):
                if isinstance(d, dict):
                    d["analysis_context"] = analysis_context
            selected_parameter_bundle = {
                "spc": spc,
                "xbar_r": xbar_r,
                "cap": cap,
                "dist": dist,
                "box": box,
                "normality": normality,
                "density": density,
                "ewma": ewma,
                "cusum": cusum,
                "run_chart": run_chart,
                "anova_parttype": anova_parttype,
                "pattern_recognition": pattern_recognition,
                "ooc_analysis": ooc_analysis,
                "shift_detection": shift_detection,
                "drift_detection": drift_detection,
                "outlier_analysis": outlier_analysis,
                "subgroup": subgroup,
                "repeated_offender": repeated_offender,
                "pareto": pareto,
                "spatial": spatial,
            }
            payload["spc"] = spc
            payload["xbar_r"] = xbar_r
            payload["cap"] = cap
            payload["dist"] = dist
            payload["pareto"] = pareto
            payload["spatial"] = spatial
            payload["box"] = box
            payload["normality"] = normality
            payload["density"] = density
            payload["ewma"] = ewma
            payload["cusum"] = cusum
            payload["run_chart"] = run_chart
            payload["anova_parttype"] = anova_parttype
            payload["pattern_recognition"] = pattern_recognition
            payload["ooc_analysis"] = ooc_analysis
            payload["shift_detection"] = shift_detection
            payload["drift_detection"] = drift_detection
            payload["outlier_analysis"] = outlier_analysis
            payload["subgroup"] = subgroup
            payload["repeated_offender"] = repeated_offender
            payload["scatter_spec"] = None
            payload["correlation_matrix"] = None
            payload["correlation_heatmap"] = None
            payload["quadrant"] = None
            payload["bivariate_outlier"] = None
            payload["anomaly_3f"] = None
            payload["consistency_3f"] = None
            payload["parallel_coord"] = None
            payload["pass_fail_matrix"] = None
            if progress_callback:
                progress_callback(50, "計算單特徵高級分析...")

            # Multi-parameter support: analyze all available features so UI can switch
            # without re-running analysis.
            _feature_cols = [c for c in ["Volume", "Area", "Height"] if c in filtered_df.columns]
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            payload["parameters"] = _build_feature_parameters(
                filtered_df, _feature_cols, workorder_spec, cancel_fn=cancel_fn,
                progress_callback=progress_callback,
                precomputed_parameters={target_col: selected_parameter_bundle},
            )

            # Pre-compute dual-feature combinations so chart page can enable dual charts
            # when the user selects 2 display features without re-running the analysis.
            dual_parameters: dict[str, dict] = {}
            for _di, _cx in enumerate(_feature_cols):
                for _cy in _feature_cols[_di + 1:]:
                    _spec_x = _parse_workorder_spec_entry(
                        workorder_spec.get(SPEC_KEY_BY_COL.get(_cx, _cx.lower()))
                    )
                    _spec_y = _parse_workorder_spec_entry(
                        workorder_spec.get(SPEC_KEY_BY_COL.get(_cy, _cy.lower()))
                    )
                    _pair_key = f"{_cx}+{_cy}"
                    dual_parameters[_pair_key] = {
                        "scatter_spec": _safe_compute_chart(
                            "ScatterSpec",
                            ScatterEngine.compute_scatter_spec,
                            filtered_df, _cx, _cy, _spec_x, _spec_y,
                        ),
                        "correlation_matrix": _safe_compute_chart(
                            "CorrelationMatrix",
                            CorrelationMatrixEngine.compute_matrix,
                            filtered_df[[_cx, _cy]],
                            [_cx, _cy],
                        ),
                        "correlation_heatmap": _safe_compute_chart(
                            "CorrelationHeatmap",
                            CorrelationMatrixEngine.compute_matrix,
                            filtered_df[[_cx, _cy]],
                            [_cx, _cy],
                        ),
                        "quadrant": _safe_compute_chart(
                            "Quadrant",
                            QuadrantEngine.compute_quadrant,
                            filtered_df, _cx, _cy, _spec_x, _spec_y,
                        ),
                        "bivariate_outlier": _safe_compute_chart(
                            "BivariateOutlier",
                            BivariateOutlierEngine.compute_bivariate_outlier,
                            filtered_df, _cx, _cy,
                        ),
                        "density": _safe_compute_chart(
                            "Density",
                            DensityEngine.compute_density,
                            filtered_df, _cx, _cy,
                        ),
                    }
            payload["dual_parameters"] = dual_parameters

            # Pre-compute triple-feature combination for when user selects all 3 display features.
            triple_parameters: dict[str, Any] = {}
            if len(_feature_cols) == 3:
                _spec_by_col = {
                    _c: workorder_spec.get(SPEC_KEY_BY_COL.get(_c, _c.lower()), {}) or {}
                    for _c in _feature_cols
                }
                triple_parameters = {
                    "anomaly_3f": _safe_compute_chart(
                        "Anomaly3F",
                        Anomaly3FEngine.compute_anomaly_3f,
                        filtered_df, _feature_cols,
                    ),
                    "consistency_3f": _safe_compute_chart(
                        "Consistency3F",
                        Consistency3FEngine.compute_consistency_3f,
                        filtered_df, cols=_feature_cols,
                    ),
                    "parallel_coord": _safe_compute_chart(
                        "ParallelCoord",
                        ParallelCoordEngine.compute_parallel_coord,
                        filtered_df, _feature_cols,
                    ),
                    "pass_fail_matrix": _safe_compute_chart(
                        "PassFail",
                        PassFailEngine.compute_pass_fail,
                        filtered_df, _feature_cols, _spec_by_col,
                    ),
                }
            payload["triple_parameters"] = triple_parameters

        elif n == 2:
            col_x, col_y = selected_features[0], selected_features[1]
            spec_x = _parse_workorder_spec_entry(workorder_spec.get(SPEC_KEY_BY_COL.get(col_x, col_x.lower())))
            spec_y = _parse_workorder_spec_entry(workorder_spec.get(SPEC_KEY_BY_COL.get(col_y, col_y.lower())))
            scatter = ScatterEngine.compute_scatter_spec(filtered_df, col_x, col_y, spec_x, spec_y)
            corr_matrix = CorrelationMatrixEngine.compute_matrix(filtered_df, [col_x, col_y])
            corr_heatmap = CorrelationMatrixEngine.compute_matrix(filtered_df, [col_x, col_y])
            quadrant = QuadrantEngine.compute_quadrant(filtered_df, col_x, col_y, spec_x, spec_y)
            bivariate = BivariateOutlierEngine.compute_bivariate_outlier(filtered_df, col_x, col_y)
            density = DensityEngine.compute_density(filtered_df, col_x, col_y)
            # For charts that allow >=1 feature, use first selected feature as driver.
            driver_series = filtered_df[col_x].dropna()
            driver_spc = SPCEngine.compute_imr(driver_series, col_x)
            driver_ewma = EWMAEngine.compute_ewma(driver_series, col_x)
            driver_cusum = CUSUMEngine.compute_cusum(
                driver_series,
                col_x,
                target=(spec_x.get("target") if spec_x else None),
                usl=(spec_x.get("usl") if spec_x else None),
                lsl=(spec_x.get("lsl") if spec_x else None),
            )
            driver_xbar_r = XbarREngine.compute_xbar_r(filtered_df, col_x)
            driver_anova = AnovaEngine.compute_one_way(filtered_df, col_x, group_col="PartType")
            driver_pattern = PatternRecognitionEngine.compute_nelson(driver_series, col_x)
            driver_outlier_bridge = {"bivariate_outlier": bivariate, "spc": driver_spc, "cusum": driver_cusum, "ewma": driver_ewma}
            ooc_analysis = compute_ooc_analysis(driver_outlier_bridge)
            shift_detection = compute_shift_detection(driver_outlier_bridge)
            drift_detection = compute_drift_detection(driver_outlier_bridge)
            outlier_analysis = compute_outlier_analysis(driver_outlier_bridge)
            _incompatible = _incompatible_chart_payload(
                get_incompatible_reason("imr", selected_features)
                or "此圖表僅支援單一特徵，請在元件/量測選定頁選擇一個特徵。",
            )
            payload["spc"] = _incompatible
            payload["xbar_r"] = driver_xbar_r
            payload["cap"] = _incompatible
            payload["dist"] = _incompatible
            payload["pareto"] = _incompatible
            payload["spatial"] = _incompatible
            payload["box"] = _incompatible
            payload["normality"] = _incompatible
            payload["scatter_spec"] = scatter
            payload["correlation_matrix"] = corr_matrix
            payload["correlation_heatmap"] = corr_heatmap
            payload["anova_parttype"] = driver_anova
            payload["quadrant"] = quadrant
            payload["bivariate_outlier"] = bivariate
            payload["density"] = density
            payload["ewma"] = driver_ewma
            payload["cusum"] = driver_cusum
            payload["run_chart"] = RunChartEngine.compute_run_chart(driver_series, col_x)
            payload["pattern_recognition"] = driver_pattern
            payload["ooc_analysis"] = ooc_analysis
            payload["shift_detection"] = shift_detection
            payload["drift_detection"] = drift_detection
            payload["outlier_analysis"] = outlier_analysis
            payload["subgroup"] = _incompatible
            payload["repeated_offender"] = _incompatible
            payload["anomaly_3f"] = None
            payload["consistency_3f"] = None
            payload["parallel_coord"] = None
            payload["pass_fail_matrix"] = None
            # Build per-feature bundles for multi-feature tabs (histogram/normality/boxplot)
            # and for future 3F-parallel continuity if user expands selection later.
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            payload["parameters"] = _build_feature_parameters(
                filtered_df, selected_features, workorder_spec, cancel_fn=cancel_fn
            )
        else:
            anomaly = Anomaly3FEngine.compute_anomaly_3f(filtered_df, selected_features)
            consistency = Consistency3FEngine.compute_consistency_3f(filtered_df, cols=selected_features)
            parallel_coord = ParallelCoordEngine.compute_parallel_coord(filtered_df, selected_features)
            spec_by_col = {col: workorder_spec.get(SPEC_KEY_BY_COL.get(col, col.lower()), {}) or {} for col in selected_features}
            pass_fail_matrix = PassFailEngine.compute_pass_fail(filtered_df, selected_features, spec_by_col)
            corr_matrix = CorrelationMatrixEngine.compute_matrix(filtered_df, selected_features)
            corr_heatmap = CorrelationMatrixEngine.compute_matrix(filtered_df, selected_features)
            primary_col = selected_features[0]
            primary_series = filtered_df[primary_col].dropna()
            primary_spec = _parse_workorder_spec_entry(
                workorder_spec.get(SPEC_KEY_BY_COL.get(primary_col, primary_col.lower()))
            )
            primary_spc = SPCEngine.compute_imr(primary_series, primary_col)
            primary_ewma = EWMAEngine.compute_ewma(primary_series, primary_col)
            primary_cusum = CUSUMEngine.compute_cusum(
                primary_series,
                primary_col,
                target=(primary_spec.get("target") if primary_spec else None),
                usl=(primary_spec.get("usl") if primary_spec else None),
                lsl=(primary_spec.get("lsl") if primary_spec else None),
            )
            primary_xbar_r = XbarREngine.compute_xbar_r(filtered_df, primary_col)
            primary_anova = AnovaEngine.compute_one_way(filtered_df, primary_col, group_col="PartType")
            primary_pattern = PatternRecognitionEngine.compute_nelson(primary_series, primary_col)
            primary_bridge = {
                "spc": primary_spc,
                "ewma": primary_ewma,
                "cusum": primary_cusum,
                "bivariate_outlier": {},
            }
            ooc_analysis = compute_ooc_analysis(primary_bridge)
            shift_detection = compute_shift_detection(primary_bridge)
            drift_detection = compute_drift_detection(primary_bridge)
            outlier_analysis = compute_outlier_analysis(primary_bridge)
            _incompatible = _incompatible_chart_payload(
                get_incompatible_reason("imr", selected_features) or "此圖表需單一或雙特徵。",
            )
            payload["spc"] = _incompatible
            payload["xbar_r"] = primary_xbar_r
            payload["cap"] = _incompatible
            payload["dist"] = _incompatible
            payload["pareto"] = _incompatible
            payload["spatial"] = _incompatible
            payload["box"] = _incompatible
            payload["normality"] = _incompatible
            payload["scatter_spec"] = None
            payload["correlation_matrix"] = corr_matrix
            payload["correlation_heatmap"] = corr_heatmap
            payload["anova_parttype"] = primary_anova
            payload["quadrant"] = None
            payload["bivariate_outlier"] = None
            payload["density"] = _incompatible
            payload["ewma"] = primary_ewma
            payload["cusum"] = primary_cusum
            payload["run_chart"] = RunChartEngine.compute_run_chart(primary_series, primary_col)
            payload["pattern_recognition"] = primary_pattern
            payload["ooc_analysis"] = ooc_analysis
            payload["shift_detection"] = shift_detection
            payload["drift_detection"] = drift_detection
            payload["outlier_analysis"] = outlier_analysis
            payload["subgroup"] = _incompatible
            payload["repeated_offender"] = _incompatible
            payload["anomaly_3f"] = anomaly
            payload["consistency_3f"] = consistency
            payload["parallel_coord"] = parallel_coord
            payload["pass_fail_matrix"] = pass_fail_matrix
            # Keep per-feature bundles available even when analysis starts from n==3.
            # Required for 3F parallel charts and distribution/normality multi-feature rendering.
            if cancel_fn and cancel_fn():
                raise _AnalysisCancelled()
            payload["parameters"] = _build_feature_parameters(
                filtered_df, selected_features, workorder_spec, cancel_fn=cancel_fn
            )
        if progress_callback:
            progress_callback(95, "正在完成分析...")
        enrich_analysis_payload(payload)
        if progress_callback:
            progress_callback(100, "分析完成")
        return (payload, None)
    except _AnalysisCancelled:
        raise
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
        logger.exception("compute_analysis_payload failed for features=%s", selected_features)
        return (None, f"計算引擎發生錯誤: {str(e)}")


class ChartAnalysisViewModel(QObject):
    """
    ViewModel handling UI actions to computation logic.
    Supports single-, dual-, and triple-feature selection; branches to appropriate engines.
    """
    data_ready = Signal(dict)
    error_occurred = Signal(str)
    summary_mode_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.store = SessionStore()
        self._summary_mode = SUMMARY_MODE_MANAGER

    @property
    def summary_mode(self) -> str:
        """Current summary display mode: manager or engineer."""
        return self._summary_mode

    def set_summary_mode(self, mode: str) -> None:
        """
        Set summary display mode and notify subscribers.
        Ignores unknown values and duplicate assignments.
        """
        if mode not in SUMMARY_MODES or mode == self._summary_mode:
            return
        self._summary_mode = mode
        self.summary_mode_changed.emit(mode)

    def analyze(
        self,
        selected_features: List[str],
        usl: float = 120.0,
        lsl: float = 80.0,
        target: float = 100.0,
        batch: str = "全部 (All)",
        refdes: str = "全部 (All)",
        part_type: str = "全部 (All)",
        workorder_spec: Optional[Dict[str, Any]] = None,
    ) -> bool:
        workorder_spec = workorder_spec or {}
        df = self.store.get_analysis_df()

        if df is None or df.empty:
            self.error_occurred.emit("尚未載入任何資料 (No Data Loaded). 請確認量測檔案是否上傳成功。")
            return False

        for col in selected_features:
            if col not in df.columns:
                self.error_occurred.emit(f"無法找到分析目標欄位 (Column '{col}' not found in data).")
                return False

        product = getattr(self.store, "filter_product", None)
        time_start = getattr(self.store, "filter_time_start", None)
        time_end = getattr(self.store, "filter_time_end", None)
        line = getattr(self.store, "filter_line", None)
        filtered_df = filter_analysis_df(
            df, batch, refdes, part_type,
            product=product, time_start=time_start, time_end=time_end, line=line,
        )
        if filtered_df.empty:
            self.error_occurred.emit("此過濾條件下無資料 (No Data Found for these conditions).")
            return False

        self.store.selected_features = list(selected_features)

        cache_key = _analysis_cache_key(
            selected_features, batch, refdes, part_type,
            product=product, time_start=time_start, time_end=time_end, line=line,
        )
        cached = self.store._analysis_cache.get(cache_key)
        if cached is not None:
            self.store.last_analysis_payload = cached
            self.data_ready.emit(cached)
            return True

        # Delegate all computation to the pure function — single source of truth
        effective_spec = workorder_spec or getattr(self.store, "workorder_spec", None) or {}
        wo_master = getattr(self.store, "workorder_master", None) or {}
        payload, err = compute_analysis_payload(
            filtered_df, selected_features, usl, lsl, target,
            workorder_spec=effective_spec,
            workorder_master=wo_master,
        )
        if err:
            logger.exception("analyze() failed for features=%s", selected_features)
            self.error_occurred.emit(err)
            return False

        self.store._analysis_cache[cache_key] = payload
        self.store.last_analysis_payload = payload
        self.data_ready.emit(payload)
        return True
