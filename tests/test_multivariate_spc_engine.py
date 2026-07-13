import numpy as np
import pandas as pd
from app.analytics.multivariate_spc_engine import MultivariateSPCEngine
from tests.helpers import assert_engine_contract

FACTORY = MultivariateSPCEngine()


def test_in_control():
    """100 in-control samples → most T² values below UCL (95% CI, allow ~10% OOC)."""
    np.random.seed(42)
    mean = [0, 0, 0]
    cov = [[1.0, 0.5, 0.3], [0.5, 1.0, 0.4], [0.3, 0.4, 1.0]]
    X = np.random.multivariate_normal(mean, cov, size=100)
    df = pd.DataFrame(X, columns=["A", "B", "C"])
    result = FACTORY.compute_hotelling_t2(df, ["A", "B", "C"])
    assert_engine_contract(result, expect_valid=True)
    assert result["metadata"]["error"] == ""
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
    assert_engine_contract(result, expect_valid=False)


def test_ten_samples_are_invalid_per_spc_minimum_sample_rule():
    rng = np.random.default_rng(7)
    df = pd.DataFrame(rng.normal(size=(10, 3)), columns=["A", "B", "C"])

    result = FACTORY.compute_hotelling_t2(df, ["A", "B", "C"])

    assert_engine_contract(result, expect_valid=False)
    assert result["metadata"]["n_samples"] == 10
    assert "11" in result["metadata"]["error"]


def test_eleven_numeric_string_samples_are_valid_boundary():
    rng = np.random.default_rng(17)
    df = pd.DataFrame(rng.normal(size=(11, 3)), columns=["A", "B", "C"]).astype(str)

    result = FACTORY.compute_hotelling_t2(df, ["A", "B", "C"])

    assert_engine_contract(result, expect_valid=True)
    assert result["metadata"]["n_samples"] == 11


def test_singular_covariance_returns_empty_invalid_contract():
    values = np.arange(20, dtype=float)
    df = pd.DataFrame({"A": values, "B": values * 2, "C": values * 3})

    result = FACTORY.compute_hotelling_t2(df, ["A", "B", "C"])

    assert_engine_contract(result, expect_valid=False)
    assert "奇異" in result["metadata"]["error"]


def test_exactly_three_features_are_required():
    rng = np.random.default_rng(11)
    df = pd.DataFrame(rng.normal(size=(20, 2)), columns=["A", "B"])

    result = FACTORY.compute_hotelling_t2(df, ["A", "B"])

    assert_engine_contract(result, expect_valid=False)
    assert result["metadata"]["p_features"] == 2


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
