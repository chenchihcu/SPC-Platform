import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.charts.boxplot_chart import BoxplotChart
from app.charts.heatmap_chart import HeatmapChart
from app.charts.parallel_coord_chart import ParallelCoordChart
from app.charts.pareto_chart import ParetoChart
from app.charts.repeated_offender_chart import RepeatedOffenderChart
from app.ui.tabs.normality_tab import NormalityTab


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _group_arrays(n_groups: int, width: int = 4) -> list[list[float]]:
    return [[float(i + j) for j in range(width)] for i in range(n_groups)]


def test_boxplot_chart_single_feature_keeps_all_groups() -> None:
    _ensure_app()
    n_groups = 60
    labels = [f"R{i:03d}" for i in range(n_groups)]
    payload = {
        "metadata": {"is_valid": True},
        "analysis_context": {"target_col": "Volume"},
        "data": {"labels": labels, "arrays": _group_arrays(n_groups)},
    }

    chart = BoxplotChart()
    chart.draw_chart(payload)

    assert len(chart.ax.get_xticks()) == n_groups
    assert "僅顯示前" not in chart.ax.get_title()
    assert f"共 {n_groups} 組" in chart.ax.get_title()


def test_boxplot_chart_multi_feature_keeps_all_groups() -> None:
    _ensure_app()
    n_groups = 60
    labels = [f"R{i:03d}" for i in range(n_groups)]
    arrays = _group_arrays(n_groups)
    payload = {
        "metadata": {"is_valid": True},
        "_multi_feature": True,
        "_features": ["Height", "Area"],
        "_feature_data": {
            "Height": {"metadata": {"is_valid": True}, "data": {"labels": labels, "arrays": arrays}},
            "Area": {"metadata": {"is_valid": True}, "data": {"labels": labels, "arrays": arrays}},
        },
    }

    chart = BoxplotChart()
    chart.draw_chart(payload)

    for ax in chart.figure.axes:
        assert len(ax.get_xticks()) == n_groups
    assert chart.figure._suptitle is not None
    assert "僅顯示前" not in chart.figure._suptitle.get_text()
    assert f"共 {n_groups} 組" in chart.figure._suptitle.get_text()


def test_pareto_chart_keeps_all_categories() -> None:
    _ensure_app()
    n_categories = 60
    categories = [f"C{i:03d}" for i in range(n_categories)]
    counts = [n_categories - i for i in range(n_categories)]
    total = sum(counts)
    running = 0
    cumulative_pct = []
    for count in counts:
        running += count
        cumulative_pct.append(running / total * 100.0)

    chart = ParetoChart()
    chart.draw_chart(
        {
            "metadata": {"is_valid": True},
            "data": {
                "categories": categories,
                "counts": counts,
                "cumulative_pct": cumulative_pct,
            },
        }
    )

    assert len(chart.ax.patches) == n_categories
    assert chart._ax2 is not None
    assert len(chart._ax2.lines[0].get_xdata()) == n_categories
    assert "僅顯示前" not in chart.ax.get_title()
    assert f"共 {n_categories} 類" in chart.ax.get_title()


def test_parallel_coord_chart_discloses_display_sampling() -> None:
    _ensure_app()
    chart = ParallelCoordChart()
    chart.draw_chart(
        {
            "metadata": {"is_valid": True},
            "data": {
                "columns": ["Volume", "Area", "Height"],
                "values": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            },
            "statistics": {
                "sampled_for_display": True,
                "displayed_n": 500,
                "n": 1200,
                "normalization_basis": "full_valid_data",
            },
        }
    )

    texts = [text.get_text() for text in chart.ax.texts]
    assert any("500/1200" in text for text in texts)
    assert any("full_valid_data" in text for text in texts)


def test_normality_tab_discloses_full_tested_sample_count() -> None:
    _ensure_app()
    tab = NormalityTab()
    tab.update_data(
        {
            "metadata": {"is_valid": True},
            "analysis_context": {"target_col": "Volume"},
            "data": {
                "theoretical_q": [-1.0, 0.0, 1.0],
                "actual_q": [90.0, 100.0, 110.0],
                "line_x": [-1.0, 1.0],
                "line_y": [90.0, 110.0],
            },
            "statistics": {
                "p_value": 0.12,
                "r_squared": 0.99,
                "is_normal": True,
                "test_name": "D'Agostino K² (full data / N>5000)",
                "total_n": 8000,
                "tested_n": 8000,
                "sampled_for_test": False,
            },
        }
    )

    assert "8000/8000" in tab.lbl_stats.text()
    assert "抽樣" not in tab.lbl_stats.text()
    texts = [text.get_text() for text in tab.ax.texts]
    assert any("8000/8000" in text for text in texts)


def test_chart_sources_do_not_use_silent_display_truncation_patterns() -> None:
    chart_dir = Path(__file__).resolve().parents[1] / "app" / "charts"
    forbidden = ("_MAX_DISPLAY_", "僅顯示前")
    offenders: dict[str, list[str]] = {}

    for path in chart_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        hits = [token for token in forbidden if token in text]
        if hits:
            offenders[path.name] = hits

    assert offenders == {}


def test_heatmap_chart_discloses_display_aggregation() -> None:
    _ensure_app()
    chart = HeatmapChart()
    chart.draw_chart(
        {
            "metadata": {"is_valid": True, "mode": "value"},
            "data": {
                "x": [0.0, 1.0, 2.0],
                "y": [0.0, 1.0, 2.0],
                "values": [100.0, 101.0, 99.0],
                "labels": ["A", "B", "C"],
            },
            "statistics": {
                "sampled_for_display": True,
                "displayed_n": 3200,
                "n": 120000,
                "aggregation_bins": 80,
            },
        }
    )
    texts = [text.get_text() for text in chart.ax.texts]
    assert any("3200/120000" in text for text in texts)
    assert any("grid=80x80" in text for text in texts)


def test_repeated_offender_chart_discloses_top_n_truncation() -> None:
    _ensure_app()
    chart = RepeatedOffenderChart()
    chart.draw_chart(
        {
            "metadata": {"is_valid": True},
            "analysis_context": {"target_col": "Volume"},
            "data": {"labels": [f"R{i}" for i in range(5)], "counts": [9, 7, 5, 4, 2]},
            "statistics": {
                "sampled_for_display": True,
                "displayed_n": 5,
                "n_refdes_with_violations": 42,
                "top_n": 5,
            },
        }
    )
    texts = [text.get_text() for text in chart.ax.texts]
    assert any("5/42" in text for text in texts)
    assert any("top_n=5" in text for text in texts)
