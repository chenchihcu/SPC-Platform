"""MainWindow data-loader ref helpers (see start_loading_worker / _current_data_loader_worker)."""

from __future__ import annotations

import os
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QTabWidget

from app.bootstrap.font_runtime import preferred_qt_font_family, register_qt_bundled_fonts
from app.data.session_store import SessionStore
from app.services import import_service
from app.ui.main_window import (
    MainWindow,
    NAV_TO_STACK,
    STACK_TO_TAB,
    TAB_TO_STACK,
    VISIBLE_WORKFLOW_TABS,
)
from app.ui.theme import apply_app_theme
from app.ui.theme.tokens import SIDEBAR_WIDTH_EXPANDED, WINDOW_MIN_HEIGHT
from app.ui.widgets.navigation_panel import NAV_STEP_TOOLTIPS


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    register_qt_bundled_fonts()
    apply_app_theme(app)
    app.setFont(QFont(preferred_qt_font_family()))
    return app


def test_current_data_loader_worker_none_when_unset(qapp: QApplication) -> None:
    mw = MainWindow()
    assert mw.worker is None
    assert mw._current_data_loader_worker() is None


class _FakeSignal:
    def __init__(self) -> None:
        self._callbacks: list[Any] = []

    def connect(self, callback: Any) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: Any, **kwargs: Any) -> None:
        for callback in list(self._callbacks):
            try:
                callback(*args, **kwargs)
            except TypeError:
                callback()


class _FakeDataLoaderWorker:
    created: list["_FakeDataLoaderWorker"] = []

    def __init__(self, coord_path: str = "", meas_path: str = "") -> None:
        self.coord_path = coord_path
        self.meas_path = meas_path
        self.running = True
        self.cancel_called = 0
        self.wait_calls: list[int] = []
        self.start_called = 0
        self.delete_later_called = 0
        self.finished = _FakeSignal()
        self.progress_changed = _FakeSignal()
        self.progress_value_changed = _FakeSignal()
        _FakeDataLoaderWorker.created.append(self)

    def isRunning(self) -> bool:
        return self.running

    def cancel(self) -> None:
        self.cancel_called += 1
        self.running = False

    def wait(self, timeout_ms: int) -> bool:
        self.wait_calls.append(timeout_ms)
        return True

    def deleteLater(self) -> None:
        self.delete_later_called += 1

    def start(self) -> None:
        self.start_called += 1
        self.running = True


def test_start_loading_worker_cancels_previous_running_loader(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeDataLoaderWorker.created.clear()
    monkeypatch.setattr(import_service, "DataLoaderWorker", _FakeDataLoaderWorker)
    mw = MainWindow()
    mw.on_load_finished = lambda *_args: None  # type: ignore[assignment]

    mw.start_loading_worker(meas_path="first.csv")
    first = _FakeDataLoaderWorker.created[-1]
    assert first.start_called == 1
    assert mw.worker is first

    mw.start_loading_worker(meas_path="second.csv")
    assert _FakeDataLoaderWorker.created[-1] is first
    assert first.cancel_called == 1
    assert first.wait_calls == []
    assert mw.worker is first

    first.finished.emit(False, "Cancelled")
    qapp.processEvents()
    second = _FakeDataLoaderWorker.created[-1]
    assert second is not first
    assert second.start_called == 1
    assert mw.worker is second


def test_stale_finished_from_old_loader_does_not_override_new_worker(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    _FakeDataLoaderWorker.created.clear()
    monkeypatch.setattr(import_service, "DataLoaderWorker", _FakeDataLoaderWorker)
    mw = MainWindow()
    mw.on_load_finished = lambda *_args: None  # type: ignore[assignment]

    mw.start_loading_worker(meas_path="old.csv")
    old_worker = _FakeDataLoaderWorker.created[-1]
    mw.start_loading_worker(meas_path="new.csv")
    assert _FakeDataLoaderWorker.created[-1] is old_worker

    old_worker.finished.emit(False, "Cancelled")
    qapp.processEvents()
    new_worker = _FakeDataLoaderWorker.created[-1]
    assert mw.worker is new_worker
    assert old_worker.delete_later_called == 1


def test_measurement_library_context_updates_workorder_master_with_legacy_fallback(
    qapp: QApplication,
) -> None:
    mw = MainWindow()
    store = SessionStore()
    store.clear()
    calls: list[dict[str, Any]] = []
    mw.start_loading_worker = lambda **kwargs: calls.append(kwargs)  # type: ignore[assignment]

    mw._on_meas_loaded_from_library_with_context(
        "library.csv",
        {
            "product_name": "DemoProduct",
            "supplier": "振順豐",
            "product_part_no": "PART-001",
            "work_order_no": "WO-LEGACY",
            "supplier_work_order_no": "",
            "outsource_work_order_no": "",
            "batch_no": "",
        },
    )

    assert calls == [{"meas_path": "library.csv"}]
    master = store.workorder_master
    assert master["product_name"] == "DemoProduct"
    assert master["supplier"] == "振順豐"
    assert master["product_part_no"] == "PART-001"
    assert master["work_order_no"] == ""
    assert master["supplier_work_order_no"] == ""
    assert master["outsource_work_order_no"] == "WO-LEGACY"
    assert master["batch_no"] == "WO-LEGACY"


def test_manage_specs_requested_routes_to_library_spec_tab(qapp: QApplication) -> None:
    mw = MainWindow()

    mw._on_manage_specs_requested()

    assert mw.workspace.currentIndex() == 1
    assert TAB_TO_STACK[mw.workspace.currentIndex()] == 6
    assert mw.navigation._current_stack_index == 1
    assert mw.pages["量測庫"].tabs.currentIndex() == 2


def test_left_sidebar_navigation_uses_eight_visible_workflow_steps(qapp: QApplication) -> None:
    mw = MainWindow()

    assert isinstance(mw.workspace, QTabWidget)
    assert mw.workspace.count() == 8
    assert [mw.workspace.tabText(i) for i in range(mw.workspace.count())] == [
        label for label, _stack_index in VISIBLE_WORKFLOW_TABS
    ]
    assert mw.workspace.tabBar().isHidden()
    assert TAB_TO_STACK == [0, 6, 2, 8, 5, 7, 3, 4]
    assert not mw.navigation.isHidden()
    assert [btn.text() for btn in mw.navigation._step_buttons] == [
        label for label, _stack_index in VISIBLE_WORKFLOW_TABS
    ]


def test_left_sidebar_navigation_buttons_switch_internal_pages(qapp: QApplication) -> None:
    mw = MainWindow()

    for nav_index, button in enumerate(mw.navigation._step_buttons):
        button.click()
        qapp.processEvents()

        assert mw.workspace.currentIndex() == STACK_TO_TAB[NAV_TO_STACK[nav_index]]
        assert mw.navigation._current_stack_index == nav_index


def test_sidebar_findability_groups_are_bounded(qapp: QApplication) -> None:
    mw = MainWindow()

    section_texts = [
        label.text()
        for label in mw.collapsible_sidebar.findChildren(QLabel)
        if label.property("class") == "sectionTitle"
    ]

    normalized = [
        "分析條件" if text.startswith("分析條件") else text
        for text in section_texts
    ]
    assert normalized == ["流程", "分析條件", "特徵", "動作"]
    assert len(mw.navigation._step_buttons) == 8
    assert mw.control_panel.target_btn.text() == "下一步"
    assert mw.control_panel.refresh_btn.text() == "重新分析"


def test_sidebar_default_density_does_not_overlap_or_clip_actions(qapp: QApplication) -> None:
    mw = MainWindow()
    mw.resize(1280, 720)
    mw._splitter.setSizes([SIDEBAR_WIDTH_EXPANDED, 1280 - SIDEBAR_WIDTH_EXPANDED])
    mw.show()
    qapp.processEvents()

    cp = mw.control_panel
    assert cp._condition_section_collapsed
    assert cp._condition_title.text() == "分析條件（已收合）"
    assert cp._condition_summary.isVisibleTo(mw)
    assert cp.refresh_btn.geometry().y() + cp.refresh_btn.geometry().height() <= cp.geometry().height()


def test_sidebar_min_height_collapses_conditions_before_clipping_actions(qapp: QApplication) -> None:
    mw = MainWindow()
    mw.resize(1280, WINDOW_MIN_HEIGHT)
    mw._splitter.setSizes([SIDEBAR_WIDTH_EXPANDED, 1280 - SIDEBAR_WIDTH_EXPANDED])
    mw.show()
    qapp.processEvents()

    cp = mw.control_panel
    assert cp._condition_section_collapsed
    assert cp._condition_container.isHidden()
    assert cp._condition_summary.isVisibleTo(mw)
    assert cp.target_btn.isVisibleTo(mw)
    assert cp.refresh_btn.isVisibleTo(mw)
    assert cp.refresh_btn.geometry().y() + cp.refresh_btn.geometry().height() <= cp.geometry().height()


def test_collapsed_sidebar_keeps_minimal_actions_visible(qapp: QApplication) -> None:
    mw = MainWindow()
    mw.resize(1280, 720)
    mw._splitter.setSizes([SIDEBAR_WIDTH_EXPANDED, 1280 - SIDEBAR_WIDTH_EXPANDED])
    mw.show()
    qapp.processEvents()

    mw.collapsible_sidebar._on_toggle()
    qapp.processEvents()

    assert mw.collapsible_sidebar.minimal_next_btn.isVisible()
    assert mw.collapsible_sidebar.minimal_refresh_btn.isVisible()
    assert not mw.collapsible_sidebar.minimal_next_btn.icon().isNull()
    assert not mw.collapsible_sidebar.minimal_refresh_btn.icon().isNull()


def test_hidden_measurement_stack_routes_through_chart_tab(qapp: QApplication) -> None:
    mw = MainWindow()

    mw._go_to_page(1)

    assert mw.workspace.currentIndex() == 2
    assert TAB_TO_STACK[mw.workspace.currentIndex()] == 2
    assert mw.navigation._current_stack_index == 2


def test_next_step_follows_visible_workflow_tab_order(qapp: QApplication) -> None:
    mw = MainWindow()
    captured: dict[str, int] = {}

    mw._maybe_confirm_then_go_next = lambda idx: captured.setdefault("next_idx", idx)  # type: ignore[assignment]
    mw.workspace.setCurrentIndex(0)
    mw._on_next_step_clicked()

    assert captured["next_idx"] == 6


def test_navigation_tooltips_match_sidebar_button_order(qapp: QApplication) -> None:
    mw = MainWindow()
    buttons = mw.navigation._step_buttons

    assert len(buttons) == 8
    assert len(NAV_STEP_TOOLTIPS) == 8
    assert [btn.toolTip() for btn in buttons] == NAV_STEP_TOOLTIPS


def test_text_summary_diagnostic_link_routes_to_statistics_data_page(qapp: QApplication) -> None:
    mw = MainWindow()

    mw._on_navigate_to_chart("ooc_analysis", ["Volume"])

    assert mw.workspace.currentIndex() == STACK_TO_TAB[8]
    assert TAB_TO_STACK[mw.workspace.currentIndex()] == 8
    assert mw.navigation._current_stack_index == 3
    assert mw.pages["統計資料"]._pending_select_chart_id == "ooc_analysis"
