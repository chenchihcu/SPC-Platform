import numpy as np
import pandas as pd

from app.analytics.scatter_engine import ScatterEngine
from tests.helpers import assert_engine_contract


def _df(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(13)
    return pd.DataFrame({
        "Volume": rng.normal(100.0, 10.0, n),
        "Area":   rng.normal(100.0, 8.0, n),
    })


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = ScatterEngine.compute_scatter_spec(_df(), col_x="Volume", col_y="Area")
    assert result["chart_type"] == "ScatterSpec"
    assert_engine_contract(result, expect_valid=True)


def test_valid_with_two_columns():
    result = ScatterEngine.compute_scatter_spec(_df(), col_x="Volume", col_y="Area")
    assert result["metadata"]["is_valid"] is True


def test_metadata_stores_col_names():
    result = ScatterEngine.compute_scatter_spec(_df(), col_x="Volume", col_y="Area")
    assert result["metadata"]["col_x"] == "Volume"
    assert result["metadata"]["col_y"] == "Area"


def test_data_contains_xy_arrays():
    result = ScatterEngine.compute_scatter_spec(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        assert "x" in result["data"]
        assert "y" in result["data"]
        assert len(result["data"]["x"]) == len(result["data"]["y"])


def test_correlation_in_statistics():
    result = ScatterEngine.compute_scatter_spec(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        assert "corr" in result["statistics"]
        assert -1.0 <= result["statistics"]["corr"] <= 1.0


def test_spec_limits_passed_through():
    spec_x = {"usl": 130.0, "lsl": 70.0}
    spec_y = {"usl": 125.0, "lsl": 75.0}
    result = ScatterEngine.compute_scatter_spec(_df(), "Volume", "Area", spec_x, spec_y)
    if result["metadata"]["is_valid"]:
        assert result["data"].get("usl_x") == 130.0
        assert result["data"].get("lsl_x") == 70.0


# ── error: missing column ─────────────────────────────────────────────────────
def test_missing_column_returns_invalid():
    df = pd.DataFrame({"Volume": [100.0] * 10})
    result = ScatterEngine.compute_scatter_spec(df, col_x="Volume", col_y="Area")
    assert result["metadata"]["is_valid"] is False


def test_empty_df_returns_invalid():
    result = ScatterEngine.compute_scatter_spec(
        pd.DataFrame({"Volume": [], "Area": []}), col_x="Volume", col_y="Area"
    )
    assert result["metadata"]["is_valid"] is False
