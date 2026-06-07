import numpy as np
import pandas as pd

from app.analytics.spc_engine import SPCEngine
from tests.helpers import assert_engine_contract


# ── helpers ───────────────────────────────────────────────────────────────────
def _data(n: int = 20, mean: float = 100.0, std: float = 5.0) -> pd.Series:
    rng = np.random.default_rng(0)
    return pd.Series(rng.normal(mean, std, n))


# ── contract ──────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = SPCEngine.compute_imr(_data())
    assert result["chart_type"] == "I-MR"
    assert_engine_contract(result, expect_valid=True)


def test_valid_with_sufficient_samples():
    result = SPCEngine.compute_imr(_data(n=20))
    assert_engine_contract(result, expect_valid=True)


def test_control_limits_present():
    result = SPCEngine.compute_imr(_data(n=20))
    for key in ("cl", "ucl", "lcl"):
        assert key in result["statistics"]


def test_ucl_greater_than_lcl():
    result = SPCEngine.compute_imr(_data(n=20))
    if result["metadata"]["is_valid"]:
        assert result["statistics"]["ucl"] > result["statistics"]["lcl"]


def test_centerline_is_mean():
    data = _data(n=20, mean=100.0, std=3.0)
    result = SPCEngine.compute_imr(data)
    if result["metadata"]["is_valid"]:
        assert abs(result["statistics"]["cl"] - data.mean()) < 1.0


# ── error: insufficient samples ───────────────────────────────────────────────
def test_fewer_than_10_samples_returns_invalid():
    result = SPCEngine.compute_imr(pd.Series([1.0, 2.0, 3.0]))
    assert_engine_contract(result, expect_valid=False)


def test_single_sample_returns_invalid():
    result = SPCEngine.compute_imr(pd.Series([100.0]))
    assert_engine_contract(result, expect_valid=False)


def test_exactly_9_samples_returns_invalid():
    result = SPCEngine.compute_imr(pd.Series(range(9), dtype=float))
    assert result["metadata"]["is_valid"] is False


def test_exactly_10_samples_is_valid():
    result = SPCEngine.compute_imr(pd.Series(range(10, 20), dtype=float))
    assert result["metadata"]["is_valid"] is True


# ── error: zero variation ─────────────────────────────────────────────────────
def test_all_identical_values_returns_invalid():
    result = SPCEngine.compute_imr(pd.Series([100.0] * 20))
    assert_engine_contract(result, expect_valid=False)


# ── data content ─────────────────────────────────────────────────────────────
def test_data_contains_values_and_indices():
    result = SPCEngine.compute_imr(_data(n=20))
    if result["metadata"]["is_valid"]:
        assert "values" in result["data"] or len(result["data"]) > 0
