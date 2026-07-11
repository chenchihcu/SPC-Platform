"""
Tests for LISA cluster map chart renderer.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import numpy as np
import pytest
from app.charts.lisa_chart import LisaChart


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _points_with_categories(
    n_hh: int = 5, n_ll: int = 5, n_hl: int = 3, n_lh: int = 3, n_ns: int = 4,
) -> list[dict]:
    """Build synthetic LISA point data with all five categories."""
    rng = np.random.default_rng(42)
    points: list[dict] = []
    categories = (
        ["HH"] * n_hh + ["LL"] * n_ll + ["HL"] * n_hl + ["LH"] * n_lh + ["NS"] * n_ns
    )
    for cat in categories:
        points.append({
            "x": float(rng.uniform(0, 100)),
            "y": float(rng.uniform(0, 100)),
            "lisa": float(rng.uniform(-3, 3)),
            "category": cat,
            "p_value": 0.01 if cat != "NS" else 0.5,
        })
    return points


@pytest.fixture
def valid_payload():
    points = _points_with_categories()
    return {
        "chart_type": "LISA",
        "data": {
            "global_i": 0.45,
            "p_value": 0.003,
            "z_score": 3.2,
            "points": points,
        },
        "statistics": {},
        "metadata": {
            "is_valid": True,
            "k_neighbors": 3,
            "n_points": len(points),
            "n_hh": 5,
            "n_ll": 5,
            "n_hl": 3,
            "n_lh": 3,
            "n_ns": 4,
        },
    }


def test_chart_renders_with_clusters(valid_payload):
    """Verify chart renders with synthetic LISA data containing all categories."""
    _app()
    chart = LisaChart()
    try:
        result = chart.draw_chart(valid_payload)
        assert result is True
    finally:
        chart.deleteLater()


def test_chart_handles_empty_data():
    """Empty data gracefully handled."""
    _app()
    chart = LisaChart()
    try:
        result = chart.draw_chart({
            "chart_type": "LISA",
            "data": {"points": []},
            "statistics": {},
            "metadata": {"is_valid": False, "error": "無資料。"},
        })
        assert result is False
    finally:
        chart.deleteLater()


def test_chart_handles_no_coordinates():
    """is_valid=False payload handled."""
    _app()
    chart = LisaChart()
    try:
        result = chart.draw_chart({
            "chart_type": "LISA",
            "data": {},
            "statistics": {},
            "metadata": {"is_valid": False, "error": "缺少座標資料。"},
        })
        assert result is False
    finally:
        chart.deleteLater()


def test_chart_legend_contains_metadata(valid_payload):
    """Global I, p-value in legend — verify render succeeds with metadata."""
    _app()
    chart = LisaChart()
    try:
        result = chart.draw_chart(valid_payload)
        assert result is True
        n_artists = len(chart.ax.texts) + len(
            [c for c in chart.ax.get_children() if hasattr(c, "get_label") and c.get_label()]
        )
        assert n_artists > 0
    finally:
        chart.deleteLater()


def test_chart_importable():
    """Module imports correctly."""
    from app.charts.lisa_chart import LISA_COLORS
    assert len(LISA_COLORS) == 5
    assert "HH" in LISA_COLORS
    assert "NS" in LISA_COLORS


def test_chart_handles_flat_arrays():
    """Fallback to flat x/y/classifications arrays works."""
    _app()
    chart = LisaChart()
    try:
        result = chart.draw_chart({
            "chart_type": "LISA",
            "data": {
                "x": [10.0, 20.0, 30.0],
                "y": [15.0, 25.0, 35.0],
                "classifications": ["HH", "LL", "NS"],
            },
            "statistics": {},
            "metadata": {"is_valid": True},
        })
        assert result is True
    finally:
        chart.deleteLater()
