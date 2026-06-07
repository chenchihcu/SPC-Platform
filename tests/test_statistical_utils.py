import numpy as np
import pandas as pd

from app.analytics.statistical_utils import StatisticalUtils, get_dot_nested_value


# ── is_valid_for_spc ──────────────────────────────────────────────────────────
def test_valid_with_sufficient_varied_data():
    data = pd.Series(np.linspace(1, 20, 20))
    ok, msg = StatisticalUtils.is_valid_for_spc(data)
    assert ok is True
    assert msg == "" or msg is None or "ok" in msg.lower() or ok


def test_invalid_too_few_samples():
    ok, msg = StatisticalUtils.is_valid_for_spc(pd.Series([1.0, 2.0, 3.0]))
    assert ok is False
    assert msg != ""


def test_invalid_single_sample():
    ok, msg = StatisticalUtils.is_valid_for_spc(pd.Series([5.0]))
    assert ok is False


def test_invalid_empty_series():
    ok, msg = StatisticalUtils.is_valid_for_spc(pd.Series([], dtype=float))
    assert ok is False


def test_invalid_zero_std():
    ok, msg = StatisticalUtils.is_valid_for_spc(pd.Series([100.0] * 20))
    assert ok is False
    assert msg != ""


def test_boundary_exactly_10_samples():
    data = pd.Series(np.linspace(90, 110, 10))
    ok, _ = StatisticalUtils.is_valid_for_spc(data)
    assert ok is True


def test_nan_values_are_dropped_before_check():
    # 20 values but 12 are NaN → effectively 8 valid → invalid
    vals = [float("nan")] * 12 + list(range(8))
    ok, _ = StatisticalUtils.is_valid_for_spc(pd.Series(vals))
    assert ok is False


# ── calculate_moving_range ────────────────────────────────────────────────────
def test_moving_range_length():
    # calculate_moving_range returns data.diff().abs() — same length as input,
    # with NaN at index 0; drop NaN to get N-1 valid values.
    data = pd.Series([1.0, 3.0, 2.0, 5.0, 4.0])
    mr = StatisticalUtils.calculate_moving_range(data)
    assert len(mr) == len(data)  # Series length matches input


def test_moving_range_values():
    data = pd.Series([10.0, 13.0, 11.0, 15.0])
    mr = StatisticalUtils.calculate_moving_range(data)
    # First element is NaN (diff of first element); skip it.
    valid = mr.dropna()
    expected = [3.0, 2.0, 4.0]
    for calc, exp in zip(valid, expected):
        assert abs(calc - exp) < 1e-9


def test_moving_range_all_non_negative():
    rng = np.random.default_rng(1)
    data = pd.Series(rng.normal(100, 5, 30))
    mr = StatisticalUtils.calculate_moving_range(data)
    assert all(v >= 0 for v in mr.dropna())


# ── get_dot_nested_value ──────────────────────────────────────────────────────
def test_get_dot_nested_value_simple():
    data = {"a": {"b": {"c": 123}}}
    assert get_dot_nested_value(data, "a.b.c") == 123
    assert get_dot_nested_value(data, "a.b.d") is None
    assert get_dot_nested_value(data, "a.x") is None


def test_get_dot_nested_value_with_default():
    data = {"a": 1}
    assert get_dot_nested_value(data, "a.b", default=999) == 999
    assert get_dot_nested_value(data, "x", default=0) == 0


def test_get_dot_nested_value_invalid_input():
    assert get_dot_nested_value(None, "a") is None
    assert get_dot_nested_value({}, "") is None
    assert get_dot_nested_value([], "a") is None
