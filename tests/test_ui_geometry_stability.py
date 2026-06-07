import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QScrollArea, QSizePolicy

from app.ui.main_window import MainWindow
from app.ui.pages.coordinate_manager_page import CoordinateManagerPage
from app.ui.pages.data_setup_page import DataSetupPage
from app.ui.theme import apply_dark_theme
from app.ui.theme.tokens import (
    DATA_SETUP_TABLE_GAP,
    DATA_SETUP_TABLE_MAIN_MIN_HEIGHT,
    DATA_SETUP_TABLE_SECTION_MIN_HEIGHT,
)


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        apply_dark_theme(app)
    return app


def _assert_no_sibling_overlap(frames: list[QFrame]) -> None:
    for idx, first in enumerate(frames):
        first_rect = first.geometry()
        for second in frames[idx + 1 :]:
            if first.parentWidget() is not second.parentWidget():
                continue
            assert not first_rect.intersects(second.geometry())


def _assert_data_setup_table_layout(page: DataSetupPage) -> None:
    regions = [
        page._workorder_wrap,
        page._coord_region,
        page._spec_region,
        page._upload_region,
    ]
    _assert_no_sibling_overlap(regions)

    workorder = page._workorder_wrap.geometry()
    coord = page._coord_region.geometry()
    spec = page._spec_region.geometry()
    upload = page._upload_region.geometry()
    assert workorder.top() < coord.top()
    assert coord.right() < spec.left()
    assert spec.bottom() < upload.top()
    assert coord.top() == spec.top()
    assert coord.bottom() == upload.bottom()

    budget = page.latest_layout_budget()
    assert budget.content_width > 0
    assert budget.content_height > 0
    assert budget.left_width > 0
    assert budget.right_width > 0
    assert budget.main_height >= DATA_SETUP_TABLE_MAIN_MIN_HEIGHT
    assert budget.left_width + budget.right_width + DATA_SETUP_TABLE_GAP <= budget.content_width


def test_data_setup_cards_do_not_overlap_at_common_sizes() -> None:
    _ensure_app()
    for width, height in ((1200, 700), (1280, 752), (1366, 768), (1920, 1080)):
        page = DataSetupPage()
        page.resize(width, height)
        page.show()
        QApplication.processEvents()
        page._sync_layout_from_width()
        QApplication.processEvents()
        cards = [
            frame
            for frame in page.findChildren(QFrame)
            if frame.objectName() == "stepCard" and frame.isVisible()
        ]
        _assert_no_sibling_overlap(cards)
        _assert_data_setup_table_layout(page)
        page.close()


def test_data_setup_embedded_sections_use_table_regions() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.resize(1280, 752)
    page.show()
    QApplication.processEvents()
    page._sync_layout_from_width()
    QApplication.processEvents()

    for section in (page._coord_page, page._stencil_editor, page._upload_page):
        assert section.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred
    assert page._coord_region.minimumHeight() == DATA_SETUP_TABLE_MAIN_MIN_HEIGHT
    assert page._spec_region.minimumHeight() == DATA_SETUP_TABLE_SECTION_MIN_HEIGHT
    assert page._upload_region.minimumHeight() == DATA_SETUP_TABLE_SECTION_MIN_HEIGHT
    page.close()


def test_coordinate_manager_bind_grid_has_separate_rows() -> None:
    _ensure_app()
    page = CoordinateManagerPage()
    assert page._bind_grid.itemAtPosition(0, 1).widget() is page.product_name_edit
    assert page._bind_grid.itemAtPosition(1, 1).widget() is page.product_part_no_edit
    assert page._bind_grid.itemAtPosition(2, 1).widget() is page.btn_register


def test_data_setup_uses_quantitative_table_budget_when_standalone() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.resize(1920, 1080)
    page.show()
    QApplication.processEvents()
    page._sync_layout_from_width()
    QApplication.processEvents()
    assert page._current_tier == 1
    _assert_data_setup_table_layout(page)
    page.close()


def test_main_window_data_setup_keeps_quantitative_table_layout() -> None:
    _ensure_app()
    window = MainWindow()
    window.resize(2048, 1229)
    window.show()
    QApplication.processEvents()
    page = window.pages["資料"]
    page._sync_layout_from_width()
    QApplication.processEvents()
    assert page._current_tier == 1
    _assert_data_setup_table_layout(page)
    window.close()


def test_data_setup_uses_one_page_table_host() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.resize(2048, 1229)
    page.show()
    QApplication.processEvents()
    page._sync_layout_from_width()
    QApplication.processEvents()
    assert not isinstance(page._content_host, QScrollArea)
    assert page._content_host.objectName() == "dataSetupTable"
    page.close()


def test_data_setup_header_footer_keep_min_height() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.resize(1200, 700)
    page.show()
    QApplication.processEvents()
    page._sync_layout_from_width()
    QApplication.processEvents()
    assert page._header_card.height() >= page._header_card.minimumHeight()
    assert page._footer_card.height() >= page._footer_card.minimumHeight()
    page.close()


def test_data_setup_chrome_regions_do_not_overlap() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.resize(1200, 700)
    page.show()
    QApplication.processEvents()
    page._sync_layout_from_width()
    QApplication.processEvents()
    assert not page._header_card.geometry().intersects(page._content_host.geometry())
    assert not page._content_host.geometry().intersects(page._footer_card.geometry())
    assert not page._header_card.geometry().intersects(page._footer_card.geometry())
    page.close()


def test_data_setup_header_controls_share_compact_row() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.resize(1200, 700)
    page.show()
    QApplication.processEvents()
    page._sync_layout_from_width()
    QApplication.processEvents()
    header_rect = page._header_card.geometry()
    controls = [page.header_lbl, page.product_combo, page.coord_status_lbl]
    centers = [control.mapTo(page, control.rect().center()).y() for control in controls]
    assert max(centers) - min(centers) <= header_rect.height() // 3
    for control in controls:
        top = control.mapTo(page, control.rect().topLeft()).y()
        bottom = control.mapTo(page, control.rect().bottomLeft()).y()
        assert header_rect.top() <= top <= bottom <= header_rect.bottom()
    page.close()


def test_data_setup_embedded_mode_hides_step_titles() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.resize(1920, 1080)
    page.show()
    QApplication.processEvents()
    texts = [label.text() for label in page.findChildren(QLabel) if label.isVisible()]
    assert not any(text.startswith("步驟") for text in texts)
    page.close()


def test_data_setup_core_labels_fit_table_regions() -> None:
    _ensure_app()
    page = DataSetupPage()
    page.resize(1280, 752)
    page.show()
    QApplication.processEvents()
    page._sync_layout_from_width()
    QApplication.processEvents()

    critical = {"資料設定", "座標", "鋼板規格", "量測", "整體狀態"}
    for label in page.findChildren(QLabel):
        text = label.text().replace("：", "").strip()
        if text not in critical or not label.isVisible():
            continue
        metrics = QFontMetrics(label.font())
        assert metrics.horizontalAdvance(label.text()) <= label.width()
    page.close()
