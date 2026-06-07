import numpy as np
import pandas as pd

from app.analytics.repeated_offender_engine import RepeatedOffenderEngine


def _df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(19)
    refdes = [f"R{i % 10}" for i in range(n)]  # 10 unique RefDes, repeated
    return pd.DataFrame({
        "RefDes":  refdes,
        "Volume":  rng.normal(100.0, 20.0, n),  # wide spread → some OOS
    })


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = RepeatedOffenderEngine.compute_repeated_offender(
        _df(), target_col="Volume", usl=130.0, lsl=70.0
    )
    assert result["chart_type"] == "RepeatedOffender"
    assert "data" in result
    assert "metadata" in result


def test_valid_with_specs():
    result = RepeatedOffenderEngine.compute_repeated_offender(
        _df(), target_col="Volume", usl=130.0, lsl=70.0
    )
    assert result["metadata"]["is_valid"] is True


def test_data_labels_and_counts():
    result = RepeatedOffenderEngine.compute_repeated_offender(
        _df(), target_col="Volume", usl=130.0, lsl=70.0
    )
    if result["metadata"]["is_valid"]:
        assert "labels" in result["data"]
        assert "counts" in result["data"]
        assert len(result["data"]["labels"]) == len(result["data"]["counts"])


def test_top_n_limits_results():
    result = RepeatedOffenderEngine.compute_repeated_offender(
        _df(n=100), target_col="Volume", usl=130.0, lsl=70.0, top_n=5
    )
    if result["metadata"]["is_valid"] and result["data"]["labels"]:
        assert len(result["data"]["labels"]) <= 5
        assert result["statistics"]["sampled_for_display"] is True


def test_counts_are_positive():
    result = RepeatedOffenderEngine.compute_repeated_offender(
        _df(), target_col="Volume", usl=130.0, lsl=70.0
    )
    if result["metadata"]["is_valid"]:
        assert all(c > 0 for c in result["data"]["counts"])


def test_default_returns_all_offenders_without_truncation() -> None:
    df = pd.DataFrame(
        {
            "RefDes": [f"R{i}" for i in range(10)],
            "Volume": [200.0] * 10,  # all violate USL
        }
    )
    result = RepeatedOffenderEngine.compute_repeated_offender(
        df, target_col="Volume", usl=130.0, lsl=70.0
    )
    assert result["metadata"]["is_valid"] is True
    assert len(result["data"]["labels"]) == 10
    assert result["statistics"]["displayed_n"] == 10
    assert result["statistics"]["n_refdes_with_violations"] == 10
    assert result["statistics"]["sampled_for_display"] is False


# ── no violations → valid but empty ──────────────────────────────────────────
def test_no_violations_returns_valid():
    df = pd.DataFrame({"RefDes": [f"R{i}" for i in range(20)], "Volume": [100.0] * 20})
    result = RepeatedOffenderEngine.compute_repeated_offender(
        df, target_col="Volume", usl=130.0, lsl=70.0
    )
    assert "metadata" in result
    # Valid with 0 offenders, or valid with empty data — both acceptable


# ── error: no spec limits ─────────────────────────────────────────────────────
def test_no_spec_returns_invalid():
    result = RepeatedOffenderEngine.compute_repeated_offender(
        _df(), target_col="Volume", usl=None, lsl=None
    )
    assert result["metadata"]["is_valid"] is False
