"""Capture native Qt evidence for stencil document UI at the current DPI scale."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _fixture_files(root: Path) -> tuple[Path, Path, Path]:
    coordinate = root / "coord.csv"
    coordinate.write_text("RefDes,Pad,X,Y\nU1,01,0,0\n", encoding="utf-8")
    gerber = root / "paste.gtp"
    gerber.write_text(
        "G04 visual fixture*\n%FSLAX46Y46*%\n%MOMM*%\n"
        "%ADD10R,0.600000X0.300000*%\nD10*\nX0000000000Y0000000000D03*\nM02*\n",
        encoding="ascii",
    )
    pads = root / "pads.csv"
    pads.write_text(
        "RefDes,Pad,X,Y,Width,Height,Rotation,Side\nU1,01,0,0,0.6,0.3,0,TOP\n",
        encoding="utf-8",
    )
    return coordinate, gerber, pads


def _seed(root: Path, coordinate: Path, gerber: Path, pads: Path) -> None:
    from app.data import master_data_db
    from app.data.coordinate_registry import register
    from app.data.product_spec_registry import save as save_product_spec
    from app.data.stencil_document_library import create_stencil_document_version
    from app.services.stencil_document_service import PARSER_VERSION

    os.environ["SPC_MASTER_DB_PATH"] = str(root / "visual.db")
    master_data_db._INITIALIZED = False
    master_data_db.init_db()
    register("VS80-UI", str(coordinate), "301-UI", 1)
    save_product_spec(
        {
            "product_name": "VS80-UI",
            "stencil_type": "normal",
            "thickness_main": 0.06,
            "precision_is_main": False,
            "default_volume_target": 100.0,
            "default_volume_lsl": 70.0,
            "default_volume_usl": 150.0,
            "default_area_target": 100.0,
            "default_area_lsl": 70.0,
            "default_area_usl": 150.0,
            "default_height_target": 100.0,
            "default_height_lsl": 70.0,
            "default_height_usl": 140.0,
        }
    )
    create_stencil_document_version(
        product_name="VS80-UI",
        stencil_no="ST-UI-001",
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


def _capture(
    app,
    widget,
    output: Path,
    prepare: Callable[[], None] | None = None,
) -> None:
    from PySide6.QtTest import QTest

    widget.show()
    app.processEvents()
    QTest.qWait(120)
    if prepare is not None:
        prepare()
        app.processEvents()
        QTest.qWait(80)
    widget.repaint()
    app.processEvents()
    QTest.qWait(40)
    window = widget.windowHandle()
    screen = window.screen() if window is not None else app.primaryScreen()
    if screen is not None:
        from PySide6.QtCore import QPoint

        origin = widget.mapToGlobal(QPoint(0, 0))
        pixmap = screen.grabWindow(
            0,
            origin.x(),
            origin.y(),
            widget.width(),
            widget.height(),
        )
    else:
        pixmap = widget.grab()
    if pixmap.isNull():
        pixmap = widget.grab()
    if pixmap.isNull() or not pixmap.save(str(output), "PNG"):
        raise RuntimeError(f"failed to capture {output}")
    widget.close()
    app.processEvents()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="spc-stencil-ui-") as temp_name:
        fixture_root = Path(temp_name)
        coordinate, gerber, pads = _fixture_files(fixture_root)
        _seed(fixture_root, coordinate, gerber, pads)

        from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout

        from app.ui.dialogs.stencil_document_import_dialog import (
            StencilDocumentImportDialog,
        )
        from app.ui.pages.data_setup_page import DataSetupPage
        from app.ui.theme import apply_app_theme
        from app.ui.widgets.stencil_document_manager import StencilDocumentManager

        app = QApplication.instance() or QApplication([])
        apply_app_theme(app)

        data_setup = DataSetupPage()
        data_setup.resize(1200, 700)
        data_setup.sync_from_store({"product_name": "VS80-UI"})
        _capture(app, data_setup, output / "data_setup.png")

        data_setup_stencil = DataSetupPage()
        data_setup_stencil.resize(1200, 700)
        data_setup_stencil.sync_from_store({"product_name": "VS80-UI"})
        _capture(
            app,
            data_setup_stencil,
            output / "data_setup_stencil.png",
            prepare=lambda: data_setup_stencil.scroll_area.ensureWidgetVisible(
                data_setup_stencil._spec_region, 0, 20
            ),
        )

        source_wizard = StencilDocumentImportDialog("VS80-UI")
        source_wizard.revision_edit.setText("B")
        source_wizard.stencil_no_edit.setText("ST-UI-001")
        source_wizard.aperture_edit.setText(str(gerber))
        source_wizard.csv_edit.setText(str(pads))
        _capture(app, source_wizard, output / "import_source.png")

        mapping_wizard = StencilDocumentImportDialog("VS80-UI")
        mapping_wizard.revision_edit.setText("B")
        mapping_wizard.stencil_no_edit.setText("ST-UI-001")
        mapping_wizard.aperture_edit.setText(str(gerber))
        mapping_wizard.csv_edit.setText(str(pads))

        def prepare_mapping() -> None:
            mapping_wizard.pages.setCurrentIndex(1)
            app.processEvents()
            if not mapping_wizard._load_csv_preview():
                raise RuntimeError("failed to prepare wizard mapping fixture")

        _capture(
            app,
            mapping_wizard,
            output / "import_mapping.png",
            prepare=prepare_mapping,
        )

        wizard = StencilDocumentImportDialog("VS80-UI")
        wizard.revision_edit.setText("B")
        wizard.stencil_no_edit.setText("ST-UI-001")
        wizard.aperture_edit.setText(str(gerber))
        wizard.csv_edit.setText(str(pads))

        def prepare_overlay() -> None:
            wizard.pages.setCurrentIndex(1)
            app.processEvents()
            if not wizard._load_csv_preview() or not wizard._parse_and_match():
                raise RuntimeError("failed to prepare wizard overlay fixture")
            wizard.overlay_confirm.setChecked(True)
            wizard.pages.setCurrentIndex(2)

        _capture(
            app,
            wizard,
            output / "import_overlay.png",
            prepare=prepare_overlay,
        )

        error_wizard = StencilDocumentImportDialog("VS80-UI")

        def prepare_error() -> None:
            error_wizard.pages.setCurrentIndex(1)
            app.processEvents()
            error_wizard._set_status(
                error_wizard.mapping_status,
                "ERROR：Pad CSV 缺少欄位 Rotation；請修正後重新驗證，資料未載入。",
                "error",
            )

        _capture(
            app,
            error_wizard,
            output / "import_error.png",
            prepare=prepare_error,
        )

        manager_dialog = QDialog()
        manager_dialog.setWindowTitle("規格管理｜開窗文件")
        manager_layout = QVBoxLayout(manager_dialog)
        manager = StencilDocumentManager()
        manager.set_product_name("VS80-UI")
        manager_layout.addWidget(manager)
        manager_dialog.resize(1100, 620)
        _capture(app, manager_dialog, output / "version_manager.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
