import os

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.chart_analysis_page import ChartAnalysisPage
from app.ui.pages.diagnostic_page import DiagnosticPage

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_chart_card_interpret_button_opens_full_sections(qapp) -> None:
    page = ChartAnalysisPage()
    captured: dict = {}

    def _fake_open_for_chart(*, chart_name, sections, context_lines=None):
        captured["chart_name"] = chart_name
        captured["sections"] = sections
        captured["context_lines"] = context_lines or []
        return 0

    page._interpretation_dialog.open_for_chart = _fake_open_for_chart  # type: ignore[method-assign]

    page._ensure_dashboard_card("imr")
    btn = page._card_interpret_buttons["imr"]
    btn.click()

    assert captured["chart_name"]
    assert len(captured["sections"]) == 4
    assert captured["sections"][1]["title"].endswith("計算函數/公式說明")


def test_diagnostic_interpret_button_opens_layer_sections(qapp) -> None:
    page = DiagnosticPage()
    captured: dict = {}

    def _fake_open_for_diagnostic(*, sections, context_lines=None):
        captured["sections"] = sections
        captured["context_lines"] = context_lines or []
        return 0

    page._interpretation_dialog.open_for_diagnostic = _fake_open_for_diagnostic  # type: ignore[method-assign]

    page._interpret_btn.click()

    assert len(captured["sections"]) == 7
    titles = [s["title"] for s in captured["sections"]]
    assert "1. 警報與健康狀態（layer_1_alarm）" in titles
    assert any("NoData" in line for line in captured["context_lines"])
