from __future__ import annotations

import os
import inspect

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QSizePolicy

from app.ui.pages.chart_analysis_page import ChartAnalysisPage
from app.ui.pages import report_export_page
from app.ui.pages.report_export_page import ReportExportPage


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_chart_analysis_selector_works_without_intent_presets(qapp: QApplication) -> None:
    page = ChartAnalysisPage()

    assert not hasattr(page, "_intent_button_group")
    assert not hasattr(page, "_intent_buttons")
    assert page._chart_id_to_checkbox
    assert any(cb.isChecked() for cb in page._chart_id_to_checkbox.values())


def test_report_export_selector_works_without_intent_presets(qapp: QApplication) -> None:
    page = ReportExportPage()

    assert not hasattr(page, "_intent_button_group")
    assert not hasattr(page, "_intent_buttons")
    assert not hasattr(page, "_intent_hint_label")
    assert page._chart_checkboxes
    assert any(cb.isChecked() for cb in page._chart_checkboxes.values())


def test_report_export_coverage_summary_lives_in_compact_header(qapp: QApplication) -> None:
    page = ReportExportPage()

    assert page.chart_coverage_hint.parentWidget().property("headerDensity") == "compact"
    assert not page.chart_coverage_hint.isHidden()
    assert page.main_card.layout().contentsMargins().top() <= 8
    assert page.main_card.objectName() == "reportContent"
    assert page.main_card.frameShape() == QFrame.Shape.NoFrame


def test_report_export_chart_groups_do_not_expand_into_blank_cards(qapp: QApplication) -> None:
    page = ReportExportPage()
    page.resize(1280, 752)
    page.show()
    qapp.processEvents()

    group_frames = [
        frame for frame in page.findChildren(QFrame)
        if frame.objectName() == "controlCard" and frame.parentWidget() is not None
    ]
    assert group_frames
    positions = [
        page.chart_layout.getItemPosition(index)[:2]
        for index in range(page.chart_layout.count())
    ]
    assert {col for _row, col in positions} <= {0, 1}
    assert page.chart_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    for index, first in enumerate(group_frames):
        for second in group_frames[index + 1:]:
            if first.parentWidget() is second.parentWidget():
                assert not first.geometry().intersects(second.geometry())
    for frame in group_frames:
        assert frame.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Maximum
        assert frame.geometry().height() <= frame.sizeHint().height() + 1
    page.close()


def test_report_export_uses_background_worker_without_process_events() -> None:
    source = inspect.getsource(ReportExportPage._export_to_pptx)

    assert "PptxExportWorker" in source
    assert "processEvents" not in source
    assert hasattr(report_export_page.PptxExportWorker, "progress_updated")
