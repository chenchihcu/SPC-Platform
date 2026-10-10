from typing import Any, Optional
import re
import pandas as pd

from app.utils.constants import ORDER_COL_PRIORITY


def safe_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns]


def detect_order_col(df: pd.DataFrame) -> Optional[str]:
    """Return the first column in ORDER_COL_PRIORITY that exists in df, or None.

    Used to sort measurements chronologically before SPC charting.
    Priority: Time-like columns first, then board identifiers as fallback.
    """
    return next((c for c in ORDER_COL_PRIORITY if c in df.columns), None)


_SUBGROUP_COL_PRIORITY = ("BoardNo", "PanelId")


def detect_subgroup_col(df: pd.DataFrame) -> Optional[str]:
    """Return the rational-subgroup id column (board/panel), or None.

    Short-term sigma (MR/d2) must be estimated from within-subgroup moving
    ranges only — a moving range that straddles a board boundary mixes
    between-board variation into the within-board estimate. Both the summary
    table and the diagnosis path resolve the subgroup column through this one
    helper so their capability indices stay identical.
    """
    return next((c for c in _SUBGROUP_COL_PRIORITY if c in df.columns), None)


_NAT_SPLIT_RE = re.compile(r"(\d+)")


def natural_sort_key(value: Any) -> tuple:
    """Natural sort key for mixed string/number board identifiers."""
    parts = _NAT_SPLIT_RE.split(str(value))
    return tuple(int(p) if p.isdigit() else p.lower() for p in parts)


def sorted_unique_values(series: pd.Series) -> list[Any]:
    """Return unique non-null values sorted by natural ordering."""
    values = [v for v in series.dropna().unique().tolist()]
    try:
        return sorted(values, key=natural_sort_key)
    except (TypeError, ValueError):
        return sorted(values, key=lambda v: str(v))


def sort_by_order_col(df: pd.DataFrame, order_col: Optional[str]) -> pd.DataFrame:
    """Stable natural-order sort of ``df`` by ``order_col``.

    Board identifiers such as ``Board_2`` / ``Board_10`` must sort numerically
    (``Board_2`` before ``Board_10``), not lexicographically. A plain
    ``df.sort_values("BoardNo")`` orders ``Board_10`` before ``Board_2``, which
    reshuffles the sequence feeding the order-dependent moving-range short-term
    sigma (Cp/Cpk) and yields a different result than the natural load order
    used by ``summary_engine``. Sorting on the natural key keeps every code path
    on one identical ordering so capability indices agree across the report.
    """
    if not order_col or order_col not in df.columns:
        return df
    try:
        return df.sort_values(
            order_col, key=lambda s: s.map(natural_sort_key), kind="stable"
        )
    except (TypeError, ValueError):
        return df.sort_values(order_col, kind="stable")
