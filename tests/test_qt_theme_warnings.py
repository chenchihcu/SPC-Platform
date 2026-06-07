"""Regression: main window construction must not emit Qt stylesheet / tab-order warnings."""
import sys

import pytest
from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication


@pytest.fixture()
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_main_window_emits_no_stylesheet_or_taborder_warnings(qapp) -> None:
    from app.bootstrap.dpi import setup_high_dpi
    from app.ui.main_window import MainWindow
    from app.ui.theme import apply_app_theme

    captured: list[str] = []

    def handler(msg_type, context, message: str) -> None:
        if msg_type >= QtMsgType.QtWarningMsg:
            captured.append(message)

    qInstallMessageHandler(handler)
    setup_high_dpi()
    apply_app_theme(qapp)
    window = MainWindow()
    window.show()
    qapp.processEvents()
    qInstallMessageHandler(None)

    bad = [
        m
        for m in captured
        if "stylesheet" in m.lower() or "setTabOrder" in m
    ]
    assert not bad, f"Unexpected Qt warnings: {bad}"


def test_theme_api_keeps_app_names_and_compatibility_aliases(qapp) -> None:
    from app.ui.theme import (
        apply_app_theme,
        apply_dark_theme,
        get_app_stylesheet,
        get_dark_stylesheet,
    )

    assert get_app_stylesheet() == get_dark_stylesheet()
    apply_app_theme(qapp)
    assert qapp.styleSheet() == get_app_stylesheet()
    apply_dark_theme(qapp)
    assert qapp.styleSheet() == get_app_stylesheet()
