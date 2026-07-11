"""
Tests for radar (spider) chart renderer.
"""

import pytest
from PySide6.QtWidgets import QApplication
from app.charts.radar_chart import RadarChart


@pytest.fixture(scope="module", autouse=True)
def qapp():
    """Ensure a QApplication exists before creating chart widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def valid_payload():
    return {
        "chart_type": "radar",
        "payload_key": "radar",
        "data": {
            "categories": ["Volume", "Area", "Height"],
            "series": [
                {"name": "Center", "values": [85.0, 78.0, 92.0]},
                {"name": "Left", "values": [72.0, 80.0, 88.0]},
                {"name": "Right", "values": [78.0, 82.0, 90.0]},
            ],
        },
        "metadata": {"is_valid": True, "n_series": 3, "n_categories": 3},
    }


def test_radar_renders_with_valid_data(valid_payload):
    chart = RadarChart()
    result = chart.draw_chart(valid_payload)
    assert result is True


def test_radar_handles_invalid_data():
    chart = RadarChart()
    result = chart.draw_chart({
        "chart_type": "radar",
        "payload_key": "radar",
        "data": {"categories": [], "series": []},
        "metadata": {"is_valid": False, "error": "No data"},
    })
    assert result is False


def test_radar_single_series():
    payload = {
        "chart_type": "radar",
        "payload_key": "radar",
        "data": {
            "categories": ["A", "B", "C", "D"],
            "series": [{"name": "Test", "values": [10.0, 20.0, 15.0, 25.0]}],
        },
        "metadata": {"is_valid": True, "n_series": 1, "n_categories": 4},
    }
    chart = RadarChart()
    result = chart.draw_chart(payload)
    assert result is True


def test_radar_empty_series():
    payload = {
        "chart_type": "radar",
        "payload_key": "radar",
        "data": {
            "categories": ["A", "B"],
            "series": [{"name": "Test", "values": []}],
        },
        "metadata": {"is_valid": True},
    }
    chart = RadarChart()
    result = chart.draw_chart(payload)
    assert result is True
