import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.coordinate_manager_page import CoordinateManagerPage
from app.ui.theme import apply_dark_theme


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        apply_dark_theme(app)
    return app


def test_embedded_bind_section_auto_expands_after_valid_coordinate() -> None:
    _ensure_app()
    page = CoordinateManagerPage(embedded=True)
    page.show()
    QApplication.processEvents()

    assert page._btn_bind_section.isChecked() is False
    assert page._bind_container.isVisible() is False

    page._on_validation_finished("C:/tmp/coord.csv", True, [], 10)
    QApplication.processEvents()

    assert page._btn_bind_section.isChecked() is True
    assert page._bind_container.isVisible() is True
    page.close()
