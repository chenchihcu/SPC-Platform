import numpy as np
import pandas as pd

from app.analytics.pareto_engine import ParetoEngine
from tests.helpers import assert_engine_contract


def _volume_df(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    return pd.DataFrame({
        "RefDes": [f"R{i}" for i in range(n)],
        "PartType": ["U1"] * (n // 2) + ["U2"] * (n - n // 2),
        "Volume": rng.normal(100.0, 15.0, n),
        "Area": rng.normal(100.0, 10.0, n),
    })


# ── compute_pareto happy path ─────────────────────────────────────────────────
def test_returns_required_structure():
    result = ParetoEngine.compute_pareto(_volume_df(), target_col="Volume", usl=130.0, lsl=70.0)
    assert result["chart_type"] == "Pareto"
    assert_engine_contract(result, expect_valid=True)
    assert "statistics" in result
    assert "metadata" in result


def test_pareto_data_keys():
    result = ParetoEngine.compute_pareto(_volume_df(), target_col="Volume", usl=130.0, lsl=70.0)
    if result["metadata"]["is_valid"]:
        for key in ("categories", "counts", "cumulative_pct"):
            assert key in result["data"]


def test_cumulative_pct_ends_at_100():
    result = ParetoEngine.compute_pareto(_volume_df(), target_col="Volume", usl=130.0, lsl=70.0)
    if (
        result["metadata"]["is_valid"]
        and result["data"].get("cumulative_pct")
        and result.get("statistics", {}).get("total_defects", 0) > 0
    ):
        last = result["data"]["cumulative_pct"][-1]
        assert abs(last - 100.0) < 0.01


def test_counts_are_non_negative():
    result = ParetoEngine.compute_pareto(_volume_df(), target_col="Volume", usl=130.0, lsl=70.0)
    if result["metadata"]["is_valid"]:
        assert all(c >= 0 for c in result["data"]["counts"])


# ── compute_pareto with perfect data (no defects) ────────────────────────────
def test_no_defects_returns_valid_or_empty():
    df = pd.DataFrame({
        "RefDes": [f"R{i}" for i in range(20)],
        "PartType": ["U1"] * 20,
        "Volume": [100.0] * 20,  # exactly at nominal — no defects by rule
    })
    result = ParetoEngine.compute_pareto(df, target_col="Volume", usl=130.0, lsl=70.0)
    assert "metadata" in result
    # Either valid with 0 defects, or invalid — both acceptable
    if result["metadata"]["is_valid"]:
        assert result["statistics"].get("total_defects", 0) == 0


# ── error: empty dataframe ────────────────────────────────────────────────────
def test_empty_df_returns_invalid():
    result = ParetoEngine.compute_pareto(pd.DataFrame({"Volume": []}), target_col="Volume", usl=130.0, lsl=70.0)
    assert result["metadata"]["is_valid"] is False


def test_no_spec_returns_invalid():
    result = ParetoEngine.compute_pareto(_volume_df(), target_col="Volume")
    assert result["metadata"]["is_valid"] is False


# ── compute_component_pareto ──────────────────────────────────────────────────
def test_component_pareto_structure():
    result = ParetoEngine.compute_component_pareto(
        _volume_df(), target_col="Volume", usl=130.0, lsl=70.0
    )
    assert "metadata" in result
    if result["metadata"]["is_valid"]:
        assert "data" in result


def test_component_pareto_without_limits_returns_invalid():
    result = ParetoEngine.compute_component_pareto(
        _volume_df(), target_col="Volume"
    )
    assert result["metadata"]["is_valid"] is False


def _overlap_df(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"PartType": ["C1"] * len(values), "Volume": values})


def test_component_pareto_counts_point_beyond_spec_and_control_once():
    # 150 is beyond USL and UCL; 125 is beyond UCL only; 100 is normal.
    result = ParetoEngine.compute_component_pareto(
        _overlap_df([150.0, 125.0, 100.0]), target_col="Volume",
        ucl=120.0, lcl=80.0, usl=130.0, lsl=70.0,
    )
    comp = result["components"][0]
    assert comp["abnormal_count"] == 2
    assert result["data"]["counts"] == [2]
    assert result["statistics"]["total_abnormal"] == 2
    assert comp["abnormal_rate"] == 2 / 3


def test_component_pareto_counts_point_below_spec_and_control_once():
    result = ParetoEngine.compute_component_pareto(
        _overlap_df([50.0, 50.0]), target_col="Volume",
        ucl=120.0, lcl=80.0, usl=130.0, lsl=70.0,
    )
    comp = result["components"][0]
    assert comp["abnormal_count"] == 2
    assert 0.0 <= comp["abnormal_rate"] <= 1.0
