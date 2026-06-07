import numpy as np
import pandas as pd

from app.analytics.anomaly_3f_engine import Anomaly3FEngine


def _df(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(37)
    return pd.DataFrame({
        "Volume": rng.normal(100.0, 10.0, n),
        "Area":   rng.normal(100.0,  8.0, n),
        "Height": rng.normal(100.0,  5.0, n),
    })


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = Anomaly3FEngine.compute_anomaly_3f(_df(), cols=["Volume", "Area", "Height"])
    assert result["chart_type"] == "Anomaly3F"
    assert "data" in result
    assert "statistics" in result
    assert "metadata" in result


def test_valid_with_three_features():
    result = Anomaly3FEngine.compute_anomaly_3f(_df(), cols=["Volume", "Area", "Height"])
    assert result["metadata"]["is_valid"] is True


def test_scores_length_matches_input():
    df = _df(n=50)
    result = Anomaly3FEngine.compute_anomaly_3f(df, cols=["Volume", "Area", "Height"])
    if result["metadata"]["is_valid"]:
        assert len(result["data"]["scores"]) == len(df)
        assert len(result["data"]["indices"]) == len(result["data"]["scores"])


def test_indices_follow_input_dataframe_index():
    df = _df(n=6).copy()
    df.index = [10, 12, 14, 16, 18, 20]
    result = Anomaly3FEngine.compute_anomaly_3f(df, cols=["Volume", "Area", "Height"])
    assert result["metadata"]["is_valid"] is True
    assert result["data"]["indices"] == [10, 12, 14, 16, 18, 20]


def test_scores_are_non_negative():
    result = Anomaly3FEngine.compute_anomaly_3f(_df(), cols=["Volume", "Area", "Height"])
    if result["metadata"]["is_valid"]:
        assert all(s >= 0 for s in result["data"]["scores"])


def test_statistics_keys():
    result = Anomaly3FEngine.compute_anomaly_3f(_df(), cols=["Volume", "Area", "Height"])
    if result["metadata"]["is_valid"]:
        for key in ("n", "mean_score", "max_score"):
            assert key in result["statistics"]


def test_columns_stored_in_data():
    cols = ["Volume", "Area", "Height"]
    result = Anomaly3FEngine.compute_anomaly_3f(_df(), cols=cols)
    if result["metadata"]["is_valid"]:
        assert result["data"]["columns"] == cols


# ── error ─────────────────────────────────────────────────────────────────────
def test_missing_column_returns_invalid():
    df = pd.DataFrame({"Volume": [100.0] * 20, "Area": [100.0] * 20})
    result = Anomaly3FEngine.compute_anomaly_3f(df, cols=["Volume", "Area", "Height"])
    assert result["metadata"]["is_valid"] is False


def test_empty_df_returns_invalid():
    result = Anomaly3FEngine.compute_anomaly_3f(
        pd.DataFrame({"Volume": [], "Area": [], "Height": []}),
        cols=["Volume", "Area", "Height"],
    )
    assert result["metadata"]["is_valid"] is False
