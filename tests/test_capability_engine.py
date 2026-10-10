import numpy as np
import pandas as pd

from app.analytics.capability_engine import CapabilityEngine
from tests.helpers import assert_engine_contract


# ── helpers ───────────────────────────────────────────────────────────────────
def _valid_data(n: int = 20, mean: float = 100.0, std: float = 5.0) -> pd.Series:
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(mean, std, n))


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = CapabilityEngine.compute_capability(_valid_data(), usl=120.0, lsl=80.0)
    assert result["chart_type"] == "Capability"
    assert_engine_contract(result, expect_valid=True)


def test_valid_capability_indices_present():
    result = CapabilityEngine.compute_capability(_valid_data(), usl=120.0, lsl=80.0)
    assert_engine_contract(result, expect_valid=True)
    for key in ("mean", "sigma_st", "sigma_lt", "cp", "cpk", "pp", "ppk"):
        assert key in result["statistics"]
        assert isinstance(result["statistics"][key], float)


def test_spec_limits_preserved_in_metadata():
    result = CapabilityEngine.compute_capability(_valid_data(), usl=120.0, lsl=80.0)
    assert result["metadata"]["usl"] == 120.0
    assert result["metadata"]["lsl"] == 80.0


def test_risk_level_high_for_tight_spec():
    data = _valid_data(n=20, mean=100.0, std=10.0)
    result = CapabilityEngine.compute_capability(data, usl=105.0, lsl=95.0)
    if result["metadata"]["is_valid"]:
        assert result["metadata"]["risk_level"] == "High risk"


def test_cp_positive_for_wide_spec():
    result = CapabilityEngine.compute_capability(_valid_data(), usl=200.0, lsl=0.0)
    if result["metadata"]["is_valid"]:
        assert result["statistics"]["cp"] > 0


# ── error: insufficient samples ───────────────────────────────────────────────
def test_too_few_samples_returns_invalid():
    result = CapabilityEngine.compute_capability(
        pd.Series([100.0, 101.0, 99.0]), usl=120.0, lsl=80.0
    )
    assert_engine_contract(result, expect_valid=False)


def test_single_sample_returns_invalid():
    result = CapabilityEngine.compute_capability(pd.Series([100.0]), usl=120.0, lsl=80.0)
    assert_engine_contract(result, expect_valid=False)


# ── error: missing spec limits ────────────────────────────────────────────────
def test_none_usl_returns_invalid():
    result = CapabilityEngine.compute_capability(_valid_data(), usl=None, lsl=80.0)
    assert_engine_contract(result, expect_valid=False)


def test_none_lsl_returns_invalid():
    result = CapabilityEngine.compute_capability(_valid_data(), usl=120.0, lsl=None)
    assert_engine_contract(result, expect_valid=False)


def test_both_none_returns_invalid():
    result = CapabilityEngine.compute_capability(_valid_data(), usl=None, lsl=None)
    assert_engine_contract(result, expect_valid=False)


# ── REGRESSION BUG-2: USL == LSL must be rejected ─────────────────────────────
def test_usl_equals_lsl_returns_invalid():
    """Regression: USL==LSL previously returned Cp=0.0 silently (BUG-2)."""
    result = CapabilityEngine.compute_capability(_valid_data(), usl=100.0, lsl=100.0)
    assert result["metadata"]["is_valid"] is False, (
        "USL==LSL must be rejected — was silently returning Cp=0.0 before BUG-2 fix."
    )


def test_usl_equals_lsl_has_error_message():
    result = CapabilityEngine.compute_capability(_valid_data(), usl=50.0, lsl=50.0)
    assert result["metadata"]["is_valid"] is False
    assert len(result["metadata"]["error"]) > 5


# ── error: zero variation ─────────────────────────────────────────────────────
def test_zero_std_returns_invalid():
    result = CapabilityEngine.compute_capability(pd.Series([100.0] * 20), usl=120.0, lsl=80.0)
    assert result["metadata"]["is_valid"] is False


# ── REGRESSION: unit/scale-mismatch sentinel ──────────────────────────────────
def test_scale_mismatch_flag_present_and_false_for_normal_process():
    """A well-scaled process must not be flagged as a unit/scale mismatch."""
    result = CapabilityEngine.compute_capability(_valid_data(), usl=120.0, lsl=80.0)
    assert result["metadata"]["scale_mismatch"] is False
    assert result["metadata"]["scale_mismatch_reason"] == ""


def test_scale_mismatch_flag_set_for_mm_data_vs_percent_spec():
    """mm-scale data (mean ~0.06) against a percent spec [50,170] yields an
    impossibly large |Cpk|; the engine must flag it instead of presenting the
    index as directly-computed capability fact (root cause of the SPI report bug).
    """
    rng = np.random.default_rng(7)
    mm_data = pd.Series(rng.normal(0.06, 0.015, 200))  # Height in mm
    result = CapabilityEngine.compute_capability(mm_data, usl=170.0, lsl=50.0)
    assert result["metadata"]["is_valid"] is True  # still renders
    assert result["metadata"]["scale_mismatch"] is True
    assert abs(result["statistics"]["cpk"]) > 50
    assert "單位" in result["metadata"]["scale_mismatch_reason"]


def test_scale_mismatch_cleared_when_spec_converted_to_measurement_units():
    """Same mm data against correctly converted mm limits (percent × 0.060mm
    stencil thickness) is a real, capable process — no mismatch flag."""
    rng = np.random.default_rng(7)
    mm_data = pd.Series(rng.normal(0.06, 0.005, 200))
    result = CapabilityEngine.compute_capability(mm_data, usl=1.70 * 0.06, lsl=0.50 * 0.06)
    assert result["metadata"]["scale_mismatch"] is False
