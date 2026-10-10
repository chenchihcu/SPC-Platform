from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication
from shapely.geometry import box

from app.data import master_data_db
from app.data.coordinate_registry import register
from app.data.stencil_document_library import create_stencil_document_version
from app.services.stencil_document_service import PARSER_VERSION
from app.services.stencil_aperture_loader import ApertureLoadResult
from app.services.stencil_document_service import ImportAnalysis
from app.ui.dialogs import stencil_document_import_dialog as import_dialog_module
from app.ui.dialogs.stencil_document_import_dialog import StencilDocumentImportDialog
from app.ui.pages.measurement_library_page import MeasurementLibraryPage
from app.ui.widgets.stencil_document_manager import StencilDocumentManager
from app.ui.widgets.stencil_spec_editor import StencilSpecEditor


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


@pytest.fixture()
def isolated_master_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "spc_master.db"
    monkeypatch.setenv("SPC_MASTER_DB_PATH", str(db_file))
    master_data_db._INITIALIZED = False
    master_data_db.init_db()
    yield db_file
    master_data_db._INITIALIZED = False


def _active_version(tmp_path: Path) -> None:
    coordinate = tmp_path / "coord.csv"
    coordinate.write_text("RefDes,Pad,X,Y\nU1,01,0,0\n", encoding="utf-8")
    assert register("P1", str(coordinate), "PN-1", 1)
    gerber = tmp_path / "paste.gtp"
    gerber.write_text(
        "G04 test*\n%FSLAX46Y46*%\n%MOMM*%\n%ADD10R,0.600000X0.300000*%\n"
        "D10*\nX0000000000Y0000000000D03*\nM02*\n",
        encoding="ascii",
    )
    pads = tmp_path / "pads.csv"
    pads.write_text(
        "RefDes,Pad,X,Y,Width,Height,Rotation,Side\nU1,01,0,0,0.6,0.3,0,TOP\n",
        encoding="utf-8",
    )
    create_stencil_document_version(
        product_name="P1",
        stencil_no="ST-001",
        revision="A",
        side="TOP",
        gerber_source=str(gerber),
        pad_csv_source=str(pads),
        coordinate_transform={"rotation_deg": 0, "mirrored": False, "scale": 1.0},
        validation_summary={
            "total_pads": 1,
            "matched_pads": 1,
            "coverage": 1.0,
            "duplicate_pad_rows": 0,
            "ambiguous_openings": 0,
            "unclassified_extra_openings": 0,
            "missing_thickness_pads": 0,
            "requires_user_overlay_confirmation": True,
            "overlay_confirmed": True,
        },
        parser_version=PARSER_VERSION,
        nominals=[
            {
                "refdes": "U1",
                "pad": "01",
                "side": "TOP",
                "opening_count": 1,
                "nominal_area_mm2": 0.18,
                "resolved_thickness_mm": 0.06,
                "nominal_volume_mm3": 0.0108,
                "match_status": "MATCHED",
                "preview_geometry": {},
            }
        ],
        activate=True,
    )


def test_import_dialog_exposes_four_functional_steps(isolated_master_db: Path) -> None:
    _app()
    dialog = StencilDocumentImportDialog("P1")
    try:
        assert dialog.pages.count() == 4
        assert "步驟 1/4" in dialog.step_label.text()
        assert dialog.aperture_edit.accessibleName() == "鋼板開窗幾何文件"
        assert dialog.aperture_unit_combo.accessibleName() == "DXF 開窗單位"
        assert [
            dialog.aperture_unit_combo.itemText(index)
            for index in range(dialog.aperture_unit_combo.count())
        ] == ["依 $INSUNITS", "mm", "inch"]
        dialog._set_status(dialog.mapping_status, "ERROR：fixture", "error")
        assert dialog.mapping_status.property("state") == "error"
        dialog.pages.setCurrentIndex(3)
        assert dialog.next_button.text() == "儲存版本"
        assert dialog.activate_checkbox.text().startswith("儲存後立即")
    finally:
        dialog.close()


def test_import_dialog_file_picker_includes_legacy_pho(
    isolated_master_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    captured: dict[str, str] = {}

    def fake_get_open_file_name(
        _parent: object, title: str, _directory: str, file_filter: str
    ) -> tuple[str, str]:
        captured.update(title=title, file_filter=file_filter)
        return "", ""

    monkeypatch.setattr(
        import_dialog_module.QFileDialog,
        "getOpenFileName",
        fake_get_open_file_name,
    )
    dialog = StencilDocumentImportDialog("P1")
    try:
        dialog._browse_aperture()
        assert captured["title"] == "選擇鋼板開窗幾何文件"
        assert "*.pho" in captured["file_filter"]
        assert "Legacy PHO" in captured["file_filter"]
    finally:
        dialog.close()


def test_import_dialog_clears_manual_exclusions_when_source_mapping_changes(
    isolated_master_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    opening = box(-0.3, -0.15, 0.3, 0.15)
    loader_result = ApertureLoadResult(
        openings=[opening],
        format_id="dxf",
        format_label="DXF R2013",
        source_layer="Paste_Top",
    )
    analysis = ImportAnalysis(
        transform={},
        validation_summary={
            "total_pads": 0,
            "matched_pads": 0,
            "coverage": 0.0,
            "duplicate_pad_rows": 0,
            "ambiguous_openings": 0,
            "ambiguous_opening_indexes": [],
            "unclassified_extra_openings": 0,
            "extra_opening_indexes": [],
            "unmatched_pads": [],
            "non_component_openings": [],
            "missing_thickness_pads": 0,
        },
        nominals=[],
        transformed_openings=[opening],
    )
    monkeypatch.setattr(
        import_dialog_module,
        "load_aperture_source",
        lambda *_args, **_kwargs: loader_result,
    )
    monkeypatch.setattr(
        import_dialog_module,
        "analyze_stencil_import",
        lambda **_kwargs: analysis,
    )
    dialog = StencilDocumentImportDialog("P1")
    try:
        dialog.aperture_edit.setText("source.dxf")
        dialog.csv_edit.setText("pads.csv")
        dialog._match_cache_key = ("source.dxf", "TOP", "", "pads.csv", "mm")
        dialog._non_component_indexes.add(7)
        dialog.unit_combo.setCurrentIndex(1)

        assert dialog._parse_and_match()
        assert dialog._non_component_indexes == set()
    finally:
        dialog.close()


def test_data_setup_editor_shows_top_bottom_document_state(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    _app()
    _active_version(tmp_path)
    editor = StencilSpecEditor(embedded=True)
    try:
        editor.set_selected_product("P1")
        assert "Top Rev A 100.0% (1/1)" in editor.document_status_lbl.text()
        assert "Bottom 未啟用" in editor.document_status_lbl.text()
        assert editor.btn_import_document.text() == "載入開窗文件"
        assert editor.btn_manage_documents.text() == "管理文件"
    finally:
        editor.close()


def test_measurement_library_preserves_main_tab_and_adds_document_subtab(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    _app()
    _active_version(tmp_path)
    page = MeasurementLibraryPage()
    try:
        assert page.tabs.tabText(2) == "規格管理"
        assert [page._spec_subtabs.tabText(i) for i in range(page._spec_subtabs.count())] == [
            "參數規格",
            "開窗文件",
        ]
        page.open_stencil_documents("P1")
        assert page.tabs.currentIndex() == 2
        assert page._spec_subtabs.currentIndex() == 1
        assert page.stencil_document_manager.table.rowCount() == 1
        assert "SUCCESS" in page.stencil_document_manager.status_label.text()
    finally:
        page.close()


def test_document_manager_requires_an_import_product_without_filtering_rows(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    _app()
    _active_version(tmp_path)
    manager = StencilDocumentManager()
    try:
        assert manager.table.rowCount() == 1
        assert not manager.import_button.isEnabled()
        manager.set_product_name("P1")
        assert manager.import_button.isEnabled()
        assert manager.table.rowCount() == 1
        assert "不會改變下方清單" in manager.product_combo.toolTip()
    finally:
        manager.close()


def test_document_manager_supports_multi_selection_and_safe_delete_shortcut(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    _app()
    _active_version(tmp_path)
    manager = StencilDocumentManager()
    try:
        manager.table.selectRow(0)
        assert manager._selected_version_ids()
        assert manager.table.selectionMode().name == "ExtendedSelection"
        assert not manager.delete_button.isEnabled()
        assert any(
            shortcut.key().matches(QKeySequence("Delete")) == QKeySequence.SequenceMatch.ExactMatch
            for shortcut in manager.table.findChildren(QShortcut)
        )
        assert "兩次確認" in manager.delete_button.toolTip()
    finally:
        manager.close()
