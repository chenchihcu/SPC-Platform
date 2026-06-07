"""Regression: after figure.clear() + new subplots, primary axes must stay on the figure (P4)."""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from app.charts.boxplot_chart import BoxplotChart
from app.charts.histogram_chart import HistogramChart
from app.ui.tabs.normality_tab import NormalityTab


@pytest.fixture()
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_histogram_multi_feature_binds_self_ax_to_figure(qapp) -> None:
    chart = HistogramChart()
    payload = {
        "_multi_feature": True,
        "_features": ["Volume", "Area"],
        "_feature_data": {
            "Volume": {"metadata": {"is_valid": False, "error": "x"}},
            "Area": {"metadata": {"is_valid": False, "error": "y"}},
        },
    }
    chart._draw_multi_feature(payload)
    assert chart.ax in chart.figure.axes
    assert chart.ax.figure is chart.figure


def test_histogram_multi_feature_empty_binds_self_ax(qapp) -> None:
    chart = HistogramChart()
    chart._draw_multi_feature(
        {
            "_multi_feature": True,
            "_features": [],
            "_feature_data": {},
        }
    )
    assert chart.ax in chart.figure.axes
    assert chart.ax.figure is chart.figure


def test_boxplot_overview_3f_binds_self_ax(qapp) -> None:
    chart = BoxplotChart()
    chart.show()
    payload = {
        "metadata": {"is_valid": True},
        "_overview_3f": True,
        "_features": ["Volume", "Area"],
        "_normalized": False,
        "_feature_data": {
            "Volume": {"data": {"values": [1.0, 2.0, 3.0]}},
            "Area": {"data": {"values": [4.0, 5.0, 6.0]}},
        },
    }
    assert chart.draw_chart(payload) is True  # requires chart.show() — return tracks canvas.isVisible()
    assert chart.ax in chart.figure.axes
    assert chart.ax.figure is chart.figure


def test_normality_tab_multi_feature_binds_self_ax(qapp) -> None:
    tab = NormalityTab()
    tab.update_data(
        {
            "_multi_feature": True,
            "_features": ["Volume", "Area"],
            "_feature_data": {
                "Volume": {"metadata": {"is_valid": False, "error": "x"}, "data": {}, "statistics": {}},
                "Area": {"metadata": {"is_valid": False, "error": "y"}, "data": {}, "statistics": {}},
            },
        }
    )
    assert tab.ax in tab.figure.axes
    assert tab.ax.figure is tab.figure
