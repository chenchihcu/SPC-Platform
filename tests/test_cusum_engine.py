import numpy as np
import pandas as pd

from app.analytics.cusum_engine import CUSUMEngine
from tests.helpers import assert_engine_contract


def _data(n: int = 20) -> pd.Series:
    rng = np.random.default_rng(5)
    return pd.Series(rng.normal(100.0, 5.0, n))


def _specs() -> dict[str, float]:
    return {"usl": 120.0, "lsl": 80.0}


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = CUSUMEngine.compute_cusum(_data(), **_specs())
    assert result["chart_type"] == "CUSUM"
    assert_engine_contract(result, expect_valid=True)


def test_valid_with_sufficient_data():
    result = CUSUMEngine.compute_cusum(_data(), **_specs())
    assert result["metadata"]["is_valid"] is True


def test_cusum_plus_and_minus_present():
    result = CUSUMEngine.compute_cusum(_data(), **_specs())
    if result["metadata"]["is_valid"]:
        assert "values" in result["data"]      # C+
        assert "values_cm" in result["data"]   # C-


def test_statistics_present():
    result = CUSUMEngine.compute_cusum(_data(), **_specs())
    if result["metadata"]["is_valid"]:
        for key in ("mu0", "sigma", "k", "h", "n"):
            assert key in result["statistics"]


def test_cusum_plus_non_negative():
    result = CUSUMEngine.compute_cusum(_data(), **_specs())
    if result["metadata"]["is_valid"]:
        assert all(v >= 0 for v in result["data"]["values"])


def test_target_col_in_metadata():
    result = CUSUMEngine.compute_cusum(_data(), target_col="Area", **_specs())
    if result["metadata"]["is_valid"]:
        assert result["metadata"]["target_col"] == "Area"


# ── error: insufficient samples ───────────────────────────────────────────────
def test_too_few_samples_returns_invalid():
    result = CUSUMEngine.compute_cusum(pd.Series([1.0, 2.0]), **_specs())
    assert result["metadata"]["is_valid"] is False
    assert result["metadata"]["error"] != ""


def test_all_identical_values_returns_invalid():
    result = CUSUMEngine.compute_cusum(pd.Series([50.0] * 20), **_specs())
    assert result["metadata"]["is_valid"] is False


def test_target_fallback_metadata_exposed_when_target_far_from_data():
    data = _data(n=30)
    result = CUSUMEngine.compute_cusum(data, target=10000.0, **_specs())
    assert result["metadata"]["is_valid"] is True
    stats = result["statistics"]
    assert stats["mu0_fallback_applied"] is True
    assert stats["mu0_fallback_reason"] == "target_or_spec_midpoint_far_from_data_mean"
    assert stats["mu0_fallback_deviation_sigma"] is not None
    assert stats["mu0_source"] == "data_mean"


def test_missing_spec_returns_invalid():
    result = CUSUMEngine.compute_cusum(_data())
    assert result["metadata"]["is_valid"] is False
    assert result["metadata"]["error"] == "Missing USL or LSL."


def test_equal_spec_returns_invalid():
    result = CUSUMEngine.compute_cusum(_data(), usl=100.0, lsl=100.0)
    assert result["metadata"]["is_valid"] is False
    assert result["metadata"]["error"] == "USL 與 LSL 相同。"
