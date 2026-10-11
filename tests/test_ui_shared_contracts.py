from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractItemView, QFrame, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem

from app.ui.pages.coordinate_manager_page import CoordinateManagerPage
from app.ui.pages.reference_page import ReferencePage
from app.ui.pages.data_setup_page import DataSetupPage
from app.ui.pages.data_upload_page import DataUploadPage
from app.ui.pages.diagnostic_page import DiagnosticPage
from app.ui.pages.measurement_library_page import MeasurementLibraryPage, _COL_NAMES
from app.ui.theme import apply_dark_theme
from app.ui.theme.dark_stylesheet import get_app_stylesheet
from app.ui.theme.tokens import SECONDARY_TAB_COMPACT_MIN_WIDTH
from app.ui.widgets.page_templates import (
    bind_table_delete_shortcut,
    confirm_action,
    confirm_double_delete,
    create_status_lamp,
    empty_state_label,
    set_drop_zone_active,
    set_status,
    style_table,
)
from app.ui.workflow_labels import VISIBLE_WORKFLOW_TABS, WORKFLOW_LABEL_CHARTS, WORKFLOW_LABEL_STATISTICS_DATA


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        apply_dark_theme(app)
    return app


def test_shared_drop_zone_active_state_contract() -> None:
    _ensure_app()
    frame = QFrame()
    frame.setProperty("class", "dropZone")

    set_drop_zone_active(frame, True)
    assert frame.property("state") == "active"

    set_drop_zone_active(frame, False)
    assert frame.property("state") == ""
    frame.close()


def test_set_status_normalizes_alias_and_syncs_label() -> None:
    _ensure_app()
    lamp = create_status_lamp()
    label = QLabel("舊文字")

    assert set_status(lamp, label, "ok", "已匯出") == "success"
    assert lamp.property("state") == "success"
    assert label.property("state") == "success"
    assert label.text() == "已匯出"
    assert "狀態：已就緒" in label.accessibleDescription()

    # text=None keeps the current label text; label=None updates only the lamp.
    set_status(lamp, label, "warning")
    assert label.text() == "已匯出"
    assert label.property("state") == "warning"
    set_status(lamp, None, "loading")
    assert lamp.property("state") == "loading"


_PENDING_DIALOG_ANSWERS: list[object] = []


def _answer_next_confirm(button_text: str) -> None:
    """Click button_text on the next visible QMessageBox (polls until shown)."""

    def _click() -> None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMessageBox) and widget.isVisible():
                for btn in widget.buttons():
                    if btn.text() == button_text:
                        btn.click()
                        return
        QTimer.singleShot(10, _click)

    # Keep the closure alive until the dialog is answered.
    _PENDING_DIALOG_ANSWERS.append(_click)
    QTimer.singleShot(0, _click)


def test_confirm_action_uses_localized_buttons_and_cancel_default() -> None:
    _ensure_app()
    seen: dict[str, object] = {}

    def _inspect_then_cancel() -> None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMessageBox) and widget.isVisible():
                seen["buttons"] = sorted(b.text() for b in widget.buttons())
                default = widget.defaultButton()
                seen["default"] = default.text() if default is not None else None
                widget.reject()
                return
        QTimer.singleShot(10, _inspect_then_cancel)

    QTimer.singleShot(0, _inspect_then_cancel)
    assert confirm_action(None, "確認", "測試") is False
    assert seen["buttons"] == sorted(["確認", "取消"])
    assert seen["default"] == "取消"

    _answer_next_confirm("確認")
    assert confirm_action(None, "確認", "測試") is True


def test_confirm_double_delete_requires_both_confirmations() -> None:
    _ensure_app()
    _answer_next_confirm("取消")
    assert confirm_double_delete(None, "刪除？") is False  # type: ignore[arg-type]

    _answer_next_confirm("確認")
    QTimer.singleShot(50, lambda: _answer_next_confirm("取消"))
    assert confirm_double_delete(None, "刪除？") is False  # type: ignore[arg-type]


def test_coordinate_and_measurement_drop_zones_use_active_state() -> None:
    _ensure_app()
    coord_page = CoordinateManagerPage()
    meas_page = DataUploadPage()

    coord_page._set_drop_zone_active(True)
    meas_page._set_drop_zone_active(True)

    assert coord_page.drop_zone.property("state") == "active"
    assert meas_page.drop_zone.property("state") == "active"

    coord_page._set_drop_zone_active(False)
    meas_page._set_drop_zone_active(False)

    assert coord_page.drop_zone.property("state") == ""
    assert meas_page.drop_zone.property("state") == ""
    coord_page.close()
    meas_page.close()


def test_measurement_library_status_states_update_accessibility() -> None:
    _ensure_app()
    page = MeasurementLibraryPage()

    page._set_status_state("loading", "解析中...")
    assert page.status_lamp.property("state") == "loading"
    assert page.status_text.property("state") == "loading"
    assert page.status_text.accessibleName() == "解析中..."
    assert "狀態：處理中" in page.status_text.accessibleDescription()

    page._set_status_state("success", "2 筆記錄")
    assert page.status_lamp.property("state") == "success"
    assert page.status_text.property("state") == "success"
    assert "狀態：已就緒" in page.status_text.accessibleDescription()

    page._set_status_state("idle", "尚無記錄")
    assert page.status_lamp.property("state") == "idle"
    assert page.status_text.property("state") == "idle"
    assert "狀態：未載入" in page.status_text.accessibleDescription()
    page.close()


def test_measurement_library_uses_compact_table_toolbars() -> None:
    _ensure_app()
    page = MeasurementLibraryPage()
    table_toolbars = [
        frame
        for frame in page.findChildren(QFrame)
        if frame.property("class") == "tableToolbar"
    ]

    assert len(table_toolbars) == page.tabs.count()
    assert page._count_lbl.parentWidget() is page.tabs.widget(0)
    assert page.status_lamp.parentWidget() is page.tabs.widget(0)
    page.close()


def test_measurement_library_table_includes_supplier_context_column() -> None:
    _ensure_app()
    page = MeasurementLibraryPage()

    assert "供應商" in _COL_NAMES
    assert page._table.columnCount() == len(_COL_NAMES)
    assert page._table.horizontalHeaderItem(_COL_NAMES.index("供應商")).text() == "供應商"
    page.close()


def test_measurement_library_context_preserves_supplier_name() -> None:
    _ensure_app()
    page = MeasurementLibraryPage()

    context = page._build_measurement_context(
        {
            "id": 7,
            "product_name": "DemoProduct",
            "supplier": "振順豐",
            "product_part_no": "PART-001",
            "supplier_work_order_no": "SUP-100",
            "outsource_work_order_no": "OUT-200",
            "batch_no": "",
        }
    )

    assert context["supplier"] == "振順豐"
    assert context["supplier_work_order_no"] == "SUP-100"
    assert context["outsource_work_order_no"] == "OUT-200"
    assert context["batch_no"] == "OUT-200"
    page.close()


def test_workflow_chart_label_is_single_source_for_visible_text() -> None:
    labels = [label for label, _stack_index in VISIBLE_WORKFLOW_TABS]
    source = Path("app/ui/pages/measurement_library_page.py").read_text(encoding="utf-8")

    assert WORKFLOW_LABEL_CHARTS == "統計圖表"
    assert WORKFLOW_LABEL_STATISTICS_DATA == "統計資料"
    assert "統計圖表" in labels
    assert "統計資料" in labels
    assert "管制圖表" not in labels
    assert "管制圖表" not in source
    assert "WORKFLOW_LABEL_CHARTS" in source


def test_header_roles_are_explicit_for_workflow_and_utility_headers() -> None:
    _ensure_app()
    setup_page = DataSetupPage()
    library_page = MeasurementLibraryPage()
    reference_page = ReferencePage()

    assert setup_page._header_card.property("headerRole") == "workflowHeader"
    assert setup_page._footer_card.property("headerRole") == "utilityHeader"
    assert setup_page._header_card.property("headerDensity") == "compact"
    assert setup_page._footer_card.property("headerDensity") == "compact"
    assert library_page.header_lbl.parentWidget().property("headerRole") == "utilityHeader"
    assert library_page.header_lbl.parentWidget().property("headerDensity") == "compact"
    assert library_page.status_lamp.parentWidget() is not library_page.header_lbl.parentWidget()
    assert reference_page.header_lbl.parentWidget().property("headerRole") == "utilityHeader"
    assert reference_page.header_lbl.parentWidget().property("headerDensity") == "compact"
    setup_page.close()
    library_page.close()
    reference_page.close()


def test_secondary_tab_contract_is_shared_by_library_reference_and_diagnostic() -> None:
    _ensure_app()
    library_page = MeasurementLibraryPage()
    reference_page = ReferencePage()
    diagnostic_page = DiagnosticPage()
    stylesheet = get_app_stylesheet()

    assert library_page.tabs.property("class") == "secondaryTabs"
    assert reference_page._tabs.property("class") == "secondaryTabs"
    assert diagnostic_page._matrix_tabs.property("class") == "secondaryTabs processMatrixTabs"
    assert 'QTabWidget[class~="secondaryTabs"] QTabBar::tab:selected' in stylesheet
    assert 'QTabWidget[class~="secondaryTabs"] QTabBar::tab:hover:!selected' in stylesheet
    assert 'QTabWidget[class~="secondaryTabs"] QTabBar::tab:disabled' in stylesheet
    assert f"min-width: {SECONDARY_TAB_COMPACT_MIN_WIDTH}px" in stylesheet
    library_page.close()
    reference_page.close()
    diagnostic_page.close()


def test_empty_state_helper_suppresses_presentation_emoji() -> None:
    _ensure_app()
    chart_hint = empty_state_label("請選擇圖表", icon="📊")
    feature_hint = empty_state_label("請先上傳量測資料", icon="📋")

    assert chart_hint.text() == "請選擇圖表"
    assert feature_hint.text() == "請先上傳量測資料"
    assert "📊" not in chart_hint.text()
    assert "📋" not in feature_hint.text()
    chart_hint.close()
    feature_hint.close()


def test_style_table_roles_control_shared_table_behavior() -> None:
    _ensure_app()
    default_table = QTableWidget(0, 2)
    reference_table = QTableWidget(0, 2)
    diagnostic_table = QTableWidget(0, 2)

    style_table(default_table)
    style_table(reference_table, role="reference")
    style_table(diagnostic_table, role="diagnostic")

    assert default_table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert default_table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows
    assert default_table.wordWrap() is False
    assert reference_table.wordWrap() is True
    assert (
        reference_table.horizontalHeader().defaultAlignment()
        == Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
    )
    assert diagnostic_table.wordWrap() is True
    assert diagnostic_table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert diagnostic_table.horizontalHeader().stretchLastSection() is False
    default_table.close()
    reference_table.close()
    diagnostic_table.close()


def test_table_delete_shortcut_requires_selection_and_stays_table_scoped() -> None:
    _ensure_app()
    table = QTableWidget(1, 1)
    table.setItem(0, 0, QTableWidgetItem("row"))
    delete_button = QPushButton("刪除")
    invocations: list[bool] = []
    delete_button.clicked.connect(lambda: invocations.append(True))
    shortcut = bind_table_delete_shortcut(table, delete_button)
    try:
        assert not delete_button.isEnabled()
        assert shortcut.context() == Qt.ShortcutContext.WidgetWithChildrenShortcut
        assert shortcut.key().matches(QKeySequence("Delete")) == QKeySequence.SequenceMatch.ExactMatch
        shortcut.activated.emit()
        assert invocations == []
        table.selectRow(0)
        table.show()
        table.activateWindow()
        table.setFocus()
        QTest.qWait(20)
        QTest.keyClick(table, Qt.Key.Key_Delete)
        assert invocations == [True]
        assert "兩次確認" in delete_button.toolTip()
    finally:
        table.close()
        delete_button.close()


def test_measurement_library_delete_actions_share_table_scoped_shortcuts() -> None:
    _ensure_app()
    page = MeasurementLibraryPage()
    try:
        pairs = (
            (page._table, page._delete_btn),
            (page._c_table, page._c_delete_btn),
            (page._sp_table, page._sp_delete_btn),
            (page._sup_table, page._sup_delete_btn),
        )
        for table, delete_button in pairs:
            shortcuts = table.findChildren(QShortcut)
            assert not delete_button.isEnabled()
            assert any(shortcut.objectName() == "tableDeleteShortcut" for shortcut in shortcuts)
            assert "Delete" in delete_button.toolTip()
    finally:
        page.close()
