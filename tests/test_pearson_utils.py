"""Degenerate Pearson inputs must not emit numpy RuntimeWarning."""

from __future__ import annotations

import warnings

import pandas as pd

from app.analytics.pearson_utils import pearson_r_safe


def test_pearson_r_safe_constant_series_returns_nan_without_warning() -> None:
    a = pd.Series([1.0, 1.0, 1.0])
    b = pd.Series([2.0, 2.0, 2.0])
    with warnings.catch_warnings():
        warnings.simplefilter("error", category=RuntimeWarning)
        r = pearson_r_safe(a, b)
    assert r != r
