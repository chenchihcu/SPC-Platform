import numpy as np
import pandas as pd
from app.analytics.multivariate_spc_engine import MultivariateSPCEngine

FACTORY = MultivariateSPCEngine()


def test_in_control():
    """100 in-control samples → most T² values below UCL (95% CI, allow ~10% OOC)."""
    np.random.seed(42)
    mean = [0, 0, 0]
    cov = [[1.0, 0.5, 0.3], [0.5, 1.0, 0.4], [0.3, 0.4, 1.0]]
    X = np.random.multivariate_normal(mean, cov, size=100)
    df = pd.DataFrame(X, columns=["A", "B", "C"])
    result = FACTORY.compute_hotelling_t2(df, ["A", "B", "C"])
    assert result["metadata"]["is_valid"] is True
    assert result["statistics"]["ucl_value"] > 0
    assert result["statistics"]["ooc_pct"] < 10, (
        f"OOC rate {result['statistics']['ooc_pct']:.1f}% exceeds expected 5%"
    )


def test_out_of_control():
    np.random.seed(42)
    mean = [0, 0, 0]
    cov = [[1.0, 0.5, 0.3], [0.5, 1.0, 0.4], [0.3, 0.4, 1.0]]
    X = np.random.multivariate_normal(mean, cov, size=100)
    X[-10:, 0] += 3.0
    df = pd.DataFrame(X, columns=["A", "B", "C"])
    result = FACTORY.compute_hotelling_t2(df, ["A", "B", "C"])
    assert result["metadata"]["is_valid"] is True
    last_10 = result["data"]["ooc_flags"][-10:]
    assert any(last_10), "No OOC detected in shifted samples"


def test_insufficient_data():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
    result = FACTORY.compute_hotelling_t2(df, ["A", "B", "C"])
    assert result["metadata"]["is_valid"] is False


def test_payload_structure():
    np.random.seed(42)
    X = np.random.randn(50, 3)
    df = pd.DataFrame(X, columns=["A", "B", "C"])
    result = FACTORY.compute_hotelling_t2(df, ["A", "B", "C"])
    assert result["payload_key"] == "hotelling_t2"
    for key in ("chart_type", "payload_key", "data", "statistics", "metadata"):
        assert key in result
    for key in ("indices", "t2_values", "ooc_flags"):
        assert key in result["data"]
    for key in ("ucl_value", "mean_t2", "max_t2", "ooc_count", "ooc_pct"):
        assert key in result["statistics"]
    for key in ("is_valid", "n_samples", "p_features", "cov_matrix", "mu0_vector", "error"):
        assert key in result["metadata"]
