"""resolve_chart_payload UI/report parity when analysis was computed with 2 selected features."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.analytics.chart_registry import resolve_chart_payload
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload
from tests.release_validation.helpers.golden_scenario import (
    load_joined_normal_baseline,
    volume_ul_target_from_spec,
)

_TWO_FEATURES = ["Volume", "Area"]


def _two_feature_payload_from_golden(golden_root: Path):
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    usl, lsl, target = volume_ul_target_from_spec(spec)
    payload, err = compute_analysis_payload(
        joined_df, _TWO_FEATURES, usl, lsl, target, workorder_spec=spec
    )
    assert err is None and payload is not None
    assert list(payload.get("selected_features") or []) == _TWO_FEATURES
    return payload


# Same 1F chart set as test_resolve_chart_payload_golden (still resolved with 2 active features).
_CHART_IDS_SHARED = [
    "imr",
    "xbar_r",
    "run_chart",
    "ewma",
    "cusum",
    "histogram_spec",
    "boxplot",
    "normality",
    "density",
    "anova_parttype",
    "ooc_analysis",
    "shift_detection",
    "drift_detection",
    "outlier_analysis",
    "pattern_recognition",
    "subgroup",
    "spatial_heatmap",
    "pareto",
    "repeated_offender",
]

# Charts that require dual selection; top-level keys exist on n==2 compute_analysis_payload.
_CHART_IDS_2F_ONLY = [
    "scatter_spec",
    "correlation_matrix",
    "correlation_heatmap",
    "quadrant",
    "bivariate_outlier",
]

_CHART_IDS_2F_ALL = _CHART_IDS_SHARED + _CHART_IDS_2F_ONLY


@pytest.mark.parametrize("chart_id", [c for c in _CHART_IDS_2F_ALL if c != "histogram_spec"])
def test_resolve_chart_payload_ui_report_parity_two_feature(golden_root: Path, chart_id: str) -> None:
    payload = _two_feature_payload_from_golden(golden_root)
    ui = resolve_chart_payload(payload, chart_id, features=_TWO_FEATURES, context="ui")
    rep = resolve_chart_payload(payload, chart_id, features=_TWO_FEATURES, context="report")
    assert ui == rep


def test_resolve_chart_payload_histogram_two_feature_normalized_false_parity(golden_root: Path) -> None:
    payload = _two_feature_payload_from_golden(golden_root)
    ui = resolve_chart_payload(
        payload, "histogram_spec", features=_TWO_FEATURES, normalized=False, context="ui"
    )
    rep = resolve_chart_payload(
        payload, "histogram_spec", features=_TWO_FEATURES, normalized=False, context="report"
    )
    assert ui == rep
