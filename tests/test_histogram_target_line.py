"""Regression: work-order spec target must reach the histogram_spec slice and be drawn.

Audit 2026-10-10: get_feature_payload_slice read cap metadata "target" but nothing
ever wrote it, so the histogram never drew a target line. A (USL+LSL)/2 midpoint is
NOT a spec target and must not be drawn as one.
"""
import sys

import numpy as np
import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from app.analytics.chart_registry import (
    get_feature_payload_slice,
    get_multi_feature_payload_slice,
    get_payload_slice,
)
from app.charts.histogram_chart import HistogramChart
from app.viewmodels.chart_analysis_viewmodel import (
    _build_feature_parameters,
    compute_analysis_payload,
)


@pytest.fixture()
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def _df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "BoardNo": np.repeat(np.arange(n // 5), 5),
            "Volume": rng.normal(100.0, 5.0, n),
            "Area": rng.normal(90.0, 4.0, n),
        }
    )


_SPEC_WITH_TARGET = {
    "volume": {"usl": "130", "lsl": "70", "target": "102"},
    "area": {"usl": "110", "lsl": "70", "target": "91"},
}
_SPEC_NO_TARGET = {
    "volume": {"usl": "130", "lsl": "70"},
    "area": {"usl": "110", "lsl": "70"},
}


def _target_labels(ax) -> list[str]:
    return [ln.get_label() for ln in ax.get_lines() if str(ln.get_label()).startswith("Target:")]


def test_feature_parameters_carry_spec_target_into_cap_metadata() -> None:
    params = _build_feature_parameters(_df(), ["Volume", "Area"], _SPEC_WITH_TARGET)
    assert params["Volume"]["cap"]["metadata"]["target"] == pytest.approx(102.0)
    assert params["Area"]["cap"]["metadata"]["target"] == pytest.approx(91.0)


def test_missing_spec_target_is_not_replaced_by_midpoint() -> None:
    params = _build_feature_parameters(_df(), ["Volume"], _SPEC_NO_TARGET)
    assert "target" not in params["Volume"]["cap"]["metadata"]


def test_target_does_not_change_capability_statistics() -> None:
    with_t = _build_feature_parameters(_df(), ["Volume"], _SPEC_WITH_TARGET)
    without_t = _build_feature_parameters(_df(), ["Volume"], _SPEC_NO_TARGET)
    assert with_t["Volume"]["cap"]["statistics"] == without_t["Volume"]["cap"]["statistics"]


def test_histogram_slices_expose_target() -> None:
    params = _build_feature_parameters(_df(), ["Volume", "Area"], _SPEC_WITH_TARGET)
    payload = {"parameters": params, "cap": params["Volume"]["cap"], "dist": params["Volume"]["dist"]}
    assert get_feature_payload_slice(payload, "histogram_spec", "Volume")["target"] == pytest.approx(102.0)
    assert get_payload_slice(payload, "histogram_spec")["target"] == pytest.approx(102.0)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [(_SPEC_WITH_TARGET, 102.0), (_SPEC_NO_TARGET, None)],
)
def test_primary_feature_payload_uses_spec_target_not_orchestrator_fallback(spec, expected) -> None:
    # orchestrator passes a midpoint/sentinel target (100.0); it must not be drawn as spec target.
    payload, err = compute_analysis_payload(_df(), ["Volume"], 130.0, 70.0, 100.0, workorder_spec=spec)
    assert err is None and payload is not None
    assert get_payload_slice(payload, "histogram_spec")["target"] == expected
    assert get_feature_payload_slice(payload, "histogram_spec", "Volume")["target"] == expected


def test_single_feature_histogram_draws_target_line(qapp) -> None:
    params = _build_feature_parameters(_df(), ["Volume"], _SPEC_WITH_TARGET)
    slice_ = get_feature_payload_slice({"parameters": params}, "histogram_spec", "Volume")
    chart = HistogramChart()
    assert chart.draw_chart(slice_) is True
    assert _target_labels(chart.ax) == ["Target: 102.00"]


def test_single_feature_histogram_without_target_draws_no_target_line(qapp) -> None:
    params = _build_feature_parameters(_df(), ["Volume"], _SPEC_NO_TARGET)
    slice_ = get_feature_payload_slice({"parameters": params}, "histogram_spec", "Volume")
    chart = HistogramChart()
    assert chart.draw_chart(slice_) is True
    assert _target_labels(chart.ax) == []


def test_multi_feature_histogram_draws_target_line_per_subplot(qapp) -> None:
    params = _build_feature_parameters(_df(), ["Volume", "Area"], _SPEC_WITH_TARGET)
    merged = get_multi_feature_payload_slice({"parameters": params}, "histogram_spec", ["Volume", "Area"])
    assert merged.get("_multi_feature") is True
    chart = HistogramChart()
    chart.draw_chart(merged)
    labels = [_target_labels(ax) for ax in chart.figure.axes]
    assert labels == [["Target: 102"], ["Target: 91"]]


def _spec_labels(ax) -> list[str]:
    return [str(ln.get_label()) for ln in ax.get_lines() if str(ln.get_label()).startswith(("USL:", "LSL:"))]


def test_target_kept_when_capability_not_computable(qapp) -> None:
    # Too few samples for Cp/Cpk, but the histogram itself still renders.
    params = _build_feature_parameters(_df(5), ["Volume"], _SPEC_WITH_TARGET)
    cap_meta = params["Volume"]["cap"]["metadata"]
    assert cap_meta["is_valid"] is False
    assert cap_meta["target"] == pytest.approx(102.0)
    slice_ = get_feature_payload_slice({"parameters": params}, "histogram_spec", "Volume")
    assert slice_["target"] == pytest.approx(102.0)
    chart = HistogramChart()
    assert chart.draw_chart(slice_) is True
    assert _target_labels(chart.ax) == ["Target: 102.00"]


def test_outlying_target_does_not_hide_valid_spec_limits(qapp) -> None:
    spec = {"volume": {"usl": "130", "lsl": "70", "target": "100000"}}
    params = _build_feature_parameters(_df(), ["Volume"], spec)
    slice_ = get_feature_payload_slice({"parameters": params}, "histogram_spec", "Volume")
    chart = HistogramChart()
    assert chart.draw_chart(slice_) is True
    assert _spec_labels(chart.ax) == ["USL: 130.00", "LSL: 70.00"]
    assert _target_labels(chart.ax) == []
    caveats = [t.get_text() for t in chart.ax.texts if "Target" in t.get_text()]
    assert caveats, "off-scale target must be disclosed, not dropped silently"


def test_multi_feature_outlying_target_does_not_hide_valid_spec_limits(qapp) -> None:
    spec = dict(_SPEC_WITH_TARGET, volume={"usl": "130", "lsl": "70", "target": "100000"})
    params = _build_feature_parameters(_df(), ["Volume", "Area"], spec)
    merged = get_multi_feature_payload_slice({"parameters": params}, "histogram_spec", ["Volume", "Area"])
    chart = HistogramChart()
    chart.draw_chart(merged)
    vol_ax, area_ax = chart.figure.axes
    assert _spec_labels(vol_ax) == ["USL: 130", "LSL: 70"]
    assert _target_labels(vol_ax) == []
    assert _target_labels(area_ax) == ["Target: 91"]
