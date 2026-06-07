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
