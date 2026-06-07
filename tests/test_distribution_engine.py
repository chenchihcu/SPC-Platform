import pandas as pd

from app.analytics.distribution_engine import DistributionEngine


def test_distribution():
    data = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = DistributionEngine.compute_histogram(data, bins=5)
    assert result["chart_type"] == "Distribution"
    assert "data" in result
    assert "metadata" in result
    assert result["metadata"].get("is_valid") is True
