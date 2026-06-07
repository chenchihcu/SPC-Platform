import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication

from app.ui.dialogs.interpretation_dialog import InterpretationDialog
from app.ui.dialogs.pptx_export_confirm_dialog import PptxExportConfirmDialog
from app.ui.pages.measurement_library_page import (
    _EditCombinedSpecDialog,
    _EditCoordinateDialog,
    _EditSessionDialog,
    _EditSupplierDialog,
)
from app.ui.theme import apply_dark_theme, layout_policy


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        apply_dark_theme(app)
    return app


def _sample_joined_spec() -> dict:
    return {
        "product_name": "DEMO",
        "product_part_no": "PN-1",
        "paste": {
            "product_name": "DEMO",
            "product_part_no": "PN-1",
            "default_volume_lsl": 70,
            "default_volume_target": 100,
            "default_volume_usl": 130,
            "default_area_lsl": 70,
            "default_area_target": 100,
            "default_area_usl": 130,
            "default_height_lsl": 80,
            "default_height_usl": 120,
        },
        "stencil": {
            "product_name": "DEMO",
            "product_part_no": "PN-1",
            "stencil_type": "normal",
            "thickness_main": 0.12,
            "precision_is_main": True,
            "unit_mode": "percent",
            "height_denominator_mm": 0.12,
        },
    }


def test_representative_dialogs_fit_available_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _ensure_app()
    monkeypatch.setattr(
        layout_policy,
        "available_geometry_for",
        lambda _widget: QRect(0, 0, 1280, 752),
    )

    dialogs = [
        InterpretationDialog(),
        PptxExportConfirmDialog(None, chart_ids=["xbar_r", "cpk"], using_fallback=False),
        _EditSessionDialog(
            {
                "id": 1,
                "product_name": "DEMO",
                "supplier_work_order_no": "SUP-1",
                "outsource_work_order_no": "MED-1",
                "product_part_no": "PN-1",
                "notes": "",
                "file_path": "C:/tmp/long/path/demo.csv",
            }
        ),
        _EditCoordinateDialog(
            {
                "product_name": "DEMO",
                "product_part_no": "PN-1",
                "file_path": "C:/tmp/long/path/coords.csv",
            }
        ),
        _EditCombinedSpecDialog(_sample_joined_spec()),
        _EditSupplierDialog(
            {
                "supplier_code": "SUP001",
                "supplier_name": "供應商",
                "steel_plate_no": "ST-1",
                "steel_plate_production_date": "2026-05-26",
            }
        ),
    ]

    for dialog in dialogs:
        dialog.show()
        app.processEvents()
        assert dialog.width() <= 1248
        assert dialog.height() <= 720
        assert dialog.frameGeometry().left() >= 16
        assert dialog.frameGeometry().top() >= 16
        dialog.close()
