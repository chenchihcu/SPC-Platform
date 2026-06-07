import numpy as np
import pandas as pd

from app.analytics.pass_fail_engine import PassFailEngine


def _df(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(31)
    return pd.DataFrame({
        "Volume": rng.normal(100.0, 15.0, n),
        "Area":   rng.normal(100.0, 10.0, n),
        "Height": rng.normal(100.0,  8.0, n),
    })


_SPEC = {
    "Volume": {"usl": 130.0, "lsl": 70.0},
    "Area":   {"usl": 125.0, "lsl": 75.0},
    "Height": {"usl": 120.0, "lsl": 80.0},
}


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = PassFailEngine.compute_pass_fail(
        _df(), cols=["Volume", "Area", "Height"], spec_by_col=_SPEC
    )
    assert result["chart_type"] == "PassFail"
    assert "data" in result
    assert "metadata" in result


def test_valid_with_three_features():
    result = PassFailEngine.compute_pass_fail(
        _df(), cols=["Volume", "Area", "Height"], spec_by_col=_SPEC
    )
    assert result["metadata"]["is_valid"] is True


def test_data_keys_present():
    result = PassFailEngine.compute_pass_fail(
        _df(), cols=["Volume", "Area", "Height"], spec_by_col=_SPEC
    )
    if result["metadata"]["is_valid"]:
        for key in ("labels", "pass_counts", "fail_counts", "pass_rates"):
            assert key in result["data"]


def test_labels_match_cols():
    cols = ["Volume", "Area", "Height"]
    result = PassFailEngine.compute_pass_fail(_df(), cols=cols, spec_by_col=_SPEC)
    if result["metadata"]["is_valid"]:
        assert result["data"]["labels"] == cols


def test_pass_rates_between_0_and_100():
    # pass_rates are percentages (0–100), not proportions (0–1).
    result = PassFailEngine.compute_pass_fail(
        _df(), cols=["Volume", "Area", "Height"], spec_by_col=_SPEC
    )
    if result["metadata"]["is_valid"]:
        assert all(0.0 <= r <= 100.0 for r in result["data"]["pass_rates"])


def test_pass_plus_fail_equals_total():
    df = _df(n=50)
    result = PassFailEngine.compute_pass_fail(df, cols=["Volume"], spec_by_col=_SPEC)
    if result["metadata"]["is_valid"]:
        p = result["data"]["pass_counts"][0]
        f = result["data"]["fail_counts"][0]
        assert p + f == len(df)


# ── error ─────────────────────────────────────────────────────────────────────
def test_empty_df_returns_invalid():
    result = PassFailEngine.compute_pass_fail(
        pd.DataFrame({"Volume": [], "Area": [], "Height": []}),
        cols=["Volume", "Area", "Height"],
        spec_by_col=_SPEC,
    )
    assert result["metadata"]["is_valid"] is False
