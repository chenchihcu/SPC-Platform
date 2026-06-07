import numpy as np
import pandas as pd

from app.analytics.consistency_3f_engine import Consistency3FEngine


def _df(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(41)
    return pd.DataFrame({
        "Volume": rng.normal(100.0, 10.0, n),
        "Area":   rng.normal(100.0,  8.0, n),
        "Height": rng.normal(100.0,  5.0, n),
    })


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = Consistency3FEngine.compute_consistency_3f(_df())
    assert result["chart_type"] == "Consistency3F"
    assert "data" in result
    assert "statistics" in result
    assert "metadata" in result


def test_valid_with_all_three_columns():
    result = Consistency3FEngine.compute_consistency_3f(_df())
    assert result["metadata"]["is_valid"] is True


def test_data_keys_present():
    result = Consistency3FEngine.compute_consistency_3f(_df())
    if result["metadata"]["is_valid"]:
        for key in ("indices", "ratio_va", "height", "ratio_va_z", "height_z", "diff_va_h"):
            assert key in result["data"]


def test_statistics_keys():
    result = Consistency3FEngine.compute_consistency_3f(_df())
    if result["metadata"]["is_valid"]:
        for key in ("n", "mean_diff", "std_diff", "ratio_std", "height_std"):
            assert key in result["statistics"]


def test_lengths_consistent():
    df = _df(n=50)
    result = Consistency3FEngine.compute_consistency_3f(df)
    if result["metadata"]["is_valid"]:
        n = len(result["data"]["indices"])
        assert len(result["data"]["ratio_va"]) == n
        assert len(result["data"]["height"]) == n
        assert len(result["data"]["ratio_va_z"]) == n
        assert len(result["data"]["height_z"]) == n


def test_indices_follow_input_dataframe_index():
    df = _df(n=6).copy()
    df.index = [101, 103, 105, 107, 109, 111]
    result = Consistency3FEngine.compute_consistency_3f(df)
    assert result["metadata"]["is_valid"] is True
    assert result["data"]["indices"] == [101, 103, 105, 107, 109, 111]


def test_standardized_diff_is_zero_when_ratio_equals_height():
    vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    df = pd.DataFrame({
        "Volume": vals,
        "Area": np.ones_like(vals),
        "Height": vals,
    })
    result = Consistency3FEngine.compute_consistency_3f(df)
    assert result["metadata"]["is_valid"] is True
    diff = np.array(result["data"]["diff_va_h"], dtype=float)
    assert np.allclose(diff, 0.0, atol=1e-9)


# ── error ─────────────────────────────────────────────────────────────────────
def test_missing_volume_column_returns_invalid():
    df = pd.DataFrame({"Area": [100.0] * 20, "Height": [100.0] * 20})
    result = Consistency3FEngine.compute_consistency_3f(df)
    assert result["metadata"]["is_valid"] is False


def test_empty_df_returns_invalid():
    result = Consistency3FEngine.compute_consistency_3f(
        pd.DataFrame({"Volume": [], "Area": [], "Height": []})
    )
    assert result["metadata"]["is_valid"] is False
