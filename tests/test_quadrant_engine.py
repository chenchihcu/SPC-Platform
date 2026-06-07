import numpy as np
import pandas as pd

from app.analytics.quadrant_engine import QuadrantEngine


def _df(n: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(29)
    return pd.DataFrame({
        "Volume": rng.normal(100.0, 10.0, n),
        "Area":   rng.normal(100.0,  8.0, n),
    })


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = QuadrantEngine.compute_quadrant(_df(), col_x="Volume", col_y="Area")
    assert result["chart_type"] == "Quadrant"
    assert "data" in result
    assert "metadata" in result


def test_valid_with_data():
    result = QuadrantEngine.compute_quadrant(_df(), col_x="Volume", col_y="Area")
    assert result["metadata"]["is_valid"] is True


def test_quadrant_labels_present():
    result = QuadrantEngine.compute_quadrant(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        assert "quadrant" in result["data"]
        assert len(result["data"]["quadrant"]) == len(_df())


def test_all_quadrants_are_1_to_4():
    result = QuadrantEngine.compute_quadrant(_df(), col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        assert all(q in (1, 2, 3, 4) for q in result["data"]["quadrant"])


def test_quadrant_counts_sum_to_n():
    df = _df(n=40)
    result = QuadrantEngine.compute_quadrant(df, col_x="Volume", col_y="Area")
    if result["metadata"]["is_valid"]:
        total = sum(
            result["data"].get(f"count_q{i}", 0) for i in range(1, 5)
        )
        assert total == len(df)


def test_spec_center_used_as_split():
    spec_x = {"usl": 120.0, "lsl": 80.0}   # center = 100
    spec_y = {"usl": 115.0, "lsl": 85.0}   # center = 100
    result = QuadrantEngine.compute_quadrant(_df(), "Volume", "Area", spec_x, spec_y)
    if result["metadata"]["is_valid"]:
        assert abs(result["data"]["center_x"] - 100.0) < 0.01
        assert abs(result["data"]["center_y"] - 100.0) < 0.01


# ── error ─────────────────────────────────────────────────────────────────────
def test_empty_df_returns_invalid():
    result = QuadrantEngine.compute_quadrant(
        pd.DataFrame({"Volume": [], "Area": []}), col_x="Volume", col_y="Area"
    )
    assert result["metadata"]["is_valid"] is False
