"""Tests for chart analysis summary mode sync (dashboard KPIs live on DiagnosticPage; chart page toggles manager/engineer mode)."""
from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.chart_analysis_page import ChartAnalysisPage
from app.viewmodels.chart_analysis_viewmodel import (
    SUMMARY_MODE_ENGINEER,
    SUMMARY_MODE_MANAGER,
    ChartAnalysisViewModel,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_viewmodel_summary_mode_defaults_to_manager():
    vm = ChartAnalysisViewModel()
    assert vm.summary_mode == SUMMARY_MODE_MANAGER


def test_chart_page_mode_sync_via_viewmodel(qapp):
    """Chart page mode switching still works through the viewmodel."""
    vm = ChartAnalysisViewModel()
    chart_page = ChartAnalysisPage()

    vm.summary_mode_changed.connect(chart_page.set_summary_mode)
    chart_page.summary_mode_changed.connect(vm.set_summary_mode)

    chart_page.summary_mode_changed.emit(SUMMARY_MODE_ENGINEER)
    assert vm.summary_mode == SUMMARY_MODE_ENGINEER
    assert chart_page._summary_mode == SUMMARY_MODE_ENGINEER

    chart_page.summary_mode_changed.emit(SUMMARY_MODE_MANAGER)
    assert vm.summary_mode == SUMMARY_MODE_MANAGER
    assert chart_page._summary_mode == SUMMARY_MODE_MANAGER
