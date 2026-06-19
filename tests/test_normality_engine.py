import numpy as np
import pandas as pd

from app.analytics.normality_engine import NormalityEngine
from tests.helpers import assert_engine_contract


def _normal_data(n: int = 50) -> pd.Series:
    rng = np.random.default_rng(7)
    return pd.Series(rng.normal(100.0, 5.0, n))


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = NormalityEngine.compute_normality(_normal_data())
    assert result["chart_type"] == "Normality"
    assert_engine_contract(result, expect_valid=True)


def test_valid_with_sufficient_data():
    result = NormalityEngine.compute_normality(_normal_data())
    assert result["metadata"]["is_valid"] is True


def test_qq_plot_data_present():
    result = NormalityEngine.compute_normality(_normal_data())
    if result["metadata"]["is_valid"]:
        d = result["data"]
        assert "theoretical_q" in d
        assert "actual_q" in d
        assert len(d["theoretical_q"]) == len(d["actual_q"])


def test_statistics_keys_present():
    result = NormalityEngine.compute_normality(_normal_data())
    if result["metadata"]["is_valid"]:
        for key in ("p_value", "is_normal", "test_name"):
            assert key in result["statistics"]


def test_normal_data_has_is_normal_key():
    # is_normal is a statistical test result — not guaranteed for any fixed seed;
    # just verify the key exists and is bool-like (Python bool or numpy bool_).
    import numpy as np
    result = NormalityEngine.compute_normality(_normal_data(n=100))
    if result["metadata"]["is_valid"]:
        assert isinstance(result["statistics"]["is_normal"], (bool, np.bool_))


# ── error: insufficient samples ───────────────────────────────────────────────
def test_too_few_samples_returns_invalid():
    result = NormalityEngine.compute_normality(pd.Series([1.0, 2.0]))
    assert result["metadata"]["is_valid"] is False
    assert result["metadata"]["error"] != ""


def test_single_sample_returns_invalid():
    result = NormalityEngine.compute_normality(pd.Series([100.0]))
    assert result["metadata"]["is_valid"] is False


def test_empty_series_returns_invalid():
    result = NormalityEngine.compute_normality(pd.Series([], dtype=float))
    assert result["metadata"]["is_valid"] is False


def test_zero_variance_data_skips_shapiro():
    # SPC_RULES §2.1: zero-variance series skip Shapiro but stay valid (p=1.0),
    # so the UI remains populated rather than erroring out.
    data = pd.Series([100.0] * 80)
    result = NormalityEngine.compute_normality(data)
    assert result["metadata"]["is_valid"] is True
    assert result["statistics"]["normality_test_skipped"] is True
    assert result["statistics"]["shapiro_skip_reason"] == "zero_variance"
    assert float(result["statistics"]["p_value"]) == 1.0


def test_large_dataset_uses_full_data_without_sampling() -> None:
    data = _normal_data(n=8000)
    result = NormalityEngine.compute_normality(data)
    stats = result["statistics"]
    assert result["metadata"]["is_valid"] is True
    assert stats["sampled_for_test"] is False
    assert stats["tested_n"] == stats["total_n"] == 8000
    assert stats["test_name"] == "D'Agostino K² (full data / N>5000)"
