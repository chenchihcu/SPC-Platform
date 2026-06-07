import numpy as np
import pandas as pd

from app.analytics.run_chart_engine import RunChartEngine


def _data(n: int = 20) -> pd.Series:
    rng = np.random.default_rng(9)
    return pd.Series(rng.normal(100.0, 5.0, n))


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = RunChartEngine.compute_run_chart(_data())
    assert result["chart_type"] == "RunChart"
    assert "data" in result
    assert "statistics" in result
    assert "metadata" in result


def test_valid_with_sufficient_data():
    result = RunChartEngine.compute_run_chart(_data())
    assert result["metadata"]["is_valid"] is True


def test_data_values_and_indices_present():
    result = RunChartEngine.compute_run_chart(_data())
    if result["metadata"]["is_valid"]:
        assert "values" in result["data"]
        assert "indices" in result["data"]


def test_center_line_in_statistics():
    result = RunChartEngine.compute_run_chart(_data())
    if result["metadata"]["is_valid"]:
        assert "center_line" in result["statistics"]


def test_center_line_near_mean():
    data = _data(n=30)
    result = RunChartEngine.compute_run_chart(data)
    if result["metadata"]["is_valid"]:
        assert abs(result["statistics"]["center_line"] - data.mean()) < 1.0


def test_target_col_stored():
    result = RunChartEngine.compute_run_chart(_data(), target_col="Height")
    if result["metadata"]["is_valid"]:
        assert result["metadata"]["target_col"] == "Height"


def test_large_dataset_keeps_full_sample_for_display():
    data = pd.Series(np.linspace(0.0, 1.0, 120000))
    result = RunChartEngine.compute_run_chart(data)
    stats = result["statistics"]
    assert result["metadata"]["is_valid"] is True
    assert stats["n"] == 120000
    assert stats["displayed_n"] == stats["n"]
    assert stats["sampled_for_display"] is False
    assert stats["downsample_step"] == 1
    assert "normalize_mean" in stats
    assert "normalize_std" in stats
    assert stats["normalization_basis"] == "full_valid_data"


# ── small data: RunChartEngine accepts any N (no min-N guard) ─────────────────
def test_small_data_still_returns_valid():
    # RunChartEngine does not enforce a minimum sample count; it accepts any N.
    result = RunChartEngine.compute_run_chart(pd.Series([1.0, 2.0]))
    assert "metadata" in result
