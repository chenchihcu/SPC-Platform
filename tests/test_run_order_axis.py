"""Sequence charts plot analysis-order positions, not DataFrame row labels.

Regression for the 2026-10-10 audit: after sorting by ``detect_order_col`` the
engines still emit original index labels, which made I-MR / Run / EWMA lines
zig-zag when the file was not already in time/board order, and the 3F engines
consumed the unsorted frame.
"""
import numpy as np
import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from app.analytics.anomaly_3f_engine import Anomaly3FEngine
from app.analytics.ooc_utils import count_contiguous_ooc_clusters, ooc_run_positions
from app.charts.anomaly_3f_chart import Anomaly3FChart
from app.charts.control_chart import ControlChart
from app.charts.ewma_chart import EWMAChart
from app.charts.imr_3f_chart import IMR3F
from app.charts.pattern_recognition_chart import PatternRecognitionChart
from app.charts.run_chart import RunChart
from app.charts.run_chart_3f_chart import RunChart3F
from app.charts.run_order_axis import marker_points, mr_positions, series_axis
from app.utils.dataframe_utils import natural_sort_key
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload


def _ensure_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _shuffled_df(n: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "BoardNo": [f"Board_{i // 4 + 1}" for i in range(n)],
        "RefDes": "R1",
        "PartType": "0402",
        "Volume": rng.normal(100, 5, n),
        "Area": rng.normal(50, 2, n),
        "Height": rng.normal(10, 1, n),
    })
    # Inject one clear outlier so OOC markers exist.
    df.loc[17, "Volume"] = 160.0
    return df.sample(frac=1, random_state=1)


def _expected_order(df: pd.DataFrame) -> list:
    return sorted(df.index, key=lambda i: (natural_sort_key(df.at[i, "BoardNo"]),))


def _payload(df, features):
    payload, err = compute_analysis_payload(df, features, None, None, None, {})
    assert err is None
    return payload


def test_helpers_map_labels_to_positions():
    x, pos = series_axis([7, 3, 9], 3)
    assert x == [1, 2, 3]
    assert marker_points([9, 42], pos, [1.0, 2.0, 3.0]) == ([3], [3.0])
    assert mr_positions([3, 9], pos, 2) == [2, 3]
    # Mismatched labels fall back to 2..N for MR and an empty marker mapping.
    x, pos = series_axis([1], 3)
    assert pos == {} and mr_positions(None, pos, 2) == [2, 3]


def test_ooc_clusters_follow_run_order_not_label_adjacency():
    sequence = [5, 2, 9, 3]
    # Labels 2 and 3 are adjacent as integers but not in run order.
    assert count_contiguous_ooc_clusters(ooc_run_positions([2, 3], sequence)) == 2
    assert count_contiguous_ooc_clusters(ooc_run_positions([2, 9], sequence)) == 1


def test_single_feature_charts_plot_positions_and_ooc_lands_on_value():
    _ensure_qapp()
    df = _shuffled_df()
    payload = _payload(df, ["Volume"])
    spc = payload["spc"]
    labels = spc["data"]["indices"]
    assert labels != sorted(labels), "fixture must exercise unsorted row labels"
    n = len(spc["data"]["values"])

    chart = ControlChart()
    assert chart.draw_chart(spc)
    xs = list(chart.ax.lines[0].get_xdata())
    assert xs == list(range(1, n + 1))
    ooc_label = spc["data"]["out_of_control_indices"][0]
    pos = labels.index(ooc_label) + 1
    ooc_offsets = chart.ax.collections[0].get_offsets()
    assert ooc_offsets[0][0] == pos
    assert ooc_offsets[0][1] == pytest.approx(spc["data"]["values"][pos - 1])
    assert list(chart.ax_mr.lines[0].get_xdata()) == list(range(2, n + 1))

    for cls, key in ((RunChart, "run_chart"), (EWMAChart, "ewma"), (PatternRecognitionChart, "pattern_recognition")):
        c = cls()
        assert c.draw_chart(payload[key])
        assert list(c.ax.lines[0].get_xdata()) == list(range(1, len(payload[key]["data"]["values"]) + 1))


def test_three_feature_charts_and_engines_use_analysis_order():
    _ensure_qapp()
    df = _shuffled_df()
    payload = _payload(df, ["Volume", "Area", "Height"])
    expected = _expected_order(df)

    anomaly = payload["anomaly_3f"]
    assert anomaly["data"]["indices"] == expected
    direct = Anomaly3FEngine.compute_anomaly_3f(df, ["Volume", "Area", "Height"])
    assert sorted(anomaly["data"]["scores"]) == pytest.approx(sorted(direct["data"]["scores"]))
    assert payload["consistency_3f"]["data"]["indices"] == expected

    chart = Anomaly3FChart()
    assert chart.draw_chart(anomaly)
    bar_x = [p.get_x() + p.get_width() / 2 for p in chart.ax.patches]
    assert bar_x == pytest.approx(list(range(1, len(expected) + 1)))

    params = payload["parameters"]
    feats = ["Volume", "Area", "Height"]
    imr = IMR3F()
    assert imr.draw_chart({
        "metadata": {"is_valid": True},
        "_features": feats,
        "_feature_data": {f: params[f]["spc"] for f in feats},
    })
    assert list(imr.figure.axes[0].lines[0].get_xdata()) == list(range(1, len(expected) + 1))
    run3f = RunChart3F()
    assert run3f.draw_chart({
        "metadata": {"is_valid": True},
        "_features": feats,
        "_feature_data": {f: params[f]["run_chart"] for f in feats},
    })
    assert list(run3f.figure.axes[0].lines[0].get_xdata()) == list(range(1, len(expected) + 1))


def test_driver_bundle_matches_single_feature_statistics():
    df = _shuffled_df()
    # EWMA sigma = MR̄/d2 is order-dependent, so equal limits prove equal ordering.
    ewma_1f = _payload(df, ["Volume"])["ewma"]["statistics"]
    for features in (["Volume", "Area"], ["Volume", "Area", "Height"]):
        driver = _payload(df, features)
        # The driver bundle feeds EWMA / run chart / pattern in multi-feature mode.
        assert driver["run_chart"]["data"]["indices"] == _expected_order(df)
        assert driver["ewma"]["statistics"]["ucl"] == pytest.approx(ewma_1f["ucl"])
        assert driver["ewma"]["statistics"]["lcl"] == pytest.approx(ewma_1f["lcl"])
