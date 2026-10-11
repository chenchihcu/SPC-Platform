"""Regression tests for the SPI_Analysis_Report number-audit fixes.

Covers three defects found by comparing the generated deck against a
recomputation from the source measurement session:

* Dual/contradictory Cpk per feature — the capability table and the anomaly
  diagnosis computed the order-dependent moving-range sigma on differently
  ordered data (lexicographic ``Board_10 < Board_2`` vs natural load order).
* Inverted Cpk confidence interval — ``max(0.0, ...)`` clamped the lower bound
  above the upper bound for negative Cpk (e.g. ``[0.000, -23108.696]``).
* Double-rounded OOC ratio — ``round(ratio, 4)`` then a 1-dp percent render
  turned 57.15% into 57.1% instead of 57.2%.
"""
import numpy as np
import pandas as pd

from app.analytics.capability_engine import CapabilityEngine
from app.analytics.summary_engine import _cpk_95ci_text
from app.services.report_formatters import format_pptx_evidence_lines
from app.utils.dataframe_utils import sort_by_order_col
from app.viewmodels.chart_analysis_viewmodel import _compute_single_feature_analysis


def _multi_board_df(n_boards: int = 12, per_board: int = 30) -> pd.DataFrame:
    """Synthetic melted measurement frame spanning enough boards that
    lexicographic and natural BoardNo ordering diverge (Board_10 vs Board_2)."""
    rng = np.random.default_rng(123)
    rows = []
    for b in range(1, n_boards + 1):
        for _ in range(per_board):
            rows.append({"BoardNo": f"Board_{b}", "Volume": rng.normal(100.0, 5.0)})
    return pd.DataFrame(rows)


# ── order unification: capability must be path-independent ─────────────────────
def test_natural_sort_orders_boards_numerically():
    df = _multi_board_df()
    ordered = sort_by_order_col(df, "BoardNo")["BoardNo"].tolist()
    first_seen = list(dict.fromkeys(ordered))
    assert first_seen[:3] == ["Board_1", "Board_2", "Board_3"]
    assert first_seen.index("Board_2") < first_seen.index("Board_10")


def test_viewmodel_capability_matches_natural_order_table():
    """The diagnosis path (viewmodel) and the table path (summary_engine) must
    yield an identical Cpk — no dual value. Both pass the board subgroup ids for
    within-subgroup short-term sigma, so the reference mirrors summary_engine."""
    df = _multi_board_df()
    table = CapabilityEngine.compute_capability(
        df["Volume"], usl=120.0, lsl=80.0, subgroup_ids=df["BoardNo"]
    )
    diag = _compute_single_feature_analysis(df, "Volume", usl=120.0, lsl=80.0)["cap"]
    assert diag["statistics"]["cpk"] == table["statistics"]["cpk"]
    assert diag["statistics"]["cp"] == table["statistics"]["cp"]


def test_within_subgroup_sigma_excludes_board_boundary_jump():
    """A moving range that straddles a board boundary must not inflate the
    short-term sigma. Two tight boards at very different levels: whole-series MR
    sees one huge boundary jump; within-subgroup MR excludes it."""
    values = [1.0, 1.1, 1.0, 1.1, 1.0, 1.1] + [100.0, 100.1, 100.0, 100.1, 100.0, 100.1]
    boards = ["Board_1"] * 6 + ["Board_2"] * 6
    data = pd.Series(values)
    sub = pd.Series(boards)
    whole = CapabilityEngine.compute_capability(data, usl=200.0, lsl=-200.0)
    within = CapabilityEngine.compute_capability(
        data, usl=200.0, lsl=-200.0, subgroup_ids=sub
    )
    # The boundary jump (|100 - 1.1| ~ 99) dominates whole-series MR but is
    # excluded within-subgroup, so within-subgroup sigma_st is far smaller.
    assert within["statistics"]["sigma_st"] < whole["statistics"]["sigma_st"] / 10


def test_subgroup_ids_none_matches_whole_series():
    """Omitting subgroup ids preserves the legacy whole-series MR behavior."""
    df = _multi_board_df()
    default = CapabilityEngine.compute_capability(df["Volume"], usl=120.0, lsl=80.0)
    explicit_none = CapabilityEngine.compute_capability(
        df["Volume"], usl=120.0, lsl=80.0, subgroup_ids=None
    )
    assert default["statistics"]["sigma_st"] == explicit_none["statistics"]["sigma_st"]


def test_sort_by_order_col_none_is_noop():
    df = _multi_board_df(n_boards=2, per_board=2)
    assert sort_by_order_col(df, None).equals(df)
    assert sort_by_order_col(df, "MissingCol").equals(df)


# ── Cpk confidence interval must never invert ─────────────────────────────────
def test_cpk_ci_not_inverted_for_negative_cpk():
    """Negative Cpk previously produced '[0.000, <negative>]' (lower > upper)."""
    text = _cpk_95ci_text(-23352.436, 17632)
    lo, hi = (float(x) for x in text.strip("[]").split(","))
    assert lo < hi, f"CI must be ordered, got {text}"
    assert lo < -23352.436 < hi, "CI must bracket the point estimate"


def test_cpk_ci_still_valid_for_positive_cpk():
    text = _cpk_95ci_text(1.33, 100)
    lo, hi = (float(x) for x in text.strip("[]").split(","))
    assert lo < 1.33 < hi


# ── OOC ratio must not double-round ───────────────────────────────────────────
def test_ooc_ratio_percent_rounds_from_full_precision():
    """10077/17632 = 57.15% must render as 57.2%, not 57.1%."""
    ratio = round(10077 / 17632, 6)
    assert format_pptx_evidence_lines({"ooc_ratio": ratio}) == ["OOC Ratio: 57.2%"]


def test_summary_cpk_matches_chart_page_when_time_order_differs_from_load_order():
    """compute_summary must use the same Time run order as the chart page, so the
    report Cpk equals the Capability chart Cpk (order-dependent within-board MR)."""
    from app.analytics.summary_engine import compute_summary

    df = _multi_board_df(n_boards=4, per_board=25)
    rng = np.random.default_rng(7)
    # Time order deliberately differs from load order inside every board.
    df["Time"] = pd.Series(rng.permutation(len(df)), index=df.index).map(
        lambda k: f"2026-01-01 00:{k // 60:02d}:{k % 60:02d}"
    )
    spec = {"volume": {"usl": "120", "lsl": "80", "target": "100"}}
    summary = compute_summary(df, spec)
    table_cpk = summary["per_measure"]["Volume"]["cap"]["statistics"]["cpk"]
    chart_cpk = _compute_single_feature_analysis(df, "Volume", usl=120.0, lsl=80.0)[
        "cap"
    ]["statistics"]["cpk"]
    assert table_cpk == chart_cpk


def test_duplicate_index_falls_back_to_whole_series_sigma():
    """Duplicate index labels make subgroup alignment ambiguous; capability must
    fall back to whole-series MR instead of raising on reindex()."""
    df = _multi_board_df(n_boards=3, per_board=20)
    df.index = [0] * len(df)
    # A missing reading makes the cleaned series a strict subset of the
    # duplicate-labelled subgroup ids — the case where reindex() raised.
    df.iloc[5, df.columns.get_loc("Volume")] = np.nan
    cap = CapabilityEngine.compute_capability(
        df["Volume"], usl=120.0, lsl=80.0, subgroup_ids=df["BoardNo"]
    )
    ref = CapabilityEngine.compute_capability(df["Volume"], usl=120.0, lsl=80.0)
    assert cap["metadata"]["is_valid"] is True
    assert cap["statistics"]["cpk"] == ref["statistics"]["cpk"]
