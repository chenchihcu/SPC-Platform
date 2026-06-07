"""resolve_chart_payload: UI vs report context parity on real golden payload."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.analytics.chart_registry import resolve_chart_payload
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload
from tests.release_validation.helpers.golden_scenario import (
    load_joined_normal_baseline,
    volume_ul_target_from_spec,
)


def _volume_payload_from_golden(golden_root: Path):
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    usl, lsl, target = volume_ul_target_from_spec(spec)
    payload, err = compute_analysis_payload(joined_df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    assert err is None and payload is not None
    return payload


# Single selected feature in payload; charts that resolve without requiring 2F/3F data in payload.
_CHART_IDS_1F = [
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


@pytest.mark.parametrize("chart_id", _CHART_IDS_1F)
def test_resolve_chart_payload_ui_report_parity_single_feature(golden_root: Path, chart_id: str) -> None:
    payload = _volume_payload_from_golden(golden_root)
    kwargs: dict = {}
    if chart_id == "histogram_spec":
        kwargs["normalized"] = False
    ui = resolve_chart_payload(payload, chart_id, features=["Volume"], context="ui", **kwargs)
    rep = resolve_chart_payload(payload, chart_id, features=["Volume"], context="report", **kwargs)
    assert ui == rep


def test_resolve_chart_payload_histogram_dual_parity(golden_root: Path) -> None:
    payload = _volume_payload_from_golden(golden_root)
    ui = resolve_chart_payload(
        payload, "histogram_spec", features=["Volume", "Area"], normalized=False, context="ui"
    )
    rep = resolve_chart_payload(
        payload, "histogram_spec", features=["Volume", "Area"], normalized=False, context="report"
    )
    assert ui == rep
