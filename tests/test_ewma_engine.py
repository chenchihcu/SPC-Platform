import numpy as np
import pandas as pd

from app.analytics.ewma_engine import EWMAEngine
from tests.helpers import assert_engine_contract


def _data(n: int = 20) -> pd.Series:
    rng = np.random.default_rng(3)
    return pd.Series(rng.normal(100.0, 5.0, n))


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = EWMAEngine.compute_ewma(_data())
    assert result["chart_type"] == "EWMA"
    assert_engine_contract(result, expect_valid=True)


def test_valid_with_sufficient_data():
    result = EWMAEngine.compute_ewma(_data())
    assert result["metadata"]["is_valid"] is True


def test_control_limits_present():
    result = EWMAEngine.compute_ewma(_data())
    if result["metadata"]["is_valid"]:
        for key in ("cl", "ucl", "lcl"):
            assert key in result["statistics"]


def test_ucl_above_lcl():
    result = EWMAEngine.compute_ewma(_data())
    if result["metadata"]["is_valid"]:
        assert result["statistics"]["ucl"] > result["statistics"]["lcl"]


def test_ewma_values_length_matches_input():
    data = _data(n=25)
    result = EWMAEngine.compute_ewma(data)
    if result["metadata"]["is_valid"]:
        assert len(result["data"]["values"]) == len(data)


def test_target_col_stored_in_metadata():
    result = EWMAEngine.compute_ewma(_data(), target_col="Volume")
    if result["metadata"]["is_valid"]:
        assert result["metadata"]["target_col"] == "Volume"


def test_custom_lambda_accepted():
    result = EWMAEngine.compute_ewma(_data(), lam=0.3)
    if result["metadata"]["is_valid"]:
        assert abs(result["statistics"]["lambda"] - 0.3) < 1e-9


# ── error: insufficient samples ───────────────────────────────────────────────
def test_too_few_samples_returns_invalid():
    result = EWMAEngine.compute_ewma(pd.Series([1.0, 2.0, 3.0]))
    assert result["metadata"]["is_valid"] is False
    assert result["metadata"]["error"] != ""


def test_all_identical_values_returns_invalid():
    result = EWMAEngine.compute_ewma(pd.Series([100.0] * 20))
    assert result["metadata"]["is_valid"] is False
