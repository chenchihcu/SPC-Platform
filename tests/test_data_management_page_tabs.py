from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget

from app.analytics.chart_registry import CHART_ORDER
from app.ui.pages.data_management_page import DataManagementPage


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_data_management_page_has_chart_reference_tab_rightmost() -> None:
    _ensure_app()
    page = DataManagementPage()
    tabs = page._tabs
    assert tabs.count() == 6
    assert tabs.tabText(tabs.count() - 2) == "SPC心智圖"
    assert tabs.tabText(tabs.count() - 1) == "圖表功能參考"


def test_chart_reference_row_count_matches_chart_order() -> None:
    _ensure_app()
    page = DataManagementPage()
    tabs = page._tabs
    chart_ref_table = tabs.widget(tabs.count() - 1)
    assert isinstance(chart_ref_table, QTableWidget)
    assert chart_ref_table.rowCount() == len(CHART_ORDER)


def test_master_table_uses_compact_columns() -> None:
    _ensure_app()
    page = DataManagementPage()
    table = page._tables["dfm"]
    assert table.columnCount() == 4
    headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
    assert headers == ["主題", "失效模式", "風險", "狀態"]


def test_master_selection_updates_detail_panel() -> None:
    _ensure_app()
    page = DataManagementPage()
    table = page._tables["dfm"]
    detail_map = page._detail_views[table]

    assert table.rowCount() > 1
    table.selectRow(1)
    QApplication.processEvents()

    topic_item = table.item(1, 0)
    entry = topic_item.data(Qt.ItemDataRole.UserRole)
    assert isinstance(entry, dict)
    assert str(entry["topic"]) in detail_map["topic"].text()
    assert str(entry["review_status"]) in detail_map["status"].text()
