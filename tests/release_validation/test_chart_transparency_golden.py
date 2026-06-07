"""G: invalid / edge analytics remain observable via resolver metadata (no silent empty)."""

from __future__ import annotations

from pathlib import Path

from app.analytics.chart_registry import get_payload_slice
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload
from tests.release_validation.helpers.golden_scenario import (
    load_manifest,
    load_measurements,
    load_workorder_spec,
    scenario_path,
    volume_ul_target_from_spec,
)


def test_invalid_spc_payload_slice_preserves_metadata_error(golden_root: Path) -> None:
    """Global I-MR slice must stay tied to top-level spc metadata (N<10 invalid)."""
    sdir = scenario_path(golden_root, "sample_lt_10")
    manifest = load_manifest(sdir)
    spec = load_workorder_spec(sdir, manifest)
    df = load_measurements(sdir)
    usl, lsl, target = volume_ul_target_from_spec(spec)
    payload, err = compute_analysis_payload(df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    assert err is None and payload is not None

    raw = get_payload_slice(payload, "imr")
    meta = raw.get("metadata") if isinstance(raw, dict) else None
    assert isinstance(meta, dict)
    assert meta.get("is_valid") is False
    err_txt = str(meta.get("error") or "")
    assert err_txt, "transparency: invalid SPC should surface non-empty error"
    assert manifest["non_computable"]["spc_error_substring"] in err_txt
