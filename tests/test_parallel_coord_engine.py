import numpy as np
import pandas as pd

from app.analytics.parallel_coord_engine import ParallelCoordEngine


def _df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(43)
    return pd.DataFrame({
        "Volume": rng.normal(100.0, 10.0, n),
        "Area":   rng.normal(100.0,  8.0, n),
        "Height": rng.normal(100.0,  5.0, n),
    })


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = ParallelCoordEngine.compute_parallel_coord(
        _df(), cols=["Volume", "Area", "Height"]
    )
    assert result["chart_type"] == "ParallelCoord"
    assert "data" in result
    assert "statistics" in result
    assert "metadata" in result


def test_valid_with_three_features():
    result = ParallelCoordEngine.compute_parallel_coord(
        _df(), cols=["Volume", "Area", "Height"]
    )
    assert result["metadata"]["is_valid"] is True


def test_columns_preserved():
    cols = ["Volume", "Area", "Height"]
    result = ParallelCoordEngine.compute_parallel_coord(_df(), cols=cols)
    if result["metadata"]["is_valid"]:
        assert result["data"]["columns"] == cols


def test_values_normalised_0_to_1():
    result = ParallelCoordEngine.compute_parallel_coord(
        _df(), cols=["Volume", "Area", "Height"]
    )
    if result["metadata"]["is_valid"]:
        for row in result["data"]["values"]:
            assert all(0.0 <= v <= 1.0 for v in row)


def test_no_display_sampling_even_when_max_points_is_small():
    result = ParallelCoordEngine.compute_parallel_coord(
        _df(n=200), cols=["Volume", "Area", "Height"], max_points=50
    )
    if result["metadata"]["is_valid"]:
        assert result["statistics"]["n_displayed"] == 200
        assert result["statistics"]["sampled_for_display"] is False


def test_statistics_keys():
    result = ParallelCoordEngine.compute_parallel_coord(
        _df(), cols=["Volume", "Area", "Height"]
    )
    if result["metadata"]["is_valid"]:
        assert "n_points" in result["statistics"]
        assert "n_displayed" in result["statistics"]
        assert "n" in result["statistics"]
        assert "displayed_n" in result["statistics"]
        assert "normalization_basis" in result["statistics"]


def test_normalization_basis_uses_full_valid_data():
    df = pd.DataFrame({
        "Volume": [1.0, 2.0, 3.0, 1000.0],
        "Area": [1.0, 2.0, 3.0, 1000.0],
        "Height": [1.0, 2.0, 3.0, 1000.0],
    })
    result = ParallelCoordEngine.compute_parallel_coord(df, cols=["Volume", "Area", "Height"], max_points=2)
    assert result["metadata"]["is_valid"] is True
    stats = result["statistics"]
    assert stats["sampled_for_display"] is False
    assert stats["normalization_basis"] == "full_valid_data"


# ── error ─────────────────────────────────────────────────────────────────────
def test_empty_df_returns_invalid():
    result = ParallelCoordEngine.compute_parallel_coord(
        pd.DataFrame({"Volume": [], "Area": [], "Height": []}),
        cols=["Volume", "Area", "Height"],
    )
    assert result["metadata"]["is_valid"] is False
