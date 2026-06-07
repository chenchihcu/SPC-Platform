"""Pearson correlation helpers that avoid numpy divide warnings on degenerate inputs."""

from __future__ import annotations

import pandas as pd


def pearson_r_safe(a: pd.Series, b: pd.Series) -> float:
    """
    Pearson r between two aligned series.
    Returns float('nan') when undefined (n < 2 or either series is constant).
    """
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    if int(a.nunique(dropna=True)) <= 1 or int(b.nunique(dropna=True)) <= 1:
        return float("nan")
    return float(a.corr(b))
