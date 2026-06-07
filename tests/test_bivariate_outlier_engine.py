import numpy as np
import pandas as pd

from app.analytics.bivariate_outlier_engine import BivariateOutlierEngine


def _df(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(47)
    return pd.DataFrame({
        "Volume": rng.normal(100.0, 10.0, n),
        "Area":   rng.normal(100.0,  8.0, n),
    })


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = BivariateOutlierEngine.compute_bivariate_outlier(_df(), col_x="Volume", col_y="Area")
    assert result["chart_type"] == "BivariateOutlier"
    assert "data" in result
    assert "statistics" in result
    assert "metadata" in result


def test_valid_with_sufficient_data():
    result = BivariateOutlierEngine.compute_bivariate_outlier(_df(), col_x="Volume", col_y="Area")
    assert result["metadata"]["is_valid"] is True


def test_data_keys_present():
    result = BivariateOutlierEngine.compute_bivariate_outlier(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        for key in ("x", "y", "is_outlier", "distance2"):
            assert key in result["data"]


def test_is_outlier_is_boolean_list():
    result = BivariateOutlierEngine.compute_bivariate_outlier(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        flags = result["data"]["is_outlier"]
        assert all(isinstance(f, (bool, int)) for f in flags)


def test_lengths_consistent():
    df = _df(n=50)
    result = BivariateOutlierEngine.compute_bivariate_outlier(df, col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        assert len(result["data"]["x"]) == len(result["data"]["y"])
        assert len(result["data"]["x"]) == len(result["data"]["is_outlier"])


def test_statistics_keys():
    result = BivariateOutlierEngine.compute_bivariate_outlier(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        for key in ("n", "n_outliers", "threshold_d2", "alpha"):
            assert key in result["statistics"]


def test_n_outliers_non_negative():
    result = BivariateOutlierEngine.compute_bivariate_outlier(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        assert result["statistics"]["n_outliers"] >= 0
        assert result["statistics"]["threshold_d2"] > 0
        assert result["metadata"]["method"] == "mahalanobis_chi2"


def test_injected_outlier_is_detected():
    df = _df(n=50).copy()
    df.loc[0, "Volume"] = 999.0   # extreme outlier
    df.loc[0, "Area"]   = 999.0
    result = BivariateOutlierEngine.compute_bivariate_outlier(df, col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        assert result["statistics"]["n_outliers"] >= 1


# ── error ─────────────────────────────────────────────────────────────────────
def test_missing_column_returns_invalid():
    df = pd.DataFrame({"Volume": [100.0] * 10})
    result = BivariateOutlierEngine.compute_bivariate_outlier(df, col_x="Volume", col_y="Area")
    assert result["metadata"]["is_valid"] is False


def test_empty_df_returns_invalid():
    result = BivariateOutlierEngine.compute_bivariate_outlier(
        pd.DataFrame({"Volume": [], "Area": []}), col_x="Volume", col_y="Area"
    )
    assert result["metadata"]["is_valid"] is False
