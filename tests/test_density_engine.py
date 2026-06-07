import numpy as np
import pandas as pd

from app.analytics.density_engine import DensityEngine


def _df(n: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(23)
    return pd.DataFrame({
        "Volume": rng.normal(100.0, 10.0, n),
        "Area":   rng.normal(100.0,  8.0, n),
    })


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = DensityEngine.compute_density(_df(), col_x="Volume", col_y="Area")
    assert result["chart_type"] == "Density"
    assert "data" in result
    assert "metadata" in result


def test_valid_with_sufficient_data():
    result = DensityEngine.compute_density(_df(), col_x="Volume", col_y="Area")
    assert result["metadata"]["is_valid"] is True


def test_col_names_stored_in_data():
    result = DensityEngine.compute_density(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        assert result["data"]["col_x"] == "Volume"
        assert result["data"]["col_y"] == "Area"


def test_xy_arrays_present():
    result = DensityEngine.compute_density(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        assert "x" in result["data"]
        assert "y" in result["data"]


# ── error: insufficient data ──────────────────────────────────────────────────
def test_single_point_returns_invalid():
    df = pd.DataFrame({"Volume": [100.0], "Area": [100.0]})
    result = DensityEngine.compute_density(df, col_x="Volume", col_y="Area")
    assert result["metadata"]["is_valid"] is False


def test_missing_column_returns_invalid():
    df = pd.DataFrame({"Volume": [100.0] * 10})
    result = DensityEngine.compute_density(df, col_x="Volume", col_y="Area")
    assert result["metadata"]["is_valid"] is False


def test_empty_df_returns_invalid():
    result = DensityEngine.compute_density(
        pd.DataFrame({"Volume": [], "Area": []}), col_x="Volume", col_y="Area"
    )
    assert result["metadata"]["is_valid"] is False


# ── univariate degenerate-data guards (Bug A regression) ─────────────────────
def test_univariate_constant_returns_invalid_without_raise():
    s = pd.Series(np.full(50, 5.0))
    result = DensityEngine.compute_univariate_density(s, col="X")
    assert result["metadata"]["is_valid"] is False
    assert result["data"] == {}
    assert result["statistics"] == {}


def test_univariate_near_constant_returns_invalid_without_raise():
    rng = np.random.default_rng(0)
    s = pd.Series(np.full(50, 5.0) + rng.normal(0, 1e-15, 50))
    result = DensityEngine.compute_univariate_density(s, col="X")
    assert result["metadata"]["is_valid"] is False
    assert result["data"] == {}
    assert result["statistics"] == {}


def test_univariate_happy_path_still_works():
    rng = np.random.default_rng(0)
    s = pd.Series(rng.normal(100.0, 10.0, 50))
    result = DensityEngine.compute_univariate_density(s, col="X")
    assert result["metadata"]["is_valid"] is True
    assert "x_grid" in result["data"]
    assert "density" in result["data"]
