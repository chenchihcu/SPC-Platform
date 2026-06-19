import pandas as pd

from app.analytics.distribution_engine import DistributionEngine


def test_distribution():
    data = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = DistributionEngine.compute_histogram(data, bins=5)
    assert result["chart_type"] == "Distribution"
    assert "data" in result
    assert "metadata" in result
    assert result["metadata"].get("is_valid") is True


def test_constant_series_still_renders():
    # A histogram of constant data is well-defined (single bar); it must render
    # rather than be rejected for zero variance. The normal-curve overlay is
    # skipped internally via the existing ``std_val > 0`` guard.
    data = pd.Series([7.0] * 6)
    result = DistributionEngine.compute_histogram(data, bins=5)
    assert result["metadata"]["is_valid"] is True
    assert "counts" in result["data"]
