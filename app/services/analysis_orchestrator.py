from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from app.data.session_store import SessionStore, _analysis_cache_key, filter_analysis_df
from app.services.analysis_context import AnalysisFilterContext, AnalysisRunContext
from app.services.spec_resolver import can_run_analysis, resolve_workorder_spec
from app.utils.constants import RANGE_SPECIFY

STATUS_MISSING_FEATURE = "missing_feature"
STATUS_IDLE_NO_DATA = "idle_no_data"
STATUS_ERROR = "error"
STATUS_CACHED = "cached"
STATUS_READY = "ready"


@dataclass
class AnalysisPreparation:
    status: str
    message: str = ""
    selected_features: List[str] = field(default_factory=list)
    filtered_df: Optional[pd.DataFrame] = None
    usl: float = 0.0
    lsl: float = 0.0
    target: float = 0.0
    batch: str = ""
    refdes: str = ""
    part_type: str = ""
    cache_key: str = ""
    cached_payload: Optional[Dict[str, Any]] = None
    filter_context: Optional[AnalysisFilterContext] = None
    run_context: Optional[AnalysisRunContext] = None


class AnalysisOrchestrator:
    """Coordinates analysis preparation/cache responsibilities away from UI widgets."""

    @staticmethod
    def _resolve_store_workorder_spec(
        store: SessionStore,
        manual_workorder_spec: Dict[str, Dict[str, str]],
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        product_name = (store.workorder_master or {}).get("product_name") or ""
        if product_name:
            ok, msg = can_run_analysis(product_name)
            if not ok:
                return None, msg or "無法分析"
            workorder_spec, err = resolve_workorder_spec(product_name)
            if err or workorder_spec is None:
                return None, err or "規格解析失敗"
            store.workorder_spec = workorder_spec
            return workorder_spec, None

        workorder_spec = getattr(store, "workorder_spec", None) or {}
        if not workorder_spec:
            workorder_spec = dict(manual_workorder_spec or {})
            store.workorder_spec = workorder_spec
        return workorder_spec, None

    @staticmethod
    def _resolve_primary_limits(
        workorder_spec: Dict[str, Any],
        primary_feature: str,
    ) -> tuple[Optional[tuple[float, float, float]], Optional[str]]:
        spec_key = primary_feature.lower()
        spec_entry = (workorder_spec or {}).get(spec_key) or {}
        try:
            usl_raw = spec_entry.get("usl")
            lsl_raw = spec_entry.get("lsl")
            target_raw = spec_entry.get("target")
            if usl_raw is None and lsl_raw is None:
                return None, f"分析失敗: 工單規格缺少 {primary_feature} 的 USL/LSL，請先建立規格。"
            usl = float(usl_raw) if usl_raw is not None else 0.0
            lsl = float(lsl_raw) if lsl_raw is not None else 0.0
            target = float(target_raw) if target_raw is not None else 0.0
            if not target and (usl or lsl):
                target = (usl + lsl) / 2.0
            elif not target:
                target = 100.0
            return (usl, lsl, target), None
        except (TypeError, ValueError):
            return None, "分析失敗: 工單規格 (USL/LSL) 必須為有效數字"

    @staticmethod
    def _build_filter_context(
        *,
        range_mode: str,
        board_specify: str,
        refdes: str,
        part_type: str,
        optional_filters: Dict[str, Any],
    ) -> AnalysisFilterContext:
        batch = board_specify if range_mode == RANGE_SPECIFY else range_mode
        return AnalysisFilterContext(
            batch=batch,
            refdes=refdes,
            part_type=part_type,
            product=optional_filters.get("product"),
            time_start=optional_filters.get("time_start"),
            time_end=optional_filters.get("time_end"),
            line=optional_filters.get("line"),
        )

    def prepare_refresh(
        self,
        *,
        store: SessionStore,
        selected_features: List[str],
        range_mode: str,
        board_specify: str,
        refdes: str,
        part_type: str,
        optional_filters: Dict[str, Any],
        manual_workorder_spec: Dict[str, Dict[str, str]],
    ) -> AnalysisPreparation:
        selected = list(selected_features or [])
        if not selected:
            return AnalysisPreparation(
                status=STATUS_MISSING_FEATURE,
                message="請至少選擇一個量測特徵 (Please select at least one feature).",
            )

        workorder_spec, spec_err = self._resolve_store_workorder_spec(store, manual_workorder_spec)
        if spec_err:
            return AnalysisPreparation(status=STATUS_ERROR, message=spec_err, selected_features=selected)

        limits, limits_err = self._resolve_primary_limits(workorder_spec or {}, selected[0])
        if limits_err:
            return AnalysisPreparation(status=STATUS_ERROR, message=limits_err, selected_features=selected)
        usl, lsl, target = limits or (0.0, 0.0, 100.0)

        filters = self._build_filter_context(
            range_mode=range_mode,
            board_specify=board_specify,
            refdes=refdes,
            part_type=part_type,
            optional_filters=optional_filters,
        )
        spec_token = store.spec_cache_token(getattr(store, "workorder_spec", None))
        run_context = AnalysisRunContext(
            selected_features=tuple(selected),
            filters=filters,
            spec_version=spec_token,
        )

        store.filter_product = filters.product
        store.filter_time_start = filters.time_start
        store.filter_time_end = filters.time_end
        store.filter_line = filters.line
        store.filter_batch = filters.batch
        store.filter_refdes = filters.refdes
        store.filter_part_type = filters.part_type

        df = store.get_analysis_df()
        if df is None or df.empty:
            return AnalysisPreparation(
                status=STATUS_IDLE_NO_DATA,
                message="待載入資料",
                selected_features=selected,
                batch=filters.batch,
                refdes=filters.refdes,
                part_type=filters.part_type,
                filter_context=filters,
                run_context=run_context,
            )

        filtered_df = filter_analysis_df(
            df,
            filters.batch,
            filters.refdes,
            filters.part_type,
            product=filters.product,
            time_start=filters.time_start,
            time_end=filters.time_end,
            line=filters.line,
        )
        if filtered_df.empty:
            return AnalysisPreparation(
                status=STATUS_ERROR,
                message="此過濾條件下無資料",
                selected_features=selected,
                batch=filters.batch,
                refdes=filters.refdes,
                part_type=filters.part_type,
                filter_context=filters,
                run_context=run_context,
            )

        cache_key = _analysis_cache_key(
            selected,
            filters.batch,
            filters.refdes,
            filters.part_type,
            product=filters.product,
            time_start=filters.time_start,
            time_end=filters.time_end,
            line=filters.line,
            spec_version=spec_token,
        )

        cached = store._analysis_cache.get(cache_key)
        if cached is not None:
            return AnalysisPreparation(
                status=STATUS_CACHED,
                selected_features=selected,
                batch=filters.batch,
                refdes=filters.refdes,
                part_type=filters.part_type,
                cache_key=cache_key,
                cached_payload=cached,
                filter_context=filters,
                run_context=run_context,
            )

        return AnalysisPreparation(
            status=STATUS_READY,
            selected_features=selected,
            filtered_df=filtered_df,
            usl=usl,
            lsl=lsl,
            target=target,
            batch=filters.batch,
            refdes=filters.refdes,
            part_type=filters.part_type,
            cache_key=cache_key,
            filter_context=filters,
            run_context=run_context,
        )

    @staticmethod
    def apply_payload_context(
        payload: Dict[str, Any],
        *,
        batch: str = "",
        refdes: str = "",
        part_type: str = "",
        filter_context: Optional[AnalysisFilterContext] = None,
    ) -> None:
        if filter_context is not None:
            batch = filter_context.batch
            refdes = filter_context.refdes
            part_type = filter_context.part_type
        payload["_ctx_batch"] = batch
        payload["_ctx_part_type"] = part_type
        payload["_ctx_refdes"] = refdes

    @staticmethod
    def cache_payload(
        store: SessionStore,
        payload: Dict[str, Any],
        *,
        batch: str = "",
        refdes: str = "",
        part_type: str = "",
        run_context: Optional[AnalysisRunContext] = None,
    ) -> str:
        selected_features = list(payload.get("selected_features", []))
        if run_context is not None:
            filters = run_context.filters
            batch = filters.batch
            refdes = filters.refdes
            part_type = filters.part_type
            product = filters.product
            time_start = filters.time_start
            time_end = filters.time_end
            line = filters.line
            spec_version = run_context.spec_version
        else:
            product = getattr(store, "filter_product", None)
            time_start = getattr(store, "filter_time_start", None)
            time_end = getattr(store, "filter_time_end", None)
            line = getattr(store, "filter_line", None)
            spec_version = store.spec_cache_token(getattr(store, "workorder_spec", None))
        cache_key = _analysis_cache_key(
            selected_features,
            batch,
            refdes,
            part_type,
            product=product,
            time_start=time_start,
            time_end=time_end,
            line=line,
            spec_version=spec_version,
        )
        store._analysis_cache[cache_key] = payload
        store.last_analysis_payload = payload
        return cache_key
