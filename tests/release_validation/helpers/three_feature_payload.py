"""Build analysis payload with Volume+Area+Height from normal_baseline golden join."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload
from tests.release_validation.helpers.golden_scenario import (
    load_joined_normal_baseline,
    volume_ul_target_from_spec,
)

THREE_FEATURES = ["Volume", "Area", "Height"]


def load_three_feature_payload_from_golden(golden_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (payload, spec) for joined normal_baseline with three display features."""
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    usl, lsl, target = volume_ul_target_from_spec(spec)
    payload, err = compute_analysis_payload(
        joined_df, THREE_FEATURES, usl, lsl, target, workorder_spec=spec
    )
    assert err is None and payload is not None
    return payload, spec
