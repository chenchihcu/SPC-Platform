"""Measurements without joined X/Y: spatial heatmap invalid (no coords path)."""

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


def test_no_coords_spatial_metadata_invalid(golden_root: Path) -> None:
    sdir = scenario_path(golden_root, "no_coords")
    manifest = load_manifest(sdir)
    spec = load_workorder_spec(sdir, manifest)
    df = load_measurements(sdir)
    usl, lsl, target = volume_ul_target_from_spec(spec)

    assert "X" not in df.columns and "Y" not in df.columns

    payload, err = compute_analysis_payload(df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    assert err is None and payload is not None
    spatial_meta = payload["spatial"]["metadata"]
    assert spatial_meta.get("is_valid") is False
    err_text = str(spatial_meta.get("error") or "")
    subs = manifest["non_computable"]["spatial_error_substrings"]
    assert any(sub in err_text for sub in subs)
