"""SPC_RULES §4 (2026-10-10): I-MR sigma == Cp/Cpk sigma_within.

Boundary MRs (subgroup id change) stay in the plotted MR series but are
excluded from MR̄; no subgroup ids keeps the legacy whole-series estimate.
"""

import numpy as np
import pandas as pd
import pytest

from app.analytics.capability_engine import CapabilityEngine
from app.analytics.spc_engine import SPCEngine
from app.viewmodels.chart_analysis_viewmodel import (
    _compute_driver_bundle,
    _compute_single_feature_analysis,
)
from tests.helpers import assert_engine_contract


def _boards(n_boards: int = 4, per_board: int = 6, offset: float = 50.0) -> pd.DataFrame:
    """Small within-board noise, large board-to-board offset."""
    rng = np.random.default_rng(7)
    rows = []
    for b in range(n_boards):
        for _ in range(per_board):
            rows.append({"BoardNo": f"Board_{b + 1}", "Volume": 100.0 + b * offset + rng.normal(0, 1.0)})
    return pd.DataFrame(rows)


def test_no_subgroup_ids_is_legacy_whole_series():
    df = _boards()
    legacy_mr = np.abs(np.diff(df["Volume"].to_numpy())).mean()
    result = SPCEngine.compute_imr(df["Volume"], "Volume")
    assert_engine_contract(result, expect_valid=True)
    assert result["statistics"]["mr_bar"] == legacy_mr
    assert result["statistics"]["sigma"] == legacy_mr / SPCEngine.I_MR_D2
    assert result["statistics"]["mr_boundary_excluded"] == 0
    assert result["metadata"]["sigma_basis"] == "whole_series"


def test_boundary_mrs_excluded_from_mr_bar_but_still_plotted():
    df = _boards(n_boards=4, per_board=6)
    values = df["Volume"].to_numpy()
    result = SPCEngine.compute_imr(df["Volume"], "Volume", subgroup_ids=df["BoardNo"])
    assert_engine_contract(result, expect_valid=True)

    # Hand-computed: MRs whose two points share a board.
    ids = df["BoardNo"].to_numpy()
    mr = np.abs(np.diff(values))
    within = mr[ids[1:] == ids[:-1]]
    stats = result["statistics"]
    assert stats["mr_bar"] == pytest.approx(within.mean(), rel=1e-12)
    assert stats["sigma"] == pytest.approx(within.mean() / 1.128, rel=1e-12)
    assert stats["ucl"] == pytest.approx(stats["cl"] + 3 * stats["sigma"], rel=1e-12)
    assert stats["mr_boundary_excluded"] == 3  # 4 boards → 3 boundaries
    assert result["metadata"]["sigma_basis"] == "within_subgroup"
    # Payload shape unchanged: every consecutive MR is still returned.
    assert len(result["data"]["mr_values"]) == len(values) - 1
    # Board jumps (~50) no longer inflate sigma (within-board noise ~1).
    assert stats["sigma"] < 3.0


def test_imr_sigma_equals_capability_sigma_st():
    df = _boards()
    imr = SPCEngine.compute_imr(df["Volume"], "Volume", subgroup_ids=df["BoardNo"])
    cap = CapabilityEngine.compute_capability(df["Volume"], 400.0, 0.0, subgroup_ids=df["BoardNo"])
    assert imr["statistics"]["sigma"] == pytest.approx(cap["statistics"]["sigma_st"], rel=1e-12)


def test_duplicate_index_falls_back_to_whole_series():
    df = _boards()
    df.index = [0] * len(df)
    result = SPCEngine.compute_imr(df["Volume"], "Volume", subgroup_ids=df["BoardNo"])
    assert result["metadata"]["sigma_basis"] == "whole_series"
    assert result["statistics"]["mr_boundary_excluded"] == 0
    assert result["statistics"]["mr_bar"] == pytest.approx(
        np.abs(np.diff(df["Volume"].to_numpy())).mean(), rel=1e-12
    )


def test_viewmodel_single_feature_imr_matches_cpk_sigma():
    df = _boards()
    bundle = _compute_single_feature_analysis(df, "Volume", usl=400.0, lsl=0.0)
    assert bundle["spc"]["metadata"]["sigma_basis"] == "within_subgroup"
    assert bundle["spc"]["statistics"]["sigma"] == pytest.approx(
        bundle["cap"]["statistics"]["sigma_st"], rel=1e-12
    )


def test_driver_bundle_uses_within_subgroup_sigma():
    df = _boards()
    spc = _compute_driver_bundle(df, "Volume", {"usl": 400.0, "lsl": 0.0})["spc"]
    assert spc["metadata"]["sigma_basis"] == "within_subgroup"
    assert spc["statistics"]["mr_boundary_excluded"] == 3


def test_constant_within_every_board_fails_closed():
    # Only between-board steps: MR̄_within = 0 → zero-width limits are undefined.
    df = pd.DataFrame(
        {"BoardNo": [f"B{b}" for b in range(4) for _ in range(5)],
         "Volume": [100.0 + 10 * b for b in range(4) for _ in range(5)]}
    )
    result = SPCEngine.compute_imr(df["Volume"], "Volume", subgroup_ids=df["BoardNo"])
    assert_engine_contract(result, expect_valid=False)


def test_interleaved_boards_pool_by_subgroup_and_match_cpk():
    # A,B,A,B,...: every adjacent MR crosses a board; pooling follows the
    # subgroup grouping (SPC_RULES §4) and still equals the Cpk sigma_within.
    rng = np.random.default_rng(3)
    ids = pd.Series(["A", "B"] * 10)
    vals = pd.Series(np.where(ids == "A", 100.0, 150.0) + rng.normal(0, 1.0, 20))
    imr = SPCEngine.compute_imr(vals, "Volume", subgroup_ids=ids)
    cap = CapabilityEngine.compute_capability(vals, 400.0, 0.0, subgroup_ids=ids)
    expected = np.concatenate([np.abs(np.diff(vals[ids == g].to_numpy())) for g in ("A", "B")]).mean()
    assert imr["statistics"]["mr_bar"] == pytest.approx(expected, rel=1e-12)
    assert imr["statistics"]["mr_boundary_excluded"] == 19
    assert imr["statistics"]["sigma"] == pytest.approx(cap["statistics"]["sigma_st"], rel=1e-12)


def test_missing_subgroup_id_counts_as_boundary():
    df = _boards(n_boards=2, per_board=6)
    ids = df["BoardNo"].copy()
    ids.iloc[3] = None
    result = SPCEngine.compute_imr(df["Volume"], "Volume", subgroup_ids=ids)
    # board change (1) + both MRs touching the missing id (2)
    assert result["statistics"]["mr_boundary_excluded"] == 3
    assert result["metadata"]["sigma_basis"] == "within_subgroup"


def test_driver_bundle_unsorted_input_matches_single_feature_path():
    # Rows shuffled out of board order: the driver bundle must sort by analysis
    # order (PR #8) and take subgroup ids from that same sorted frame, giving the
    # same I-MR as the single-feature path.
    df = _boards(n_boards=4, per_board=6).sample(frac=1.0, random_state=11)
    driver = _compute_driver_bundle(df, "Volume", {"usl": 400.0, "lsl": 0.0})["spc"]
    single = _compute_single_feature_analysis(df, "Volume", usl=400.0, lsl=0.0)["spc"]
    assert driver["metadata"]["sigma_basis"] == "within_subgroup"
    assert driver["statistics"]["mr_boundary_excluded"] == 3
    assert driver["statistics"]["sigma"] == pytest.approx(single["statistics"]["sigma"], rel=1e-12)
    assert driver["statistics"]["mr_bar"] == pytest.approx(single["statistics"]["mr_bar"], rel=1e-12)
