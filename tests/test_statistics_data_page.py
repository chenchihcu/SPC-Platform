from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidget, QLabel

from app.analytics.chart_registry import TEXT_SUMMARY_CHART_IDS
from app.ui.pages.statistics_data_page import StatisticsDataPage


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _valid_summary(
    *,
    count_key: str,
    count: int,
    n_key: str,
    n: int,
    ratio_key: str,
    ratio: float,
    status_key: str,
    status: str,
    summary: str,
) -> dict:
    return {
        "metadata": {"is_valid": True},
        "data": {
            count_key: count,
            n_key: n,
            ratio_key: ratio,
            status_key: status,
            "summary_lines": [summary],
        },
        "statistics": {},
    }


def _summary_payload() -> dict:
    return {
        "selected_features": ["Volume"],
        "ooc_analysis": _valid_summary(
            count_key="ooc_count",
            count=2,
            n_key="n",
            n=10,
            ratio_key="ooc_ratio",
            ratio=0.2,
            status_key="severity",
            status="Alarm",
            summary="OOC Count: 2 / 10",
        ),
        "shift_detection": _valid_summary(
            count_key="ooc_count",
            count=1,
            n_key="n",
            n=10,
            ratio_key="ooc_ratio",
            ratio=0.1,
            status_key="shift_level",
            status="Local Shift",
            summary="CUSUM exceeded local threshold.",
        ),
        "drift_detection": {
            "metadata": {"is_valid": True},
            "data": {
                "drift_abs": 0.25,
                "cl": 1.0,
                "trend_level": "Warning Drift",
                "summary_lines": ["EWMA drift ratio above warning."],
            },
            "statistics": {},
        },
        "outlier_analysis": _valid_summary(
            count_key="outlier_count",
            count=3,
            n_key="total_n",
            n=20,
            ratio_key="outlier_ratio",
            ratio=0.15,
            status_key="level",
            status="Alarm",
            summary="Outliers detected.",
        ),
    }


def test_statistics_data_page_renders_one_page_summary_table(qapp: QApplication) -> None:
    page = StatisticsDataPage()
    page.update_all_statistics(_summary_payload())
    qapp.processEvents()

    assert page.table.rowCount() == len(TEXT_SUMMARY_CHART_IDS)
    assert page.findChildren(QListWidget) == []
    assert page.table.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert not page.empty_hint.isVisible()
    assert set(page._row_by_chart_id) == set(TEXT_SUMMARY_CHART_IDS)
    assert "統計資料 | 特徵: Volume" in page.context_strip.text()
    assert page.table.cellWidget(0, 0) is not None
    assert page.table.cellWidget(0, 1) is not None

    summary_items = [
        page.table.item(row, 6).text()
        for row in range(page.table.rowCount())
        if page.table.item(row, 6) is not None
    ]
    assert any("OOC Count" in text for text in summary_items)


def test_statistics_data_page_select_summary_highlights_requested_row(qapp: QApplication) -> None:
    page = StatisticsDataPage()
    page.update_all_statistics(_summary_payload())
    page.select_summary("drift_detection", ["Volume"])
    qapp.processEvents()

    row = page._row_by_chart_id["drift_detection"]
    assert page.table.currentRow() == row
    assert page.table.selectedItems()


def test_statistics_data_page_target_viewport_shows_all_rows_without_horizontal_scroll(
    qapp: QApplication,
) -> None:
    page = StatisticsDataPage()
    page.resize(894, 633)
    page.update_all_statistics(_summary_payload())
    page.show()
    qapp.processEvents()

    last_row = page.table.rowCount() - 1
    last_row_bottom = page.table.rowViewportPosition(last_row) + page.table.rowHeight(last_row)

    assert last_row_bottom <= page.table.viewport().height()
    assert page.table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    page.close()


def test_statistics_data_page_icon_name_cells_keep_accessible_text(qapp: QApplication) -> None:
    page = StatisticsDataPage()
    page.update_all_statistics(_summary_payload())
    qapp.processEvents()

    for chart_id, row in page._row_by_chart_id.items():
        name_cell = page.table.cellWidget(row, 0)
        labels = name_cell.findChildren(QLabel) if name_cell is not None else []
        assert labels
        assert any(label.toolTip() for label in labels)
        assert chart_id in TEXT_SUMMARY_CHART_IDS
