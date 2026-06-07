import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.debug.ui_runtime_diagnostics import (
    build_ui_diagnostics_snapshot,
    ui_diagnostics_enabled,
)
from app.ui.main_window import MainWindow
from app.ui.theme import apply_dark_theme


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        apply_dark_theme(app)
    return app


def test_ui_diagnostics_flag_is_env_driven(monkeypatch) -> None:
    monkeypatch.setenv("SPC_UI_DIAGNOSTICS", "1")
    assert ui_diagnostics_enabled() is True
    monkeypatch.setenv("SPC_UI_DIAGNOSTICS", "0")
    assert ui_diagnostics_enabled() is False


def test_ui_diagnostics_snapshot_contains_data_setup_geometry() -> None:
    _ensure_app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    QApplication.processEvents()
    window.pages["資料"]._sync_layout_from_width()
    QApplication.processEvents()
    snapshot = build_ui_diagnostics_snapshot(window)
    assert snapshot["app_version"]
    assert snapshot["main_window"]["width"] > 0
    assert snapshot["workspace"]["width"] > 0
    assert snapshot["data_setup"]["tier"] in {1, 2, 3}
    assert snapshot["data_setup"]["layout_budget"]["content_width"] > 0
    assert snapshot["data_setup"]["layout_budget"]["main_height"] > 0
    assert snapshot["data_setup"]["available_w"] >= snapshot["data_setup"]["content_host_width"]
    assert snapshot["data_setup"]["coord_geometry"]["width"] > 0
    assert snapshot["data_setup"]["stencil_geometry"]["width"] > 0
    assert snapshot["data_setup"]["upload_geometry"]["width"] > 0
    assert snapshot["data_setup"]["coord_size_hint"]["height"] > 0
    window.close()
