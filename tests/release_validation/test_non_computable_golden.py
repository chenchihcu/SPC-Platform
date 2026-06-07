"""Non-computable paths: N<10 SPC, sigma=0."""

from __future__ import annotations

from pathlib import Path

from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload
from tests.release_validation.helpers.golden_scenario import (
    load_manifest,
    load_measurements,
    load_workorder_spec,
    scenario_path,
    volume_ul_target_from_spec,
)


def test_sample_lt_10_spc_invalid(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "sample_lt_10")
    manifest = load_manifest(sdir)
    spec = load_workorder_spec(sdir, manifest)
    df = load_measurements(sdir)
    usl, lsl, target = volume_ul_target_from_spec(spec)

    payload, err = compute_analysis_payload(df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    assert err is None and payload is not None
    meta = payload["spc"]["metadata"]
    assert meta["is_valid"] is False
    exp = manifest["non_computable"]
    assert exp["spc_error_substring"] in (meta.get("error") or "")


def test_sigma_zero_spc_invalid(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "sigma_zero_constant")
    manifest = load_manifest(sdir)
    spec = load_workorder_spec(sdir, manifest)
    df = load_measurements(sdir)
    usl, lsl, target = volume_ul_target_from_spec(spec)

    payload, err = compute_analysis_payload(df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    assert err is None and payload is not None
    meta = payload["spc"]["metadata"]
    assert meta["is_valid"] is False
    exp = manifest["non_computable"]
    assert exp["spc_error_substring"] in (meta.get("error") or "")
