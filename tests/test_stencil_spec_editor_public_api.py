import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.data.product_spec_registry import STENCIL_STEPPED
from app.ui.widgets.stencil_spec_editor import StencilSpecEditor


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_load_selected_product_spec_without_product_shows_prompt_in_embedded_mode() -> None:
    _ensure_app()
    editor = StencilSpecEditor(embedded=True)

    editor.set_summary_mode(False)
    editor.product_combo.setCurrentIndex(-1)
    editor.load_selected_product_spec()

    assert "請先選擇或新增產品" in editor.summary_spec_lbl.text()
    editor.close()


def test_load_selected_product_spec_without_saved_spec_resets_to_defaults(monkeypatch) -> None:
    _ensure_app()
    editor = StencilSpecEditor(embedded=True)

    monkeypatch.setattr("app.ui.widgets.stencil_spec_editor.get_product_spec", lambda _name: None)
    editor.product_combo.clear()
    editor.product_combo.addItem("P1", "P1")
    editor.product_combo.setCurrentIndex(0)
    editor.thickness_main.setText("0.2")
    editor.thickness_precision.setText("0.1")

    editor.load_selected_product_spec()

    assert editor.thickness_main.text() == ""
    assert editor.thickness_main.placeholderText() == "0.12"
    assert editor.thickness_precision.text() == ""
    assert editor.thickness_precision.placeholderText() == "0.08"
    assert editor.type_combo.currentIndex() == 0
    assert "尚未設定" in editor.summary_spec_lbl.text()
    editor.close()


def test_load_selected_product_spec_applies_saved_values(monkeypatch) -> None:
    _ensure_app()
    editor = StencilSpecEditor(embedded=True)

    spec = {
        "stencil_type": STENCIL_STEPPED,
        "thickness_main": 0.15,
        "thickness_precision": 0.09,
        "precision_is_main": False,
        "default_volume_lsl": 75.0,
        "default_volume_usl": 135.0,
        "default_area_lsl": 80.0,
        "default_area_usl": 130.0,
        "default_height_lsl": 78.0,
        "default_height_usl": 128.0,
    }
    monkeypatch.setattr("app.ui.widgets.stencil_spec_editor.get_product_spec", lambda _name: spec)

    called = {"refresh_refdes_list": False}

    def _mark_refresh() -> None:
        called["refresh_refdes_list"] = True

    monkeypatch.setattr(editor, "refresh_refdes_list", _mark_refresh)

    editor.product_combo.clear()
    editor.product_combo.addItem("P1", "P1")
    editor.product_combo.setCurrentIndex(0)

    editor.load_selected_product_spec()

    assert editor.thickness_main.text() == "0.15"
    assert editor.thickness_precision.text() == "0.09"
    assert editor.type_combo.currentData() == STENCIL_STEPPED
    assert editor.precision_which.currentIndex() == 1
    assert editor.vol_lsl.text() == "75.0"
    assert editor.vol_usl.text() == "135.0"
    assert "V:75.0-135.0%" in editor.summary_spec_lbl.text()
    assert called["refresh_refdes_list"] is True
    editor.close()
