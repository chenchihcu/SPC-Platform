"""A: measurement / joined frames satisfy docs/specs/data_contract.md minimum columns."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.data.relation.join_engine import JoinEngine
from tests.release_validation.helpers.golden_scenario import (
    load_coords_optional,
    load_manifest,
    load_measurements,
    scenario_path,
)

_MEASURE_KEYS = ("Volume", "Area", "Height")
_TIME_LIKE = ("Time", "Timestamp", "timestamp", "DateTime", "Date")


def _scenario_dirs_with_measurements(golden_root: Path) -> list[Path]:
    return sorted(p for p in golden_root.iterdir() if p.is_dir() and (p / "measurements.csv").is_file())


def test_all_measurement_csvs_satisfy_minimum_contract(golden_root: Path) -> None:
    for scenario_dir in _scenario_dirs_with_measurements(golden_root):
        df = pd.read_csv(scenario_dir / "measurements.csv")
        assert "RefDes" in df.columns, scenario_dir.name
        has_board = "BoardNo" in df.columns or "PanelId" in df.columns
        has_time = any(c in df.columns for c in _TIME_LIKE)
        assert has_board or has_time, f"{scenario_dir.name}: need BoardNo, PanelId, or time-like column per data_contract"
        assert any(k in df.columns for k in _MEASURE_KEYS), (
            f"{scenario_dir.name}: need at least one of Volume/Area/Height"
        )


def test_joined_spatial_columns_when_coords_in_manifest(golden_root: Path) -> None:
    for scenario_dir in _scenario_dirs_with_measurements(golden_root):
        mp = scenario_dir / "expected" / "manifest.json"
        doc = json.loads(mp.read_text(encoding="utf-8"))
        join_exp = (doc.get("expected") or {}).get("join") or {}
        coords_name = join_exp.get("coords_file")
        if not coords_name:
            continue
        coords = load_coords_optional(scenario_dir, coords_name)
        assert coords is not None
        meas = load_measurements(scenario_dir)
        joined_df, report = JoinEngine.join(coords, meas)
        assert report.get("can_do_spatial") is True, scenario_dir.name
        assert "X" in joined_df.columns and "Y" in joined_df.columns, scenario_dir.name
        matched = joined_df.dropna(subset=["X", "Y"], how="any")
        assert len(matched) >= int(join_exp.get("match_count") or 0), scenario_dir.name


def test_panel_id_scenario_listed_and_joinable(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "panel_id_instead_of_board")
    manifest = load_manifest(sdir)
    assert manifest["scenario_id"] == "panel_id_instead_of_board"
    assert "PanelId" in pd.read_csv(sdir / "measurements.csv").columns
