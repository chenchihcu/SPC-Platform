from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QCheckBox, QGridLayout
from PySide6.QtCore import QEvent

from app.ui.pages.chart_analysis_page import ChartAnalysisPage
from app.ui.state.app_status_model import AppStatusModel, STATE_ANALYZING, STATE_SUCCESS
from app.ui.widgets.status_bar import StatusBarWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_chart_page_header_title_and_top_right_status_are_removed(qapp: QApplication) -> None:
    page = ChartAnalysisPage()

    assert not hasattr(page, "_header_lbl")
    assert not hasattr(page, "lamp")
    assert not hasattr(page, "status_lbl")


def test_chart_page_toolbar_controls_are_on_single_row_in_order(qapp: QApplication) -> None:
    # Feature buttons (高度/面積/體積) moved to sidebar; toolbar now shows
    # only display-mode controls: step label, normalize, and tab buttons.
    page = ChartAnalysisPage()
    page.resize(1600, 900)
    page.show()
    qapp.processEvents()

    page._display_features = ["Height", "Area"]
    page._sync_normalize_visibility()
    qapp.processEvents()
    assert page.chk_normalize.isVisible()

    assert page._mode_step_label.text() == ChartAnalysisPage._MODE_STEP_TEXT
    assert page.chk_normalize.text() == ChartAnalysisPage._NORMALIZE_LABEL
    assert not hasattr(page, "_feature_step_label")
    assert not hasattr(page, "btn_feature_height")

    controls = [
        page._mode_step_label,
        page.chk_normalize,
        page._feature_tab_buttons[1],
        page._feature_tab_buttons[2],
        page._feature_tab_buttons[3],
    ]
    y_positions = [w.mapTo(page, w.rect().topLeft()).y() for w in controls]
    x_positions = [w.mapTo(page, w.rect().topLeft()).x() for w in controls]
    right_edges = [w.mapTo(page, w.rect().topRight()).x() for w in controls]
    adjacent_gaps = [
        x_positions[i + 1] - right_edges[i] - 1
        for i in range(len(controls) - 1)
    ]

    assert max(y_positions) - min(y_positions) <= 2
    assert x_positions == sorted(x_positions)
    # Guard against accidental middle stretch reintroduction.
    assert max(adjacent_gaps) <= page.width() // 8


def test_chart_page_uses_compact_selector_and_card_header(qapp: QApplication) -> None:
    page = ChartAnalysisPage()
    page.resize(1600, 900)
    page.show()
    qapp.processEvents()

    assert page.accordion_area.property("layoutDensity") == "compact"
    assert page.accordion_area.maximumHeight() > 0

    first_card = next(iter(page._dashboard_cards.values()))
    assert first_card.layout().contentsMargins().top() <= 4
    first_button = next(iter(page._card_interpret_buttons.values()))
    assert first_button.property("variant") == "chartCardAction"
    first_status = next(iter(page._card_status_labels.values()))
    assert first_status.property("class") == "chartCardStatus"
    assert any(not card.isHidden() for card in page._dashboard_cards.values())
    assert not page._empty_hint.isVisible()
    assert sum(widget is not None for widget in page._chart_widgets.values()) < len(page._chart_widgets)

    _header, content, content_layout = page._accordion_panels["製程監控"]
    assert isinstance(content_layout, QGridLayout)
    assert content_layout.itemAtPosition(0, 1) is not None
    options = [cb for cb in content.findChildren(QCheckBox) if cb.parentWidget() is content]
    assert len(options) >= 6
    assert max(option.geometry().bottom() for option in options) <= content.rect().bottom()


def test_chart_page_feature_tabs_use_dynamic_equal_min_width(qapp: QApplication) -> None:
    page = ChartAnalysisPage()
    page.resize(1600, 900)
    page.show()
    qapp.processEvents()

    buttons = [page._feature_tab_buttons[1], page._feature_tab_buttons[2], page._feature_tab_buttons[3]]
    min_widths = [btn.minimumWidth() for btn in buttons]

    assert all(width >= ChartAnalysisPage._FEATURE_TAB_BASE_MIN_WIDTH for width in min_widths)
    assert len(set(min_widths)) == 1
    # Dynamic sizing should avoid fixed-width lock (min=max=68).
    assert all(btn.maximumWidth() > ChartAnalysisPage._FEATURE_TAB_BASE_MIN_WIDTH for btn in buttons)


def test_chart_page_feature_tabs_recompute_can_expand_min_width(qapp: QApplication) -> None:
    page = ChartAnalysisPage()
    page.resize(1600, 900)
    page.show()
    qapp.processEvents()

    base_width = page._feature_tab_buttons[1].minimumWidth()
    page._feature_tab_buttons[1].setStyleSheet("font-size: 24pt; font-weight: 700;")
    page._recompute_feature_tab_button_widths()
    qapp.processEvents()

    expanded_width = page._feature_tab_buttons[1].minimumWidth()
    assert expanded_width > base_width
    assert all(
        btn.minimumWidth() == expanded_width
        for btn in (page._feature_tab_buttons[1], page._feature_tab_buttons[2], page._feature_tab_buttons[3])
    )


def test_chart_page_change_event_triggers_feature_tab_width_recompute(qapp: QApplication) -> None:
    page = ChartAnalysisPage()
    page.resize(1600, 900)
    page.show()
    qapp.processEvents()

    called = {"count": 0}
    original = page._recompute_feature_tab_button_widths

    def spy() -> None:
        called["count"] += 1
        original()

    page._recompute_feature_tab_button_widths = spy
    page.changeEvent(QEvent(QEvent.Type.StyleChange))
    qapp.processEvents()

    assert called["count"] >= 1


def test_chart_page_operation_hint_is_folded_into_context_strip(qapp: QApplication) -> None:
    page = ChartAnalysisPage()
    page.resize(1600, 900)
    page.show()
    qapp.processEvents()

    assert hasattr(page, "_operation_hint")
    assert not page._operation_hint.isVisible()
    assert page._operation_hint.text() == ChartAnalysisPage._OPERATION_HINT_TEXT
    page._selected_chart_ids = []
    page._sync_ui_state()
    assert ChartAnalysisPage._OPERATION_HINT_TEXT in page._chart_context_strip.text()


def test_chart_page_clearing_autoswitch_reason_keeps_persistent_operation_hint(
    qapp: QApplication,
) -> None:
    page = ChartAnalysisPage()
    page.resize(1600, 900)
    page.show()
    qapp.processEvents()

    page._set_autoswitch_reason("自動改選圖表：A → B")
    qapp.processEvents()
    assert page.get_ui_state_snapshot()["autoswitch_reason"] != ""

    page._set_autoswitch_reason("")
    qapp.processEvents()

    assert page.get_ui_state_snapshot()["autoswitch_reason"] == ""
    assert not page._operation_hint.isVisible()
    assert page._operation_hint.text() == ChartAnalysisPage._OPERATION_HINT_TEXT
    page._selected_chart_ids = []
    page._sync_ui_state()
    assert ChartAnalysisPage._OPERATION_HINT_TEXT in page._chart_context_strip.text()
    assert not page._autoswitch_hint.isVisible()


def test_chart_page_selection_feedback_highlights_context_then_clears(qapp: QApplication) -> None:
    page = ChartAnalysisPage()
    page.resize(1600, 900)
    page.show()
    qapp.processEvents()

    page._show_selection_feedback("顯示模式 雙特徵", target="mode")
    qapp.processEvents()

    assert "更新: 顯示模式 雙特徵" in page._chart_context_strip.text()
    assert page._chart_context_strip.property("interactionState") == "changed"
    assert page._mode_step_label.property("interactionState") == "changed"

    page._clear_selection_feedback()
    qapp.processEvents()

    assert "更新:" not in page._chart_context_strip.text()
    assert page._chart_context_strip.property("interactionState") == ""
    assert page._mode_step_label.property("interactionState") == ""


def test_chart_page_normalize_toggle_uses_mode_feedback(qapp: QApplication) -> None:
    page = ChartAnalysisPage()
    page._display_features = ["Height", "Area"]
    page._active_feature_tab_count = 2

    page.chk_normalize.setChecked(True)
    qapp.processEvents()

    assert "更新: 標準化 開啟" in page._chart_context_strip.text()
    assert page._mode_step_label.property("interactionState") == "changed"


def test_status_bar_remains_dynamic_for_analyzing_and_success_states(qapp: QApplication) -> None:
    model = AppStatusModel()
    widget = StatusBarWidget()
    widget.set_status_model(model)

    model.set_state(STATE_ANALYZING, "正在分析…")
    qapp.processEvents()
    assert widget._label.text() == "正在分析…"
    assert widget._lamp.property("state") == STATE_ANALYZING

    model.set_state(STATE_SUCCESS, "分析完成")
    qapp.processEvents()
    assert widget._label.text() == "分析完成"
    assert widget._lamp.property("state") == STATE_SUCCESS
