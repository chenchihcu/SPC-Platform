import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.ui.pages.data_setup_page import DataSetupPage
from app.ui.theme import apply_dark_theme
from app.ui.widgets.page_templates import add_labeled_field, setup_multi_status_header
from app.ui.widgets.status_bar import StatusBarWidget


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        apply_dark_theme(app)
    return app


def test_add_labeled_field_binds_buddy_and_accessible_name() -> None:
    _ensure_app()
    host = QWidget()
    grid = QGridLayout(host)
    field = QLineEdit()

    label = add_labeled_field(grid, 0, 0, "供應商名稱：", field)

    assert label.buddy() is field
    assert label.accessibleName() == "供應商名稱"
    assert field.accessibleName() == "供應商名稱"
    host.close()


def test_data_setup_inline_fields_bind_labels_and_readonly_names() -> None:
    _ensure_app()
    page = DataSetupPage()

    date_label = next(lbl for lbl in page._date_field.findChildren(QLabel) if lbl.text() == "生產日期")
    batch_label = next(lbl for lbl in page._batch_field.findChildren(QLabel) if lbl.text() == "批量")

    assert date_label.buddy() is page.production_date_edit
    assert page.production_date_edit.accessibleName() == "生產日期"
    assert batch_label.buddy() is page.batch_qty_display
    assert page.batch_qty_display.accessibleName() == "批量"
    assert "批量顯示" in page.batch_qty_display.accessibleDescription()
    page.close()


def test_multi_status_header_marks_lamps_decorative_and_labels_semantic() -> None:
    _ensure_app()
    host = QWidget()
    layout = QVBoxLayout(host)

    _, lamps = setup_multi_status_header(layout, "資料設定", [("coord", "座標")])
    lamp, label = lamps["coord"]

    assert lamp.accessibleName() == ""
    assert "裝飾性狀態指示" in lamp.accessibleDescription()
    assert label.accessibleName() == "座標"
    assert "狀態：" in label.accessibleDescription()
    host.close()


def test_status_bar_progress_accessibility_tracks_progress_states() -> None:
    _ensure_app()
    widget = StatusBarWidget()

    widget._on_progress_changed(42)
    assert not widget._progress_bar.isHidden()
    assert widget._progress_bar.accessibleName() == "分析進度"
    assert "42%" in widget._progress_bar.accessibleDescription()

    widget._on_progress_changed(-1)
    assert "尚未確定" in widget._progress_bar.accessibleDescription()

    widget._on_progress_changed(-2)
    assert widget._progress_bar.isHidden()
    assert "未顯示" in widget._progress_bar.accessibleDescription()
    widget.close()
