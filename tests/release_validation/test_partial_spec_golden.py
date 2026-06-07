"""Workorder spec missing Area/Height: summary defect + parameters.cap degrade."""

from __future__ import annotations

from pathlib import Path

from app.analytics.summary_engine import compute_summary
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload
from tests.release_validation.helpers.golden_scenario import (
    load_manifest,
    load_measurements,
    load_workorder_spec,
    scenario_path,
    volume_ul_target_from_spec,
)


def test_partial_spec_area_defect_metrics_absent(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "partial_spec")
    manifest = load_manifest(sdir)
    spec = load_workorder_spec(sdir, manifest)
    df = load_measurements(sdir)
    assert len(df) == manifest["measurement_row_count"]

    summary = compute_summary(df, spec)
    area_def = summary["per_measure"]["Area"]["defect"]
    assert area_def["dpmo_feature"] is None
    assert area_def["ppm_total"] is None


def test_partial_spec_parameters_area_capability_invalid(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "partial_spec")
    manifest = load_manifest(sdir)
    spec = load_workorder_spec(sdir, manifest)
    df = load_measurements(sdir)
    usl, lsl, target = volume_ul_target_from_spec(spec)

    payload, err = compute_analysis_payload(df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    assert err is None and payload is not None
    cap_meta = (payload["parameters"]["Area"].get("cap") or {}).get("metadata") or {}
    assert cap_meta.get("is_valid") is False
