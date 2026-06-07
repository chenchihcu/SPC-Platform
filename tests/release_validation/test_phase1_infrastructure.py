"""Phase 1: golden layout, tolerance policy, deterministic seed hooks."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app.analytics.summary_engine import compute_summary
from app.data.relation.join_engine import JoinEngine
from tests.release_validation.helpers.golden_scenario import (
    load_coords_optional,
    load_manifest,
    load_measurements,
    load_workorder_spec,
    scenario_path,
)
from tests.release_validation.helpers.tolerance import (
    assert_with_tolerance,
    load_tolerance_policy,
)


def test_golden_tolerance_policy_loads(golden_tolerance_path: Path) -> None:
    policy = load_tolerance_policy(golden_tolerance_path)
    assert policy.get("schema_version") == "1"
    assert "mean" in (policy.get("metrics") or {})
    assert "oos_count" in (policy.get("exact_integer_metrics") or [])


def test_assert_with_tolerance_float_mean(golden_tolerance_path: Path) -> None:
    policy = load_tolerance_policy(golden_tolerance_path)
    assert_with_tolerance(1.0, 1.0 + 5e-7, "mean", policy=policy)
    with pytest.raises(AssertionError):
        assert_with_tolerance(1.0, 1.01, "mean", policy=policy)


def test_assert_with_tolerance_exact_oos(golden_tolerance_path: Path) -> None:
    policy = load_tolerance_policy(golden_tolerance_path)
    assert_with_tolerance(3, 3, "oos_count", policy=policy)
    with pytest.raises(AssertionError):
        assert_with_tolerance(3, 4, "oos_count", policy=policy)


def test_assert_with_tolerance_both_none_non_computable(golden_tolerance_path: Path) -> None:
    policy = load_tolerance_policy(golden_tolerance_path)
    assert_with_tolerance(None, None, "cpk", policy=policy)


def test_manifest_tolerance_override_merges(golden_tolerance_path: Path) -> None:
    policy = load_tolerance_policy(golden_tolerance_path)
    assert_with_tolerance(1.0, 1.05, "mean", policy=policy, tolerance_overrides={"mean": {"abs": 0.1}})
    with pytest.raises(AssertionError):
        assert_with_tolerance(1.0, 1.2, "mean", policy=policy, tolerance_overrides={"mean": {"abs": 0.1}})


def test_numpy_random_deterministic_after_session_seed() -> None:
    import numpy as np

    np.random.seed(42)
    b = np.random.randint(0, 1_000_000, size=5)
    np.random.seed(42)
    c = np.random.randint(0, 1_000_000, size=5)
    assert (b == c).all()


def test_normal_baseline_golden_files_exist(golden_root: Path) -> None:
    base = golden_root / "normal_baseline"
    assert (base / "measurements.csv").is_file()
    assert (base / "workorder_spec.json").is_file()
    assert (base / "expected" / "manifest.json").is_file()


def test_normal_baseline_row_count_matches_manifest(golden_root: Path) -> None:
    base = golden_root / "normal_baseline"
    manifest = json.loads((base / "expected" / "manifest.json").read_text(encoding="utf-8"))
    df = pd.read_csv(base / "measurements.csv")
    policy = load_tolerance_policy(golden_root / "golden_tolerance.json")
    assert_with_tolerance(
        manifest["measurement_row_count"],
        len(df),
        "measurement_row_count",
        policy=policy,
    )


def test_normal_baseline_volume_stats_vs_manifest(golden_root: Path) -> None:
    base = golden_root / "normal_baseline"
    manifest = json.loads((base / "expected" / "manifest.json").read_text(encoding="utf-8"))
    policy = load_tolerance_policy(golden_root / "golden_tolerance.json")
    overrides = manifest.get("tolerance_overrides") or {}

    df = pd.read_csv(base / "measurements.csv")
    spec = json.loads((base / "workorder_spec.json").read_text(encoding="utf-8"))
    summary = compute_summary(df, spec)
    vol = summary["per_measure"]["Volume"]
    dist_stats = (vol.get("dist") or {}).get("statistics") or {}
    exp = manifest["expected"]["volume"]

    assert_with_tolerance(exp["n"], vol["n"], "n", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["mean"], dist_stats["mean"], "mean", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["std"], dist_stats["std"], "std", policy=policy, tolerance_overrides=overrides)


@pytest.mark.parametrize(
    "scenario_id",
    (
        "time_only_measurements",
        "timestamp_alias_measurements",
        "datetime_alias_measurements",
        "timestamp_lowercase_measurements",
    ),
)
def test_time_like_column_volume_stats_vs_manifest(golden_root: Path, scenario_id: str) -> None:
    """Same numeric grid as normal_baseline; join + summary with Time / Timestamp / DateTime column."""
    sdir = scenario_path(golden_root, scenario_id)
    manifest = load_manifest(sdir)
    policy = load_tolerance_policy(golden_root / "golden_tolerance.json")
    overrides = manifest.get("tolerance_overrides") or {}
    spec = load_workorder_spec(sdir, manifest)
    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, manifest["expected"]["join"]["coords_file"])
    assert coords is not None
    joined_df, _report = JoinEngine.join(coords, meas)
    summary = compute_summary(joined_df, spec)
    vol = summary["per_measure"]["Volume"]
    dist_stats = (vol.get("dist") or {}).get("statistics") or {}
    exp = manifest["expected"]["volume"]
    assert_with_tolerance(exp["n"], vol["n"], "n", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["mean"], dist_stats["mean"], "mean", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["std"], dist_stats["std"], "std", policy=policy, tolerance_overrides=overrides)


def test_partial_coord_match_volume_stats_vs_manifest(golden_root: Path) -> None:
    """12 rows: 10 matched coords + 2 R99 without coords; volume aggregates over full joined df."""
    sdir = scenario_path(golden_root, "partial_coord_match")
    manifest = load_manifest(sdir)
    policy = load_tolerance_policy(golden_root / "golden_tolerance.json")
    overrides = manifest.get("tolerance_overrides") or {}
    spec = load_workorder_spec(sdir, manifest)
    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, manifest["expected"]["join"]["coords_file"])
    assert coords is not None
    joined_df, _report = JoinEngine.join(coords, meas)
    summary = compute_summary(joined_df, spec)
    vol = summary["per_measure"]["Volume"]
    dist_stats = (vol.get("dist") or {}).get("statistics") or {}
    exp = manifest["expected"]["volume"]
    assert_with_tolerance(exp["n"], vol["n"], "n", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["mean"], dist_stats["mean"], "mean", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["std"], dist_stats["std"], "std", policy=policy, tolerance_overrides=overrides)


def test_refdes_suffix_strip_join_volume_stats_vs_manifest(golden_root: Path) -> None:
    """SPI RefDes with _1 suffix; coords use stripped key after JoinEngine fallback."""
    sdir = scenario_path(golden_root, "refdes_suffix_strip_join")
    manifest = load_manifest(sdir)
    policy = load_tolerance_policy(golden_root / "golden_tolerance.json")
    overrides = manifest.get("tolerance_overrides") or {}
    spec = load_workorder_spec(sdir, manifest)
    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, manifest["expected"]["join"]["coords_file"])
    assert coords is not None
    joined_df, _report = JoinEngine.join(coords, meas)
    summary = compute_summary(joined_df, spec)
    vol = summary["per_measure"]["Volume"]
    dist_stats = (vol.get("dist") or {}).get("statistics") or {}
    exp = manifest["expected"]["volume"]
    assert_with_tolerance(exp["n"], vol["n"], "n", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["mean"], dist_stats["mean"], "mean", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["std"], dist_stats["std"], "std", policy=policy, tolerance_overrides=overrides)


def test_duplicate_refdes_coords_volume_stats_vs_manifest(golden_root: Path) -> None:
    """Duplicate RefDes rows in coords.csv; joined volume stats match normal grid."""
    sdir = scenario_path(golden_root, "duplicate_refdes_coords")
    manifest = load_manifest(sdir)
    policy = load_tolerance_policy(golden_root / "golden_tolerance.json")
    overrides = manifest.get("tolerance_overrides") or {}
    spec = load_workorder_spec(sdir, manifest)
    meas = load_measurements(sdir)
    coords = load_coords_optional(sdir, manifest["expected"]["join"]["coords_file"])
    assert coords is not None
    joined_df, _report = JoinEngine.join(coords, meas)
    summary = compute_summary(joined_df, spec)
    vol = summary["per_measure"]["Volume"]
    dist_stats = (vol.get("dist") or {}).get("statistics") or {}
    exp = manifest["expected"]["volume"]
    assert_with_tolerance(exp["n"], vol["n"], "n", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["mean"], dist_stats["mean"], "mean", policy=policy, tolerance_overrides=overrides)
    assert_with_tolerance(exp["std"], dist_stats["std"], "std", policy=policy, tolerance_overrides=overrides)


def test_dataset_version_fixture_matches_normal_baseline_manifest(dataset_version: str) -> None:
    assert dataset_version.startswith("1.0.0-")


def test_golden_profile_fixture_default(golden_profile: str) -> None:
    assert golden_profile == "default"


def test_summary_has_dashboard_layers_contract_path(golden_root: Path) -> None:
    """Phase 1 hook: document actual keys for later L-module tests."""
    base = golden_root / "normal_baseline"
    df = pd.read_csv(base / "measurements.csv")
    spec = json.loads((base / "workorder_spec.json").read_text(encoding="utf-8"))
    summary = compute_summary(df, spec)
    process = summary["process"]
    assert "dashboard_layers" in process
    layers = process["dashboard_layers"]
    assert "layer_1_alarm" in layers
    assert "layer_3_info" in layers
    assert "layer_4_defect_structure" in layers
    assert "layer_7_engineering_info" in layers
    assert "layer_8_diagnosis" in layers
