import json
import logging
import pandas as pd
from typing import Dict, Any, List, Optional

from app.utils.constants import FILTER_ALL, RANGE_ALL_BOARDS, RANGE_FIRST, RANGE_LAST
from app.utils.dataframe_utils import sorted_unique_values

# Default selected features for analysis (single-feature for backward compatibility)
DEFAULT_SELECTED_FEATURES: List[str] = ["Volume"]
_log = logging.getLogger(__name__)


def _analysis_cache_key(
    selected_features: List[str],
    batch: str,
    refdes: str,
    part_type: str,
    product: Optional[str] = None,
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
    line: Optional[str] = None,
    spec_version: Optional[str] = None,
) -> str:
    """Build a stable cache key for analysis payload (Phase 3). Includes optional filter dimensions."""
    return str((
        tuple(selected_features),
        batch,
        refdes,
        part_type,
        product or "",
        time_start or "",
        time_end or "",
        line or "",
        spec_version or "",
    ))


# Column names used for optional filters (when present in df)
_FILTER_COL_PRODUCT = ("Product", "product_id", "ProductId", "ProductName")
_FILTER_COL_TIME = ("Time", "Timestamp", "timestamp", "DateTime")
_FILTER_COL_LINE = ("Line", "line_id", "LineId", "LineName")


def filter_analysis_df(
    df: pd.DataFrame,
    batch: str,
    refdes: str,
    part_type: str,
    product: Optional[str] = None,
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
    line: Optional[str] = None,
) -> pd.DataFrame:
    """
    Filter dataframe by batch, refdes, part_type, and optional product/time/line.
    Uses FILTER_ALL to skip a dimension when "全部". Applies optional filters only when column exists.
    """
    mask = pd.Series(True, index=df.index)
    str_cache: Dict[str, pd.Series] = {}
    did_filter = False

    def _as_str(col: str) -> pd.Series:
        cached = str_cache.get(col)
        if cached is None:
            cached = df[col].astype(str)
            str_cache[col] = cached
        return cached

    def _apply_eq(col: str, value: Any) -> None:
        nonlocal mask, did_filter
        mask &= _as_str(col) == str(value)
        did_filter = True

    board_col = None
    if "BoardNo" in df.columns:
        board_col = "BoardNo"
    elif "PanelId" in df.columns:
        board_col = "PanelId"
    if board_col:
        if batch in (FILTER_ALL, RANGE_ALL_BOARDS, ""):
            pass  # no board filter — include all boards
        elif batch == RANGE_FIRST:
            boards = sorted_unique_values(df[board_col])
            if boards:
                _apply_eq(board_col, boards[0])
        elif batch == RANGE_LAST:
            boards = sorted_unique_values(df[board_col])
            if boards:
                _apply_eq(board_col, boards[-1])
        else:
            _apply_eq(board_col, batch)
    if refdes and refdes != FILTER_ALL and "RefDes" in df.columns:
        _apply_eq("RefDes", refdes)
    if part_type and part_type != FILTER_ALL and "PartType" in df.columns:
        _apply_eq("PartType", part_type)
    if product and str(product).strip():
        for col in _FILTER_COL_PRODUCT:
            if col in df.columns:
                _apply_eq(col, product)
                break
    if time_start or time_end:
        for col in _FILTER_COL_TIME:
            if col in df.columns:
                try:
                    ser = _as_str(col)
                    if time_start and str(time_start).strip():
                        mask &= ser >= str(time_start)
                        did_filter = True
                    if time_end and str(time_end).strip():
                        mask &= ser <= str(time_end)
                        did_filter = True
                except (TypeError, ValueError):
                    _log.warning(
                        "Time filter coercion failed: col=%s, start=%r, end=%r",
                        col,
                        time_start,
                        time_end,
                        exc_info=True,
                    )
                break
    if line and str(line).strip():
        for col in _FILTER_COL_LINE:
            if col in df.columns:
                _apply_eq(col, line)
                break
    if not did_filter:
        return df
    return df.loc[mask]


class SessionStore:
    """
    Global Singleton Data Store holding the loaded dataframes and mapping contexts.
    Allows UI Tabs to securely query the centralized dataset without reloading files.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionStore, cls).__new__(cls)
            cls._instance.clear()
        return cls._instance

    def clear(self) -> None:
        """Clear chart canvas and reset to empty state."""
        self.meas_df = pd.DataFrame()
        self.coord_df = pd.DataFrame()
        self.joined_df = pd.DataFrame()
        self.meas_meta: Dict[str, Any] = {}
        self.coord_meta: Dict[str, Any] = {}
        self.relation_meta: Dict[str, Any] = {}
        self.workorder_master: Dict[str, Any] = {}
        self.workorder_spec: Dict[str, Any] = {}
        self.height_spec_by_refdes: Dict[str, Dict[str, float]] = {}  # 階梯鋼板時 RefDes -> {target,lsl,usl}
        self.stencil_thickness_um: Optional[float] = None  # IPC-7525: stencil thickness for TE calc
        self.paste_type: Optional[str] = None  # J-STD-005: Type 3/4/5/6
        self.selected_features: List[str] = list(DEFAULT_SELECTED_FEATURES)
        self.last_analysis_payload: Optional[Dict[str, Any]] = None
        self.chart_ids_for_report: List[str] = []
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}  # Phase 3: key = _analysis_cache_key(...)
        # Shared filter state (optional dimensions; applied when columns exist)
        self.filter_product: Optional[str] = None
        self.filter_time_start: Optional[str] = None
        self.filter_time_end: Optional[str] = None
        self.filter_line: Optional[str] = None
        self.filter_batch: Optional[str] = None
        self.filter_refdes: Optional[str] = None
        self.filter_part_type: Optional[str] = None

    @staticmethod
    def spec_cache_token(workorder_spec: Optional[Dict[str, Any]]) -> str:
        """Stable token for cache invalidation when spec changes."""
        if not isinstance(workorder_spec, dict):
            return ""
        try:
            return json.dumps(workorder_spec, sort_keys=True, ensure_ascii=True)
        except (TypeError, ValueError):
            return str(workorder_spec)

    def get_analysis_df(self) -> Optional[pd.DataFrame]:
        """
        Return the dataframe to use for analysis: joined_df if available and non-empty, else meas_df.
        Returns None if both are unavailable.
        """
        if self.joined_df is not None and not self.joined_df.empty:
            return self.joined_df
        return self.meas_df if self.meas_df is not None else None
