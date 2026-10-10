"""CsvFileSelectorPane: shared coord/meas CSV selector contract."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.coordinate_manager_page import CoordinateManagerPage
from app.ui.pages.data_upload_page import DataUploadPage
from app.ui.theme.tokens import EMPTY_CSV_PATH_TEXT
from app.ui.widgets.csv_file_selector_pane import CsvFileSelectorPane


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    return app


@pytest.mark.parametrize("embedded", [True, False])
def test_both_pages_share_empty_path_text_and_pane_widgets(embedded: bool) -> None:
    _ensure_app()
    for page in (CoordinateManagerPage(embedded=embedded), DataUploadPage(embedded=embedded)):
        assert isinstance(page.file_pane, CsvFileSelectorPane)
        assert page.btn_browse is page.file_pane.btn_browse
        assert page.lbl_path is page.file_pane.lbl_path
        assert page.lbl_meta is page.file_pane.lbl_meta
        assert page.drop_zone is page.file_pane.drop_zone
        assert page.lbl_path.text() == EMPTY_CSV_PATH_TEXT

        page.set_path_text("目前載入檔：C:/tmp/a.csv")
        page.set_metadata("a.csv", 12, "2026-10-10 08:00:00")
        assert page.lbl_path.text().endswith("a.csv")
        assert page.lbl_meta.text() == "列數：12"
        assert page.file_pane.drop_zone_hint.toolTip() == "已載入：a.csv"

        page.reset_upload_state()
        assert page.lbl_path.text() == EMPTY_CSV_PATH_TEXT
        assert page.lbl_meta.text() == "列數：--"
        assert page.file_pane.drop_zone_hint.toolTip() == ""
        page.close()


def test_pane_selection_routes_to_page_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_app()
    meas = DataUploadPage(embedded=True)
    got: list[str] = []
    meas.meas_uploaded.connect(got.append)
    meas.file_pane._on_csv_dropped("C:/tmp/meas.csv")
    assert got == ["C:/tmp/meas.csv"]
    assert meas.file_pane.drop_zone_hint.toolTip() == "已載入：meas.csv"
    meas.close()

    started: list[str] = []
    monkeypatch.setattr(
        CoordinateManagerPage, "_start_validation", lambda self, fp: started.append(fp)
    )
    coord = CoordinateManagerPage(embedded=True)
    coord.file_pane._on_csv_dropped("C:/tmp/coord.csv")
    assert started == ["C:/tmp/coord.csv"]
    coord.close()
