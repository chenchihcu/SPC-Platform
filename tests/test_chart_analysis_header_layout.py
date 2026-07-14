from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QCheckBox, QGridLayout
from app.analytics.chart_registry import TEXT_SUMMARY_CHART_IDS
from app.ui.pages.chart_analysis_page import ChartAnalysisPage
from app.ui.state.app_status_model import AppStatusModel, STATE_ANALYZING, STATE_SUCCESS
from app.ui.theme.tokens import CHART_COMBINATION_COMBO_MIN_WIDTH
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
    # Analysis features live in the sidebar; the chart toolbar selects one
    # precomputed display combination and optional normalization.
    page = ChartAnalysisPage()
    page.resize(1600, 900)
    page.show()
    qapp.processEvents()

    page._display_features = ["Height", "Area"]
    page._sync_feature_combination_selector(preferred=("Height", "Area"))
    page._sync_normalize_visibility()
    qapp.processEvents()
    assert page.chk_normalize.isVisible()

    assert page._mode_step_label.text() == ChartAnalysisPage._MODE_STEP_TEXT
    assert page.chk_normalize.text() == ChartAnalysisPage._NORMALIZE_LABEL
    assert not hasattr(page, "_feature_step_label")
    assert not hasattr(page, "btn_feature_height")

    controls = [
        page._mode_step_label,
        page.feature_combination_combo,
        page.chk_normalize,
    ]
    center_y_positions = [w.mapTo(page, w.rect().center()).y() for w in controls]
    x_positions = [w.mapTo(page, w.rect().topLeft()).x() for w in controls]
    right_edges = [w.mapTo(page, w.rect().topRight()).x() for w in controls]
    adjacent_gaps = [
        x_positions[i + 1] - right_edges[i] - 1
        for i in range(len(controls) - 1)
    ]

    assert max(center_y_positions) - min(center_y_positions) <= 2
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
    assert not set(page._chart_id_to_checkbox).intersection(TEXT_SUMMARY_CHART_IDS)
    assert max(option.geometry().bottom() for option in options) <= content.rect().bottom()


def test_chart_page_combination_selector_uses_tokenized_min_width(qapp: QApplication) -> None:
    page = ChartAnalysisPage()
    assert page.feature_combination_combo.minimumWidth() == CHART_COMBINATION_COMBO_MIN_WIDTH
    assert not hasattr(page, "_feature_tab_buttons")


def test_chart_page_combination_selector_lists_all_three_feature_combinations(
    qapp: QApplication,
) -> None:
    page = ChartAnalysisPage()
    page._display_features = ["Volume", "Area", "Height"]
    page._sync_feature_combination_selector(preferred=("Volume", "Area", "Height"))

    assert page.feature_combination_combo.count() == 7
    assert page.feature_combination_combo.findData("Volume|Height") >= 0
    assert page.feature_combination_combo.currentData() == "Volume|Area|Height"


def test_chart_page_single_combination_uses_static_label(qapp: QApplication) -> None:
    page = ChartAnalysisPage()
    page._display_features = ["Height"]
    page._sync_feature_combination_selector(preferred=("Height",))

    assert page.feature_combination_combo.isHidden()
    assert page._feature_combination_static.text() == "單變量｜高度"


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

    page._show_selection_feedback("圖表組合 體積 × 面積", target="mode")
    qapp.processEvents()

    assert "更新: 圖表組合 體積 × 面積" in page._chart_context_strip.text()
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
    page._sync_feature_combination_selector(preferred=("Height", "Area"))

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
