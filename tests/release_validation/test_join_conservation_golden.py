"""Join conservation: match + unmatch == measurement rows; joined row count."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.data.relation.join_engine import JoinEngine
from app.data.session_store import filter_analysis_df
from app.utils.constants import FILTER_ALL
from app.utils.dataframe_utils import detect_order_col
from tests.release_validation.helpers.golden_scenario import (
    load_coords_optional,
    load_manifest,
    load_measurements,
    scenario_path,
)
from tests.release_validation.helpers.tolerance import (
    assert_with_tolerance,
    load_tolerance_policy,
)

_JOIN_COORD_SCENARIOS = (
    "normal_baseline",
    "panel_id_instead_of_board",
    "time_only_measurements",
    "timestamp_alias_measurements",
    "datetime_alias_measurements",
    "timestamp_lowercase_measurements",
    "duplicate_refdes_coords",
    "partial_coord_match",
    "refdes_suffix_strip_join",
)

_TIME_ORDER_SCENARIOS = (
    "time_only_measurements",
    "timestamp_alias_measurements",
    "datetime_alias_measurements",
    "timestamp_lowercase_measurements",
)


@pytest.mark.parametrize("scenario_id", _JOIN_COORD_SCENARIOS)
def test_join_report_matches_manifest_for_coord_scenarios(golden_root: Path, scenario_id: str) -> None:
    sdir = scenario_path(golden_root, scenario_id)
    manifest = load_manifest(sdir)
    policy = load_tolerance_policy(golden_root / "golden_tolerance.json")
    ovr = manifest.get("tolerance_overrides") or {}
    join_exp = manifest["expected"]["join"]

    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, join_exp.get("coords_file"))
    assert coords is not None

    joined_df, report = JoinEngine.join(coords, meas)

    assert_with_tolerance(
        join_exp["total_measurements"],
        report["total_measurements"],
        "measurement_row_count",
        policy=policy,
        tolerance_overrides=ovr,
    )
    assert_with_tolerance(join_exp["match_count"], report["match_count"], "n", policy=policy, tolerance_overrides=ovr)
    assert_with_tolerance(join_exp["unmatch_count"], report["unmatch_count"], "n", policy=policy, tolerance_overrides=ovr)

    assert report["match_count"] + report["unmatch_count"] == report["total_measurements"]
    assert len(joined_df) == len(meas)
    assert len(meas) == manifest["measurement_row_count"]


@pytest.mark.parametrize("scenario_id", _JOIN_COORD_SCENARIOS)
def test_filter_and_dropna_conservation_for_coord_scenarios(golden_root: Path, scenario_id: str) -> None:
    sdir = scenario_path(golden_root, scenario_id)
    manifest = load_manifest(sdir)
    meas = load_measurements(sdir)
    join_exp = manifest["expected"]["join"]
    coords = load_coords_optional(sdir, join_exp.get("coords_file"))
    assert coords is not None
    joined_df, _report = JoinEngine.join(coords, meas)

    assert len(joined_df) == manifest["measurement_row_count"]
    vol = joined_df["Volume"].replace([float("inf"), float("-inf")], pd.NA).dropna()
    assert len(vol) == manifest["expected"]["volume"]["n"]


def test_panel_id_filter_uses_panel_column(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "panel_id_instead_of_board")
    manifest = load_manifest(sdir)
    join_exp = manifest["expected"]["join"]
    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, join_exp.get("coords_file"))
    assert coords is not None
    joined_df, _report = JoinEngine.join(coords, meas)
    sub = filter_analysis_df(joined_df, "B1", FILTER_ALL, FILTER_ALL)
    assert len(sub) == 2
    assert sub["PanelId"].astype(str).eq("B1").all()


@pytest.mark.parametrize("scenario_id", _TIME_ORDER_SCENARIOS)
def test_time_or_timestamp_order_col_and_time_filter(golden_root: Path, scenario_id: str) -> None:
    sdir = scenario_path(golden_root, scenario_id)
    manifest = load_manifest(sdir)
    join_exp = manifest["expected"]["join"]
    exp_block = manifest["expected"]
    probe = exp_block["time_filter_probe"]
    want_col = str(exp_block["order_col_expected"])
    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, join_exp.get("coords_file"))
    assert coords is not None
    joined_df, _report = JoinEngine.join(coords, meas)
    assert detect_order_col(joined_df) == want_col
    sub = filter_analysis_df(
        joined_df,
        FILTER_ALL,
        FILTER_ALL,
        FILTER_ALL,
        time_start=str(probe["time_start"]),
        time_end=str(probe["time_end"]),
    )
    assert len(sub) == int(probe["expected_row_count"])


def test_duplicate_refdes_coords_keeps_first_row_xy(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "duplicate_refdes_coords")
    manifest = load_manifest(sdir)
    dedupe = manifest["expected"]["coord_dedupe"]
    join_exp = manifest["expected"]["join"]
    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, join_exp.get("coords_file"))
    assert coords is not None
    joined_df, report = JoinEngine.join(coords, meas)
    assert report.get("match_count") == join_exp["match_count"]
    r1 = str(dedupe["refdes_with_duplicate_coord"])
    xs = joined_df.loc[joined_df["RefDes"].astype(str) == r1, "X"].astype(float).unique().tolist()
    ys = joined_df.loc[joined_df["RefDes"].astype(str) == r1, "Y"].astype(float).unique().tolist()
    assert xs == [float(dedupe["first_xy"][0])]
    assert ys == [float(dedupe["first_xy"][1])]


def test_partial_coord_match_unmatched_rows_have_no_xy(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "partial_coord_match")
    manifest = load_manifest(sdir)
    join_exp = manifest["expected"]["join"]
    unmatched = set(manifest["expected"]["unmatched_refdes"])
    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, join_exp.get("coords_file"))
    assert coords is not None
    joined_df, report = JoinEngine.join(coords, meas)
    assert report["unmatch_count"] == join_exp["unmatch_count"]
    sample = report.get("unmatched_refdes_sample") or []
    assert any(str(x) in unmatched for x in sample)
    for ref in unmatched:
        sub = joined_df[joined_df["RefDes"].astype(str) == ref]
        assert not sub.empty
        assert sub["X"].isna().all() and sub["Y"].isna().all()


def test_refdes_suffix_strip_join_xy_matches_coord_table(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "refdes_suffix_strip_join")
    manifest = load_manifest(sdir)
    join_exp = manifest["expected"]["join"]
    assert join_exp.get("uses_refdes_suffix_fallback") is True
    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, join_exp.get("coords_file"))
    assert coords is not None
    joined_df, report = JoinEngine.join(coords, meas)
    assert report["match_count"] == join_exp["match_count"]
    row = joined_df[joined_df["RefDes"].astype(str) == "R1_1"].iloc[0]
    assert float(row["X"]) == 10.0
    assert float(row["Y"]) == 20.0
