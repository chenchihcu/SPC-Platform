import numpy as np
import pandas as pd

from app.analytics.subgroup_engine import SubgroupEngine
from tests.helpers import assert_engine_contract


def _df(n_per_group: int = 15) -> pd.DataFrame:
    rng = np.random.default_rng(17)
    groups = ["U1", "U2", "U3"]
    records = []
    for g in groups:
        records.extend([
            {"PartType": g, "Volume": v}
            for v in rng.normal(100.0, 5.0, n_per_group)
        ])
    return pd.DataFrame(records)


# ── happy path ────────────────────────────────────────────────────────────────
def test_returns_required_structure():
    result = SubgroupEngine.compute_subgroup(_df(), target_col="Volume")
    assert result["chart_type"] == "Subgroup"
    assert_engine_contract(result, expect_valid=True)


def test_valid_with_multiple_groups():
    result = SubgroupEngine.compute_subgroup(_df(), target_col="Volume")
    assert_engine_contract(result, expect_valid=True)


def test_data_keys_present():
    result = SubgroupEngine.compute_subgroup(_df(), target_col="Volume")
    if result["metadata"]["is_valid"]:
        for key in ("labels", "means", "counts"):
            assert key in result["data"]


def test_group_count_matches_unique_groups():
    df = _df()
    result = SubgroupEngine.compute_subgroup(df, target_col="Volume")
    if result["metadata"]["is_valid"]:
        n_groups = len(df["PartType"].unique())
        assert len(result["data"]["labels"]) == n_groups


def test_violation_rates_with_spec():
    result = SubgroupEngine.compute_subgroup(
        _df(), target_col="Volume", usl=120.0, lsl=80.0
    )
    if result["metadata"]["is_valid"]:
        assert "violation_rates" in result["data"]
        rates = result["data"]["violation_rates"]
        assert all(0.0 <= r <= 1.0 for r in rates)


# ── error ─────────────────────────────────────────────────────────────────────
def test_empty_df_returns_invalid():
    result = SubgroupEngine.compute_subgroup(
        pd.DataFrame({"PartType": [], "Volume": []}), target_col="Volume"
    )
    assert result["metadata"]["is_valid"] is False
