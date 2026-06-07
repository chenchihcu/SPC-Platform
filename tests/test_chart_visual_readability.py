from matplotlib.colors import to_rgba
from PySide6.QtWidgets import QApplication

from app.charts.base_chart import (
    BaseChart,
    add_sample_disclosure,
    annotate_latest_point,
    chart_line_style,
    format_sample_disclosure,
    semantic_line_style,
)
from app.charts.density_chart import DensityChart
from app.charts.pattern_recognition_chart import PatternRecognitionChart
from app.charts.scatter_spec_chart import ScatterSpecChart
from app.ui.theme import get_app_stylesheet
from app.ui.theme.tokens import CHART_AXES_BG, CHART_FIGURE_BG


def _ensure_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_base_chart_applies_layered_background_tokens():
    _ensure_qapp()
    chart = BaseChart()
    assert chart.figure.get_facecolor() == to_rgba(CHART_FIGURE_BG)
    assert chart.ax.get_facecolor() == to_rgba(CHART_AXES_BG)


def test_density_chart_uses_readable_colormap_and_colorbar():
    _ensure_qapp()
    chart = DensityChart()
    payload = {
        "metadata": {"is_valid": True},
        "data": {
            "x": [98.0, 100.0, 101.0, 103.0, 105.0],
            "y": [108.0, 110.0, 111.0, 109.0, 107.0],
            "col_x": "Area",
            "col_y": "Height",
        },
        "statistics": {"gridsize": 12},
    }

    chart.draw_chart(payload)
    assert chart.cbar is not None
    assert chart.cbar.ax.get_ylabel() == "計數"
    assert chart.ax.collections, "Hexbin collection should be rendered."
    assert chart.ax.collections[0].get_cmap().name == "YlGnBu"


def test_chart_line_style_tokens_for_primary_and_secondary():
    primary = chart_line_style(primary=True)
    secondary = chart_line_style(primary=False)
    assert primary["linestyle"] == "-"
    assert primary["linewidth"] > secondary["linewidth"]
    assert secondary["linestyle"] in ("--", "-.")


def test_control_and_spec_limit_styles_are_distinct():
    control = semantic_line_style("control_limit")
    spec = semantic_line_style("spec_limit")
    assert control["color"] != spec["color"]
    assert control["linestyle"] != spec["linestyle"]


def test_latest_point_annotation_and_sample_disclosure_helpers():
    _ensure_qapp()
    chart = BaseChart()
    annotate_latest_point(chart.ax, [0, 1, 2], [10.0, 11.0, 12.0], label="Latest")
    assert any(text.get_text() == "Latest" for text in chart.ax.texts)

    payload = {
        "metadata": {"is_valid": True},
        "statistics": {
            "n": 1200,
            "displayed_n": 500,
            "aggregation_bins": 80,
            "top_n": 20,
            "normalization_basis": "full_valid_data",
        },
        "_normalized": True,
    }
    disclosure = format_sample_disclosure(payload)
    assert "N=1200" in disclosure
    assert "shown=500/1200" in disclosure
    assert "grid=80x80" in disclosure
    assert "top_n=20" in disclosure
    assert "normalized" in disclosure

    add_sample_disclosure(chart.ax, payload)
    assert any("shown=500/1200" in text.get_text() for text in chart.ax.texts)


def test_status_indicator_qss_has_chart_card_states():
    qss = get_app_stylesheet()
    for state in ('state="ready"', 'state="incompatible"', 'state="nodata"', 'state="error"'):
        assert state in qss


def test_scatter_spec_chart_labels_spec_bounds_and_oos_points():
    _ensure_qapp()
    chart = ScatterSpecChart()
    chart.draw_chart(
        {
            "metadata": {"is_valid": True, "col_x": "Area", "col_y": "Height"},
            "data": {
                "x": [5.0, 11.0, 4.0],
                "y": [5.0, 6.0, 12.0],
                "lsl_x": 1.0,
                "usl_x": 10.0,
                "lsl_y": 2.0,
                "usl_y": 9.0,
            },
        }
    )

    texts = [text.get_text() for text in chart.ax.texts]
    assert any("LSL Area" in text for text in texts)
    assert any("USL Area" in text for text in texts)
    assert any("LSL Height" in text for text in texts)
    assert any("USL Height" in text for text in texts)
    legend = chart.ax.get_legend()
    assert legend is not None
    legend_texts = [text.get_text() for text in legend.get_texts()]
    assert "OOS" in legend_texts
    assert chart.ax.patches, "Spec window should remain visible."


def test_pattern_recognition_exposes_latest_and_mean_labels():
    _ensure_qapp()
    chart = PatternRecognitionChart()
    chart.draw_chart(
        {
            "metadata": {"is_valid": True},
            "data": {
                "indices": [0, 1, 2, 3],
                "values": [10.0, 10.5, 12.0, 11.5],
                "hit_indices": [2],
            },
            "statistics": {"mean": 11.0, "rule_count": 1, "hit_point_count": 1},
        }
    )

    texts = [text.get_text() for text in chart.ax.texts]
    assert "Latest" in texts
    assert any(text.startswith("Mean:") for text in texts)
