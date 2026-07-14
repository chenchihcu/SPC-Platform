"""Tests for MoranIEngine — Global and Local Moran's I spatial autocorrelation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analytics.moran_i_engine import MoranIEngine
from tests.helpers import assert_engine_contract


def _coords(n: int = 30, seed: int = 42) -> np.ndarray:
    """Generate random 2D coordinates for testing."""
    rng = np.random.default_rng(seed)
    return rng.uniform(0, 100, (n, 2))


def _values(n: int = 30, seed: int = 99) -> pd.Series:
    """Generate random measurement values."""
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(100.0, 5.0, n))


def _spatial_pattern(n: int = 30, seed: int = 7) -> tuple[np.ndarray, pd.Series]:
    """Generate coordinates and values with a spatial gradient."""
    rng = np.random.default_rng(seed)
    coords = rng.uniform(0, 100, (n, 2))
    # Value increases with X (spatial structure → positive autocorrelation)
    vals = pd.Series(coords[:, 0] + rng.normal(0, 5, n))
    return coords, vals


# ── Global Moran's I: happy path ──────────────────────────────────────────


def test_global_returns_required_structure():
    result = MoranIEngine.compute_global_moran_i(_coords(), _values())
    assert result["chart_type"] == "MoranI"
    assert_engine_contract(result, expect_valid=True)


def test_global_valid_with_sufficient_data():
    result = MoranIEngine.compute_global_moran_i(_coords(), _values())
    assert result["metadata"]["is_valid"] is True


def test_global_statistics_keys_present():
    result = MoranIEngine.compute_global_moran_i(_coords(), _values())
    for key in ("global_moran_i", "expected_i", "p_value", "z_score", "n", "k"):
        assert key in result["statistics"], f"Missing key: {key}"


def test_global_moran_i_finite():
    result = MoranIEngine.compute_global_moran_i(_coords(), _values())
    if result["metadata"]["is_valid"]:
        assert np.isfinite(result["statistics"]["global_moran_i"])
        assert np.isfinite(result["statistics"]["z_score"])


def test_global_with_spatial_pattern():
    """Spatially structured data should produce positive I (approximately)."""
    coords, vals = _spatial_pattern(50, seed=7)
    result = MoranIEngine.compute_global_moran_i(coords, vals)
    if result["metadata"]["is_valid"]:
        # With X-driven gradient, Moran's I should be positive
        assert result["statistics"]["global_moran_i"] > 0


def test_global_target_col_stored_in_metadata():
    result = MoranIEngine.compute_global_moran_i(_coords(), _values())
    if result["metadata"]["is_valid"]:
        assert "method" in result["metadata"]


def test_global_dataframe_input():
    """Should accept DataFrame coords with X/Y columns."""
    coords_df = pd.DataFrame(_coords(), columns=["X", "Y"])
    result = MoranIEngine.compute_global_moran_i(coords_df, _values())
    assert_engine_contract(result, expect_valid=True)


# ── Global Moran's I: error cases ─────────────────────────────────────────


def test_global_too_few_points_returns_invalid():
    coords = np.array([[0.0, 0.0], [1.0, 1.0]])
    vals = pd.Series([1.0, 2.0])
    result = MoranIEngine.compute_global_moran_i(coords, vals, k=3)
    assert result["metadata"]["is_valid"] is False


def test_global_constant_values_returns_invalid():
    vals = pd.Series([5.0] * 30)
    result = MoranIEngine.compute_global_moran_i(_coords(), vals)
    assert result["metadata"]["is_valid"] is False


def test_global_missing_xy_columns_returns_invalid():
    bad_df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    result = MoranIEngine.compute_global_moran_i(bad_df, _values(3))
    assert result["metadata"]["is_valid"] is False


def test_global_dimension_mismatch_returns_invalid():
    coords = np.ones((10, 2))
    vals = pd.Series(np.ones(5))
    result = MoranIEngine.compute_global_moran_i(coords, vals)
    assert result["metadata"]["is_valid"] is False


def test_global_empty_series_returns_invalid():
    result = MoranIEngine.compute_global_moran_i(_coords(5), pd.Series([], dtype=float))
    assert result["metadata"]["is_valid"] is False


# ── Local Moran's I (LISA): happy path ─────────────────────────────────────


def test_local_returns_required_structure():
    result = MoranIEngine.compute_local_moran_i(_coords(), _values())
    assert result["chart_type"] == "MoranI_LISA"
    assert_engine_contract(result, expect_valid=True)


def test_local_valid_with_sufficient_data():
    result = MoranIEngine.compute_local_moran_i(_coords(), _values())
    assert result["metadata"]["is_valid"] is True


def test_local_data_keys_present():
    result = MoranIEngine.compute_local_moran_i(_coords(), _values())
    if result["metadata"]["is_valid"]:
        for key in ("x", "y", "local_i", "p_values", "classifications", "quadrant_std_value", "quadrant_lag"):
            assert key in result["data"], f"Missing key: {key}"
        assert result["data"]["x"] == pytest.approx(_coords()[:, 0])
        assert result["data"]["y"] == pytest.approx(_coords()[:, 1])


def test_local_classifications_length():
    result = MoranIEngine.compute_local_moran_i(_coords(), _values())
    if result["metadata"]["is_valid"]:
        n = len(result["data"]["classifications"])
        assert n == len(result["data"]["local_i"])
        valid_labels = {"HH", "LL", "HL", "LH", "NS"}
        for label in result["data"]["classifications"]:
            assert label in valid_labels, f"Unexpected label: {label}"


def test_local_statistics_keys_present():
    result = MoranIEngine.compute_local_moran_i(_coords(), _values())
    for key in ("n", "k", "n_significant", "class_counts"):
        assert key in result["statistics"], f"Missing key: {key}"


# ── Local Moran's I: error cases ──────────────────────────────────────────


def test_local_too_few_points_returns_invalid():
    coords = np.array([[0.0, 0.0], [1.0, 1.0]])
    vals = pd.Series([1.0, 2.0])
    result = MoranIEngine.compute_local_moran_i(coords, vals, k=3)
    assert result["metadata"]["is_valid"] is False


def test_local_constant_values_returns_invalid():
    vals = pd.Series([5.0] * 30)
    result = MoranIEngine.compute_local_moran_i(_coords(), vals)
    assert result["metadata"]["is_valid"] is False


def test_local_missing_xy_columns_returns_invalid():
    bad_df = pd.DataFrame({"A": [1, 2, 3]})
    result = MoranIEngine.compute_local_moran_i(bad_df, _values(3))
    assert result["metadata"]["is_valid"] is False
