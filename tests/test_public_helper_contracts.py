from __future__ import annotations

import os

import pandas as pd

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from app.data.models import RelationReport, WorkorderRecord
from app.ui.widgets.page_templates import (
    apply_button_icon,
    create_form_grid,
    create_page_shell,
    create_section_card,
    create_status_badge,
    create_summary_card,
    set_button_role,
)
from app.ui.workflow_labels import WORKFLOW_LABEL_CHARTS, workflow_label_for_stack
from app.utils.dataframe_utils import safe_columns
from app.utils.enums import SampleMode


def _qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication([])


def test_shared_page_template_helpers_are_public_contracts() -> None:
    _qapp()
    shell, shell_layout = create_page_shell("Demo")
    card, card_layout = create_section_card("Section", "Subtitle")
    grid = create_form_grid()
    button = QPushButton("Run")
    summary = create_summary_card("Rows", "12")
    badge = create_status_badge("Ready", "ok")

    set_button_role(button, "primary")
    apply_button_icon(button, "open")

    try:
        assert shell_layout.count() >= 1
        assert card.objectName() == "stepCard"
        assert card_layout.count() >= 2
        assert grid.horizontalSpacing() >= 0
        assert button.property("class") == "primary"
        assert summary.property("class") == "kpiCard"
        assert badge.property("state") == "ok"
    finally:
        for widget in (shell, card, button, summary, badge):
            widget.deleteLater()


def test_shared_lightweight_data_contract_helpers() -> None:
    report = RelationReport(
        matched_count=3,
        unmatched_count=1,
        match_rate=75.0,
        invalid_refdes=[],
        duplicate_refdes=["R1"],
    )
    workorder = WorkorderRecord(workorder_no="WO-1", line_name="L1")

    assert report.match_rate == 75.0
    assert workorder.workorder_no == "WO-1"
    assert SampleMode.FIRST.value == "首件"
    assert safe_columns(pd.DataFrame({1: [1], "BoardNo": ["B1"]})) == ["1", "BoardNo"]
    assert workflow_label_for_stack(2) == WORKFLOW_LABEL_CHARTS
