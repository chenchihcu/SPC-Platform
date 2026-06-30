from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import app.ui.pages.measurement_library_page as measurement_library_page
from app.ui.pages.measurement_library_page import (
    _COMBINED_SPEC_COL_NAMES,
    _COMBINED_SPEC_GROUPS,
    _EditCombinedSpecDialog,
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


def test_combined_spec_tab_has_add_spec_button() -> None:
    _ensure_app()
    page = MeasurementLibraryPage()
    try:
        assert page._sp_add_btn.text() == "新增規格"
        assert page._sp_add_btn.property("class") == "secondary"
        assert page._sp_load_btn.property("class") == "primary"
        assert page._sp_delete_btn.property("class") == "danger"
    finally:
        page.close()


def test_add_combined_spec_dialog_starts_from_registry_defaults() -> None:
    _ensure_app()
    dialog = _EditCombinedSpecDialog(is_new=True)
    try:
        assert dialog.windowTitle() == "新增產品規格"
        dialog.product_name_edit.setText("X3000")
        dialog.part_no_edit.setText("301-000100124")

        values = dialog.get_values()

        assert values["paste"]["product_name"] == "X3000"
        assert values["paste"]["product_part_no"] == "301-000100124"
        assert values["paste"]["default_volume_target"] == 100.0
        assert values["paste"]["default_volume_lsl"] == 70.0
        assert values["paste"]["default_volume_usl"] == 150.0
        assert values["paste"]["default_area_target"] == 100.0
        assert values["paste"]["default_area_lsl"] == 70.0
        assert values["paste"]["default_area_usl"] == 150.0
        assert values["paste"]["default_height_lsl"] == 70.0
        assert values["paste"]["default_height_usl"] == 140.0
        assert values["stencil"]["thickness_main"] == 0.12
        assert values["stencil"]["thickness_precision"] == 0.08
        assert values["stencil"]["unit_mode"] == "percent"
        assert values["stencil"]["height_denominator_mm"] == 0.12
    finally:
        dialog.close()


def test_spec_product_filter_names_include_spec_only_products(monkeypatch) -> None:
    monkeypatch.setattr(
        measurement_library_page,
        "list_paste_spec_products",
        lambda: ["SpecOnly", "Both"],
    )
    monkeypatch.setattr(
        measurement_library_page,
        "list_stencil_spec_products",
        lambda: ["SpecOnly", "StencilOnly"],
    )

    names = MeasurementLibraryPage._list_spec_product_names(["CoordOnly", "Both"])

    assert names == ["Both", "CoordOnly", "SpecOnly", "StencilOnly"]
