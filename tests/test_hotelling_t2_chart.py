"""
Tests for Hotelling T² chart renderer.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import numpy as np
import pytest
from app.charts.hotelling_t2_chart import HotellingT2Chart


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def valid_payload():
    np.random.seed(42)
    t2_values = np.random.chisquare(3, 50).tolist()
    return {
        "chart_type": "hotelling_t2",
        "payload_key": "hotelling_t2",
        "data": {
            "indices": list(range(50)),
            "t2_values": t2_values,
            "ooc_flags": [False] * 50,
        },
        "statistics": {
            "ucl_value": 12.0,
            "mean_t2": float(np.mean(t2_values)),
            "max_t2": float(max(t2_values)),
            "ooc_count": 0,
            "ooc_pct": 0.0,
        },
        "metadata": {"is_valid": True},
    }


def test_chart_renders_with_ucl(valid_payload):
    _app()
    chart = HotellingT2Chart()
    try:
        result = chart.draw_chart(valid_payload)
        assert result is True
    finally:
        chart.deleteLater()


def test_chart_handles_invalid_data():
    _app()
    chart = HotellingT2Chart()
    try:
        result = chart.draw_chart({
            "chart_type": "hotelling_t2",
            "payload_key": "hotelling_t2",
            "data": {"indices": [], "t2_values": [], "ooc_flags": []},
            "statistics": {
                "ucl_value": 0.0, "mean_t2": 0.0, "max_t2": 0.0,
                "ooc_count": 0, "ooc_pct": 0.0,
            },
            "metadata": {"is_valid": False, "error": "No data"},
        })
        assert result is False
    finally:
        chart.deleteLater()


def test_chart_ooc_markers():
    _app()
    t2_values = [5.0, 6.0, 15.0, 4.0, 20.0]
    payload = {
        "chart_type": "hotelling_t2",
        "payload_key": "hotelling_t2",
        "data": {
            "indices": [0, 1, 2, 3, 4],
            "t2_values": t2_values,
            "ooc_flags": [False, False, True, False, True],
        },
        "statistics": {
            "ucl_value": 10.0,
            "mean_t2": float(np.mean(t2_values)),
            "max_t2": 20.0,
            "ooc_count": 2,
            "ooc_pct": 40.0,
        },
        "metadata": {"is_valid": True},
    }
    chart = HotellingT2Chart()
    try:
        result = chart.draw_chart(payload)
        assert result is True
    finally:
        chart.deleteLater()
