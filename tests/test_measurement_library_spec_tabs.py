from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.measurement_library_page import (
    _COMBINED_SPEC_COL_NAMES,
    _COMBINED_SPEC_GROUPS,
    MeasurementLibraryPage,
)


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_measurement_library_has_combined_spec_tab() -> None:
    _ensure_app()
    page = MeasurementLibraryPage()
    try:
        texts = [page.tabs.tabText(i) for i in range(page.tabs.count())]
        assert "規格管理" in texts
        # The two old separate tabs must no longer exist.
        assert "錫膏印刷規格管理" not in texts
        assert "鋼板厚度規格管理" not in texts
    finally:
        page.close()


def test_combined_spec_table_has_grouped_columns() -> None:
    _ensure_app()
    page = MeasurementLibraryPage()
    try:
        # All 12 columns from the combined header are present, in order.
        assert page._sp_table.columnCount() == len(_COMBINED_SPEC_COL_NAMES)
        for col, expected in enumerate(_COMBINED_SPEC_COL_NAMES):
            header_item = page._sp_table.horizontalHeaderItem(col)
            assert header_item is not None
            assert header_item.text() == expected

        # Group bands cover every column without gaps or overlaps.
        covered: list[int] = []
        for _label, first, last in _COMBINED_SPEC_GROUPS:
            covered.extend(range(first, last + 1))
        assert covered == list(range(len(_COMBINED_SPEC_COL_NAMES)))
    finally:
        page.close()
