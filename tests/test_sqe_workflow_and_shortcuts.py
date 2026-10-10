# -*- coding: utf-8 -*-
"""
Tests for SQE Daily Workflow and Keyboard Shortcuts in MainWindow.
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_mainwindow_shortcuts_registered(qapp):
    """Verify that SQE productivity shortcuts are registered in MainWindow."""
    w = MainWindow()

    # Inspect registered shortcuts on window
    from PySide6.QtGui import QShortcut
    shortcuts = w.findChildren(QShortcut)
    keys = [s.key().toString() for s in shortcuts]

    # F5 / Ctrl+R, Ctrl+E, Ctrl+1..7 should be registered
    assert any("F5" in k or "Ctrl+R" in k for k in keys), f"F5 or Ctrl+R shortcut not found in {keys}"
    assert any("Ctrl+E" in k for k in keys), f"Ctrl+E shortcut not found in {keys}"
    assert any("Ctrl+1" in k for k in keys), f"Ctrl+1 shortcut not found in {keys}"

    w.close()


def test_mainwindow_tab_navigation_shortcuts(qapp):
    """Verify that tab shortcuts switch the active workflow tab correctly."""
    w = MainWindow()

    # Initial tab should be 資料設定 (index 0)
    assert w.workspace.currentIndex() == 0

    # Test switching to charts (Ctrl+3 or tab index 2)
    w._go_to_workflow_tab(2)
    assert w.workspace.currentIndex() == 2

    # Test switching to diagnostic (tab index 4)
    w._go_to_workflow_tab(4)
    assert w.workspace.currentIndex() == 4

    # Test switching to report (tab index 5)
    w._go_to_workflow_tab(5)
    assert w.workspace.currentIndex() == 5

    w.close()


def test_mainwindow_one_click_analysis_trigger(qapp, monkeypatch):
    """Verify that start_analysis triggers synchronization and analysis worker."""
    w = MainWindow()

    refreshed = []
    monkeypatch.setattr(w, "refresh_analysis", lambda: refreshed.append(True))

    # Trigger from data setup page
    w.pages["資料"].start_analysis_requested.emit()
    assert len(refreshed) == 1

    w.close()
