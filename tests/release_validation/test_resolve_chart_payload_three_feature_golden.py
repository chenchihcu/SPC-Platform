"""resolve_chart_payload UI/report parity for 3F charts on real golden payload."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.analytics.chart_registry import resolve_chart_payload
from tests.release_validation.helpers.three_feature_payload import (
    THREE_FEATURES,
    load_three_feature_payload_from_golden,
)

_CHART_IDS_3F_ROOT = [
    "anomaly_3f",
    "consistency_3f",
    "parallel_coord",
    "pass_fail_matrix",
]

_CHART_IDS_3F_PARALLEL = [
    "imr_3f",
    "run_chart_3f",
    "ewma_3f",
    "cusum_3f",
    "boxplot_3f",
]


@pytest.mark.parametrize("chart_id", _CHART_IDS_3F_ROOT)
def test_resolve_3f_root_charts_ui_report_parity(golden_root: Path, chart_id: str) -> None:
    payload, _spec = load_three_feature_payload_from_golden(golden_root)
    ui = resolve_chart_payload(payload, chart_id, features=THREE_FEATURES, context="ui")
    rep = resolve_chart_payload(payload, chart_id, features=THREE_FEATURES, context="report")
    assert ui == rep


@pytest.mark.parametrize("chart_id", _CHART_IDS_3F_PARALLEL)
def test_resolve_3f_parallel_charts_ui_report_parity(golden_root: Path, chart_id: str) -> None:
    payload, _spec = load_three_feature_payload_from_golden(golden_root)
    ui = resolve_chart_payload(
        payload, chart_id, features=THREE_FEATURES, normalized=True, context="ui"
    )
    rep = resolve_chart_payload(
        payload, chart_id, features=THREE_FEATURES, normalized=True, context="report"
    )
    assert ui == rep


def test_resolve_histogram_triple_ui_report_parity(golden_root: Path) -> None:
    payload, _spec = load_three_feature_payload_from_golden(golden_root)
    ui = resolve_chart_payload(
        payload,
        "histogram_spec",
        features=THREE_FEATURES,
        normalized=False,
        context="ui",
    )
    rep = resolve_chart_payload(
        payload,
        "histogram_spec",
        features=THREE_FEATURES,
        normalized=False,
        context="report",
    )
    assert ui == rep


def test_resolve_correlation_matrix_dual_on_three_feature_payload_parity(golden_root: Path) -> None:
    payload, _spec = load_three_feature_payload_from_golden(golden_root)
    pair = ["Volume", "Area"]
    ui = resolve_chart_payload(payload, "correlation_matrix", features=pair, context="ui")
    rep = resolve_chart_payload(payload, "correlation_matrix", features=pair, context="report")
    assert ui == rep
