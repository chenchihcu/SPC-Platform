import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.data_setup_page import DataSetupPage
from app.ui.theme import apply_dark_theme


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        apply_dark_theme(app)
    return app


def test_upload_event_enters_loading_not_ready() -> None:
    _ensure_app()
    page = DataSetupPage()
    page._on_coord_uploaded("C:/tmp/coord.csv")
    page._on_meas_uploaded("C:/tmp/meas.csv")
    QApplication.processEvents()

    assert page._coord_ready is False
    assert page._meas_ready is False
    assert "載入中…" in page.coord_status_lbl.text()
    assert "載入中…" in page.meas_status_lbl.text()
    assert page.coord_lamp.property("state") == "loading"
    assert page.meas_lamp.property("state") == "loading"
    assert page.btn_start_analysis.isEnabled() is False
    page.close()


def test_update_display_uses_metadata_validity_for_ready_state() -> None:
    _ensure_app()
    page = DataSetupPage()

    page.update_coord_display(None, {"filepath": "C:/tmp/coord.csv", "is_valid": False, "missing_required": ["RefDes"]})
    page.update_meas_display(None, {"filepath": "C:/tmp/meas.csv", "is_valid": False, "missing_required": ["Volume"]})
    QApplication.processEvents()

    assert page._coord_ready is False
    assert page._meas_ready is False
    assert "缺欄位" in page.coord_status_lbl.text()
    assert "缺欄位" in page.meas_status_lbl.text()
    assert page.coord_lamp.property("state") == "warning"
    assert page.meas_lamp.property("state") == "warning"
    page.close()


def test_start_analysis_gate_requires_valid_coord_meas_and_spec() -> None:
    _ensure_app()
    page = DataSetupPage()
    page._current_product = "PRODUCT-A"
    page._spec_ready = True

    page.update_coord_display(None, {"filepath": "C:/tmp/coord.csv", "is_valid": False})
    page.update_meas_display(None, {"filepath": "C:/tmp/meas.csv", "is_valid": True})
    QApplication.processEvents()
    assert page.btn_start_analysis.isEnabled() is False

    page.update_coord_display(None, {"filepath": "C:/tmp/coord.csv", "is_valid": True})
    QApplication.processEvents()
    assert page.btn_start_analysis.isEnabled() is True
    page.close()
