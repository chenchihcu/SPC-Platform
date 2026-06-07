import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

from app.ui.pages.data_setup_page import DataSetupPage
from app.ui.theme import apply_dark_theme


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        apply_dark_theme(app)
    return app


def test_get_workorder_info_includes_line_and_production_date() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.line_name_combo.setCurrentText("Line 2")
    page.production_date_edit.setDate(QDate(2026, 4, 9))
    info = page.get_workorder_info()
    assert info["line_name"] == "Line 2"
    assert info["production_date"] == "26/04/09"
    page.close()


def test_sync_from_store_applies_line_and_production_date() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.sync_from_store(
        {
            "product_name": "",
            "line_name": "Line 4",
            "production_date": "26/03/15",
        }
    )
    assert page.line_name_combo.currentText() == "Line 4"
    assert page.production_date_edit.date().toString("yy/MM/dd") == "26/03/15"
    page.close()
