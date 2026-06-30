import contextlib
import logging
import sqlite3
import sys
from typing import Any, Dict, List, Optional, cast

_log = logging.getLogger(__name__)
_log.setLevel(logging.WARNING)

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QSplitter, QTabWidget, QMessageBox
from PySide6.QtGui import QKeySequence, QShortcut, QFont
from PySide6.QtCore import QSettings, QByteArray, QTimer, QThread, Signal
from shiboken6 import Shiboken
from app.bootstrap.app_config import APP_NAME, DEFAULT_WINDOW_SIZE, INITIAL_WINDOW_SCREEN_RATIO
from app.bootstrap.font_runtime import register_qt_bundled_fonts, preferred_qt_font_family
from app.ui.theme.tokens import (
    DATA_LIST_PAGE_MIN_WIDTH,
    SIDEBAR_WIDTH_EXPANDED,
    SIDEBAR_WIDTH_COLLAPSED,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
)
from app.ui.workflow_labels import (
    VISIBLE_WORKFLOW_TABS,
    WORKFLOW_LABEL_CHARTS,
    WORKFLOW_LABEL_DATA_SETUP,
    WORKFLOW_LABEL_DIAGNOSTIC_1,
    WORKFLOW_LABEL_DIAGNOSTIC_2,
    WORKFLOW_LABEL_LIBRARY,
    WORKFLOW_LABEL_REFERENCE,
    WORKFLOW_LABEL_REPORT,
    WORKFLOW_LABEL_STATISTICS_DATA,
)
from app.analytics.chart_registry import is_text_summary_chart
from app.ui.widgets.collapsible_sidebar import CollapsibleSidebar
from app.ui.widgets.status_bar import StatusBarWidget
from app.ui.theme.layout_policy import (
    ensure_window_visible,
    fit_top_level_to_available,
    normalize_text_input_policies,
)
from app.ui.state.app_status_model import (
    AppStatusModel,
    STATE_IDLE,
    STATE_LOADING,
    STATE_ANALYZING,
    STATE_SUCCESS,
    STATE_ERROR,
)
from app.ui.pages.data_setup_page import DataSetupPage
from app.ui.pages.component_select_page import ComponentSelectPage
from app.ui.pages.chart_analysis_page import ChartAnalysisPage
from app.ui.pages.statistics_data_page import StatisticsDataPage
from app.ui.pages.report_export_page import ReportExportPage
from app.ui.pages.data_management_page import DataManagementPage
from app.ui.pages.diagnostic_page import DiagnosticPage
from app.ui.pages.diagnostic_matrix_page import DiagnosticMatrixPage
from app.ui.pages.measurement_library_page import MeasurementLibraryPage
from app.services.analysis_orchestrator import (
    AnalysisOrchestrator,
    STATUS_CACHED,
    STATUS_ERROR,
    STATUS_IDLE_NO_DATA,
    STATUS_MISSING_FEATURE,
    STATUS_READY,
)
from app.services.analysis_context import AnalysisRunContext

SETTINGS_GEOMETRY_KEY = "main_window/geometry"
SETTINGS_STATE_KEY = "main_window/state"
SETTINGS_GROUP = "MainWindow"

# 實際堆疊順序
STACK_ORDER = [
    "資料",   # 0
    "量測",   # 1  元件/量測選定
    "圖表",   # 2
    "報告",   # 3
    "參考",   # 4
    "診斷",   # 5
    "量測庫", # 6  量測資料庫管理頁
    "診斷二", # 7
    "統計資料", # 8
]
# 左側導覽顯示 8 項 (統計圖表/統計資料、診斷一/診斷二各自並排)
NAV_PHASES: list[tuple[str, list[str | list[str]]]] = [
    ("", [WORKFLOW_LABEL_DATA_SETUP, WORKFLOW_LABEL_LIBRARY]),
    (
        "",
        [
            [WORKFLOW_LABEL_CHARTS, WORKFLOW_LABEL_STATISTICS_DATA],
            [WORKFLOW_LABEL_DIAGNOSTIC_1, WORKFLOW_LABEL_DIAGNOSTIC_2],
        ],
    ),
    ("", [WORKFLOW_LABEL_REPORT, WORKFLOW_LABEL_REFERENCE]),
]
# 導覽索引 (0..7) -> 堆疊索引 (0..8)
# nav: 0=資料, 1=量測庫, 2=圖表, 3=統計資料, 4=診斷一, 5=診斷二, 6=報告, 7=參考
NAV_TO_STACK = [0, 6, 2, 8, 5, 7, 3, 4]
# 堆疊索引 -> 導覽索引
STACK_TO_NAV = {0: 0, 1: 2, 2: 2, 3: 6, 4: 7, 5: 4, 6: 1, 7: 5, 8: 3}
TAB_TO_STACK = [stack_index for _, stack_index in VISIBLE_WORKFLOW_TABS]
STACK_TO_TAB = {stack_index: tab_index for tab_index, stack_index in enumerate(TAB_TO_STACK)}
# 相容：部分程式仍用 PAGE_NAMES 當頁名列表
PAGE_NAMES = STACK_ORDER

REFRESH_DEBOUNCE_MS = 600


class AnalysisWorker(QThread):
    """Runs analysis in background; emits result_ready(payload, success, generation_id, error_message)."""
    result_ready = Signal(object, bool, int, str)  # payload or None, success, generation_id, error_message

    def __init__(
        self,
        generation_id: int,
        filtered_df: Any,
        selected_features: List[str],
        usl: float,
        lsl: float,
        target: float,
        workorder_spec: Dict[str, Any],
        workorder_master: Optional[Dict[str, Any]] = None,
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self._generation_id = generation_id
        self._filtered_df = filtered_df
        self._selected_features = selected_features
        self._usl = usl
        self._lsl = lsl
        self._target = target
        self._workorder_spec = workorder_spec
        self._workorder_master = workorder_master or {}
        self._cancelled = False

    def cancel(self) -> None:
        """Mark this worker as cancelled so it skips computation."""
        self._cancelled = True

    # Add progress signal
    progress_updated = Signal(int, str)

    def run(self) -> None:
        """Run analysis payload computation in background and emit completion signal."""
        if self._cancelled:
            return
        
        from app.viewmodels.chart_analysis_viewmodel import (
            compute_analysis_payload,
            _AnalysisCancelled,
        )

        def progress_cb(val, msg):
            if not self._cancelled:
                self.progress_updated.emit(val, msg)

        try:
            payload, err = compute_analysis_payload(
                self._filtered_df,
                self._selected_features,
                self._usl,
                self._lsl,
                self._target,
                self._workorder_spec,
                workorder_master=self._workorder_master,
                cancel_fn=lambda: self._cancelled,
                progress_callback=progress_cb
            )
        except _AnalysisCancelled:
            return
        if self._cancelled:
            return
        success = err is None
        self.result_ready.emit(payload, success, self._generation_id, err or "")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self._post_show_geometry_clamped = False

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._splitter = QSplitter()
        layout.addWidget(self._splitter)

        self.collapsible_sidebar = CollapsibleSidebar(phases=NAV_PHASES)
        self.navigation = self.collapsible_sidebar.navigation
        self.control_panel = self.collapsible_sidebar.control_panel
        self.workspace = QTabWidget()
        self.workspace.setObjectName("workflowTabs")
        self.workspace.setMinimumWidth(DATA_LIST_PAGE_MIN_WIDTH)

        self.status_model = AppStatusModel(self)
        self.pages: Dict[str, Any] = {
            "資料": DataSetupPage(),
            "量測": ComponentSelectPage(),
            "圖表": ChartAnalysisPage(status_model=self.status_model),
            "統計資料": StatisticsDataPage(),
            "報告": ReportExportPage(status_model=self.status_model),
            "參考": DataManagementPage(),
            "診斷": DiagnosticPage(show_matrix_tabs=False),
            "診斷二": DiagnosticMatrixPage(),
            "量測庫": MeasurementLibraryPage(),
        }
        # Wire references for cross-page refreshes
        self.pages["量測庫"].coord_page = self.pages["資料"]
        
        for tab_label, stack_index in VISIBLE_WORKFLOW_TABS:
            self.workspace.addTab(self.pages[STACK_ORDER[stack_index]], tab_label)
        self.workspace.tabBar().hide()

        # Hook Data Import Signals (from unified 資料 page)
        self.pages["資料"].meas_uploaded.connect(self._on_meas_uploaded)
        self.pages["資料"].coord_uploaded.connect(self._on_coord_uploaded)
        self.pages["資料"].product_name_selected.connect(self._on_product_name_selected)
        self.pages["資料"].start_analysis_requested.connect(self._on_data_setup_start_analysis)
        self.pages["資料"].spec_saved.connect(self._on_product_name_selected)
        self.pages["資料"].manage_specs_requested.connect(self._on_manage_specs_requested)

        # Hook Measurement Library: 從資料庫選取量測檔載入分析
        # 注意：走專屬 handler，不重複寫入 DB
        measurement_library_page: MeasurementLibraryPage = self.pages["量測庫"]
        if hasattr(measurement_library_page, "measurement_selected_with_context"):
            measurement_library_page.measurement_selected_with_context.connect(
                self._on_meas_loaded_from_library_with_context
            )
        else:
            measurement_library_page.measurement_selected.connect(self._on_meas_loaded_from_library)
        measurement_library_page.coordinate_selected.connect(self._on_coord_loaded_from_library)
        measurement_library_page.spec_selected.connect(self._on_product_name_selected)

        self._splitter.addWidget(self.collapsible_sidebar)
        self._splitter.addWidget(self.workspace)
        self._apply_initial_geometry_and_splitter()
        self.collapsible_sidebar.collapse_changed.connect(self._on_sidebar_collapse_changed)

        self.status_widget = StatusBarWidget()
        self.status_widget.set_status_model(self.status_model)
        self.statusBar().addPermanentWidget(self.status_widget, 1)

        self.navigation.step_clicked.connect(self._on_nav_step_clicked)
        self.workspace.currentChanged.connect(self._on_workspace_current_changed)
        self.navigation.set_current_stack_index(0)  # Default to 資料 (start of workflow)
        
        # ── ViewModel & Data Binding ──
        from app.viewmodels.chart_analysis_viewmodel import ChartAnalysisViewModel
        self.chart_vm = ChartAnalysisViewModel()
        self.analysis_orchestrator = AnalysisOrchestrator()
        self._active_analysis_run_context: Optional[AnalysisRunContext] = None
        self.chart_vm.data_ready.connect(self.pages["圖表"].update_all_charts)
        self.chart_vm.data_ready.connect(self.pages["統計資料"].update_all_statistics)
        self.chart_vm.data_ready.connect(self.pages["診斷"].update_hints)
        self.chart_vm.data_ready.connect(self.pages["診斷二"].update_hints)
        self.chart_vm.error_occurred.connect(self._on_analysis_error)
        self.chart_vm.summary_mode_changed.connect(self.pages["圖表"].set_summary_mode)
        self.pages["圖表"].summary_mode_changed.connect(self.chart_vm.set_summary_mode)
        self.chart_vm.set_summary_mode(self.chart_vm.summary_mode)


        # Wire Control Panel Actions (full panel and minimal strip when collapsed)
        self.control_panel.refresh_btn.clicked.connect(self.refresh_analysis)
        self.control_panel.target_btn.clicked.connect(self._on_next_step_clicked)
        self.collapsible_sidebar.minimal_refresh_btn.clicked.connect(self.refresh_analysis)
        self.collapsible_sidebar.minimal_next_btn.clicked.connect(self._on_next_step_clicked)
        # Sidebar feature toggles → same handler as old chart-page shortcuts
        self.control_panel.feature_shortcut_toggled.connect(self._on_feature_shortcut_clicked)

        # Keep track of user selected paths globally
        self.current_coord_path = ""
        self.current_meas_path = ""
        self._pending_workorder_save_after_load = False
        self._pending_workorder_style_after_refresh = False  # set when refresh was triggered by save/load; apply style in _on_analysis_result_ready

        # Auto-refresh: generation id and debounce timer
        self._analysis_generation_id = 0
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._run_refresh_analysis)
        self._analysis_worker: Optional[AnalysisWorker] = None
        self.worker: Optional[Any] = None
        self._loader_restart_queued = False

        # Feature selection uses debounce (user may click 3 checkboxes rapidly)
        self.pages["量測"].selection_changed.connect(lambda _: self._schedule_refresh_analysis(immediate=False))
        # Keep sidebar feature buttons in sync when ComponentSelectPage changes externally
        self.pages["量測"].selection_changed.connect(
            lambda selected: self.control_panel.sync_feature_states(selected)
        )
        self.control_panel.range_combo.currentTextChanged.connect(lambda _: self._schedule_refresh_analysis(immediate=True))
        self.control_panel.board_specify_combo.currentTextChanged.connect(lambda _: self._schedule_refresh_analysis(immediate=True))
        self.control_panel.refdes_combo.currentTextChanged.connect(lambda _: self._schedule_refresh_analysis(immediate=True))
        self.control_panel.part_type_combo.currentTextChanged.connect(lambda _: self._schedule_refresh_analysis(immediate=True))
        self.control_panel.optional_filters_changed.connect(lambda: self._schedule_refresh_analysis(immediate=True))
        # Pareto bar click → set component filter and refresh (component SPC)
        self.pages["圖表"].pareto_component_selected.connect(self._on_pareto_component_selected)
        # 診斷頁「前往圖表頁」→ 切換至圖表頁並選取圖表
        self.pages["診斷"].navigate_to_chart.connect(self._on_navigate_to_chart)
        self.pages["診斷二"].navigate_to_chart.connect(self._on_navigate_to_chart)

        # Debounce: Optional filters
        # Keyboard shortcuts（Ctrl+1..8 對應左側可見 workflow 導覽）
        QShortcut(QKeySequence("Ctrl+R"), self, self.refresh_analysis)
        QShortcut(QKeySequence("Ctrl+Right"), self, self._on_next_step_clicked)
        for tab_i, stack_idx in enumerate(TAB_TO_STACK):
            QShortcut(
                QKeySequence(f"Ctrl+{tab_i + 1}"),
                self,
                lambda checked=False, s=stack_idx: self._go_to_page(s),
            )

        # Accessibility: object and accessible names for key widgets
        self.workspace.setAccessibleName("工作流程內容容器")
        self.workspace.setAccessibleDescription(
            "頁面內容由左側流程導覽切換：" + "、".join(label for label, _stack_index in VISIBLE_WORKFLOW_TABS)
        )
        self.navigation.setAccessibleName("流程導覽")
        self.navigation.setAccessibleDescription("左側流程切換：" + "、".join(label for label, _stack_index in VISIBLE_WORKFLOW_TABS))
        self.control_panel.refresh_btn.setAccessibleName("重新分析按鈕")
        self.control_panel.target_btn.setAccessibleName("下一步按鈕")

        # 初始化：同步側欄特徵按鈕狀態
        _init_selected = self.pages["量測"].get_selected_features() if hasattr(self.pages["量測"], "get_selected_features") else []
        self.control_panel.sync_feature_states(_init_selected)
        normalize_text_input_policies(self)

    def _on_analysis_error(self, msg: str) -> None:
        self.statusBar().showMessage(f"分析錯誤：{msg}", 5000)
        self.status_model.set_state(STATE_ERROR, f"分析錯誤：{msg}")

    def _on_loader_progress(self, msg: str) -> None:
        self.statusBar().showMessage(msg)
        self.status_model.set_state(STATE_LOADING, msg)

    def _on_loader_progress_value(self, value: int) -> None:
        self.status_model.set_progress(value)

    def _on_navigate_to_chart(self, chart_id: str, feature_set: list) -> None:
        """Route DiagnosticPage linkage clicks to chart visuals or text-summary data."""
        if is_text_summary_chart(chart_id):
            self._go_to_page(8)  # stack index 8 = 統計資料
            self.pages["統計資料"].select_summary(chart_id, feature_set)
            return
        self._go_to_page(2)  # stack index 2 = 圖表
        self.pages["圖表"].select_recommended_charts([chart_id], feature_set)

    def _on_pareto_component_selected(self, component_id: str) -> None:
        """Set component filter from Pareto bar click and refresh so downstream charts show component SPC."""
        combo = self.control_panel.part_type_combo
        idx = combo.findText(component_id)
        if idx >= 0:
            combo.blockSignals(True)
            try:
                combo.setCurrentIndex(idx)
            finally:
                combo.blockSignals(False)
            self._schedule_refresh_analysis(immediate=True)

    def _on_spec_text_changed(self) -> None:
        self._schedule_refresh_analysis(immediate=False)

    def _on_feature_shortcut_clicked(self, logical_name: str) -> None:
        """高度 / 面積 / 體積快捷：toggle 量測頁勾選並同步側欄按鈕狀態。"""
        mapping = {"height": "Height", "area": "Area", "volume": "Volume"}
        col = mapping.get(logical_name.lower())
        if not col:
            return
        comp_page = self.pages["量測"]
        if hasattr(comp_page, "toggle_feature"):
            comp_page.toggle_feature(col)
        selected = comp_page.get_selected_features() if hasattr(comp_page, "get_selected_features") else []
        self.control_panel.sync_feature_states(selected)
        self._schedule_refresh_analysis(immediate=True)

    def _schedule_refresh_analysis(self, immediate: bool) -> None:
        if immediate:
            self._refresh_timer.stop()
            self._run_refresh_analysis()
        else:
            self._refresh_timer.start(REFRESH_DEBOUNCE_MS)

    def _clear_analysis_worker(self, worker: "AnalysisWorker") -> None:
        """Null out the shared worker reference when a specific worker finishes.

        This must be connected to the worker's ``finished`` signal *before*
        ``deleteLater`` so that ``_analysis_worker`` is cleared before the Qt
        event loop destroys the underlying C++ QThread object.  Without this,
        a subsequent call to ``_analysis_worker.isRunning()`` would raise
        ``RuntimeError: Internal C++ object already deleted``.
        """
        if self._analysis_worker is worker:
            self._analysis_worker = None

    def _restore_refresh_button(self, gen_id: Optional[int] = None) -> None:
        """Restore the refresh button from its loading state.

        When called with a gen_id (from a worker ``finished`` signal), only
        restores if gen_id matches ``_refresh_button_gen`` — the generation
        recorded when the manual refresh was triggered.  This prevents a
        *cancelled* predecessor worker from prematurely clearing the loading
        state before the active worker completes.

        When called without gen_id (early-return paths inside
        ``_run_refresh_analysis``), always restores unconditionally.
        """
        if not getattr(self, "_refresh_button_loading", False):
            return
        if gen_id is not None and gen_id != getattr(self, "_refresh_button_gen", None):
            return
        self._refresh_button_loading = False
        refresh_btn = self.control_panel.refresh_btn
        refresh_btn.setEnabled(True)
        refresh_btn.setText("重新分析")
        refresh_btn.setProperty("state", "")
        refresh_btn.style().unpolish(refresh_btn)
        refresh_btn.style().polish(refresh_btn)
        self.status_model.set_progress(-2) # Ensure hidden

    def _run_refresh_analysis(self) -> None:
        comp_page = self.pages["量測"]
        selected_features = comp_page.get_selected_features() if hasattr(comp_page, "get_selected_features") else []

        store = self._get_store()

        range_mode = self.control_panel.range_combo.currentText()
        board_specify = self.control_panel.board_specify_combo.currentText()
        refdes = self.control_panel.refdes_combo.currentText()
        part_type = self.control_panel.part_type_combo.currentText()
        opt = self.control_panel.get_optional_filters()
        manual_workorder_spec = store.workorder_spec or {}
        prep = self.analysis_orchestrator.prepare_refresh(
            store=store,
            selected_features=selected_features,
            range_mode=range_mode,
            board_specify=board_specify,
            refdes=refdes,
            part_type=part_type,
            optional_filters=opt,
            manual_workorder_spec=manual_workorder_spec,
        )
        self._active_analysis_run_context = None
        if prep.status == STATUS_MISSING_FEATURE:
            self.statusBar().showMessage(prep.message, 5000)
            self.status_model.set_state(STATE_IDLE, "就緒 (Ready)")
            self._restore_refresh_button()
            return
        if prep.status == STATUS_IDLE_NO_DATA:
            self.status_model.set_state(STATE_IDLE, prep.message or "待載入資料")
            self._restore_refresh_button()
            return
        if prep.status == STATUS_ERROR:
            msg = prep.message or "分析失敗"
            self.statusBar().showMessage(msg, 6000)
            self.status_model.set_state(STATE_ERROR, msg)
            self._restore_refresh_button()
            return
        if prep.status == STATUS_CACHED and prep.cached_payload is not None:
            store.selected_features = list(prep.selected_features)
            cached = prep.cached_payload
            self.analysis_orchestrator.apply_payload_context(
                cached,
                batch=prep.batch,
                refdes=prep.refdes,
                part_type=prep.part_type,
                filter_context=prep.filter_context,
            )
            store.last_analysis_payload = cached
            self.chart_vm.data_ready.emit(cached)
            self.status_model.set_state(STATE_SUCCESS, "分析完成")
            self._restore_refresh_button()
            return
        if prep.status != STATUS_READY or prep.filtered_df is None:
            self.status_model.set_state(STATE_ERROR, "分析失敗")
            self._restore_refresh_button()
            return
        self._active_analysis_run_context = prep.run_context

        self._analysis_generation_id += 1
        current_id = self._analysis_generation_id
        # Cancel previous worker to avoid wasted CPU.
        # Guard with try/except: deleteLater may have already destroyed the C++
        # object while the Python wrapper still exists (_clear_analysis_worker
        # handles the common case; this catch covers any residual timing edge).
        if self._analysis_worker is not None:
            try:
                if self._analysis_worker.isRunning():
                    self._analysis_worker.cancel()
            except RuntimeError:
                self._analysis_worker = None
        self.status_model.set_state(STATE_ANALYZING, "正在分析…")

        # If this worker is created while the loading state is active, pin the
        # restore target to this generation so only *this* worker's finish will
        # clear "計算中…" (prevents a cancelled predecessor's finished signal
        # from prematurely resetting the flag).
        if getattr(self, "_refresh_button_loading", False):
            self._refresh_button_gen = current_id

        self._analysis_worker = AnalysisWorker(
            current_id,
            prep.filtered_df,
            prep.selected_features,
            prep.usl,
            prep.lsl,
            prep.target,
            store.workorder_spec,
            workorder_master=dict(store.workorder_master or {}),
        )
        self._analysis_worker.progress_updated.connect(self.status_model.set_progress)
        self._analysis_worker.result_ready.connect(self._on_analysis_result_ready)  # (payload, success, gen_id, error_msg)
        # Clear the shared reference FIRST so isRunning() is never called on
        # a C++ object that has already been destroyed by deleteLater.
        _w = self._analysis_worker
        self._analysis_worker.finished.connect(lambda w=_w: self._clear_analysis_worker(w))
        self._analysis_worker.finished.connect(self._analysis_worker.deleteLater)
        # AGENTS §3: restore on worker exit (e.g. exception in run())
        # Pass gen_id via lambda so only the pinned generation clears loading state.
        self._analysis_worker.finished.connect(
            lambda _g=current_id: self._restore_refresh_button(_g)
        )
        self._analysis_worker.start()

    def _on_analysis_result_ready(self, payload: Any, success: bool, generation_id: int, error_message: str = "") -> None:
        if generation_id != self._analysis_generation_id:
            return
        self.status_model.set_progress(-2) # Hide
        self._restore_refresh_button()
        if success and payload is not None:
            store = self._get_store()
            store.selected_features = list(payload.get("selected_features", []))
            run_context = self._active_analysis_run_context
            if run_context is not None:
                batch = run_context.filters.batch
                refdes = run_context.filters.refdes
                part_type = run_context.filters.part_type
            else:
                batch = str(getattr(store, "filter_batch", None) or "")
                refdes = str(getattr(store, "filter_refdes", None) or "")
                part_type = str(getattr(store, "filter_part_type", None) or "")
            self.analysis_orchestrator.apply_payload_context(
                payload,
                batch=batch,
                refdes=refdes,
                part_type=part_type,
                filter_context=run_context.filters if run_context is not None else None,
            )
            self.analysis_orchestrator.cache_payload(
                store,
                payload,
                batch=batch,
                refdes=refdes,
                part_type=part_type,
                run_context=run_context,
            )
            self.chart_vm.data_ready.emit(payload)
            self.status_model.set_state(STATE_SUCCESS, "分析完成")
            self.statusBar().showMessage("分析完成", 2000)
        else:
            msg = error_message or "分析失敗"
            self.status_model.set_state(STATE_ERROR, msg)
            self.chart_vm.error_occurred.emit(msg)
        self._active_analysis_run_context = None

        if getattr(self, "_pending_workorder_style_after_refresh", False):
            self._pending_workorder_style_after_refresh = False
            if success:
                self.statusBar().showMessage("座標已依產品名稱載入，規格已套用。", 3000)
            else:
                self.statusBar().showMessage("座標已載入，但分析失敗，請檢查規格數值。", 5000)

    def _settings(self) -> QSettings:
        return QSettings("SPC", "PlatformV2")

    def _apply_initial_geometry_and_splitter(self) -> None:
        """Restore saved geometry/state or use QScreen-based initial size and center (spec W-01, W-04)."""
        s = self._settings()
        s.beginGroup(SETTINGS_GROUP)
        geom = cast(QByteArray, s.value(SETTINGS_GEOMETRY_KEY, QByteArray()))
        state = cast(QByteArray, s.value(SETTINGS_STATE_KEY, QByteArray()))
        s.endGroup()
        restored_geometry = bool(geom and self.restoreGeometry(geom))
        if restored_geometry:
            restored_geometry = ensure_window_visible(self)

        if restored_geometry:
            if state:
                self.restoreState(state)
        else:
            fit_top_level_to_available(
                self,
                screen_ratio=INITIAL_WINDOW_SCREEN_RATIO,
                fallback_size=DEFAULT_WINDOW_SIZE,
            )
        total = self.width()
        # 專業佈局：sidebar 固定 220px 左右，主工作區取剩餘空間
        sidebar_w = SIDEBAR_WIDTH_EXPANDED
        workspace_min = DATA_LIST_PAGE_MIN_WIDTH
        left_w = sidebar_w
        right_w = max(workspace_min, total - left_w)
        self._splitter.setSizes([left_w, right_w])

    def showEvent(self, event) -> None:
        """Clamp native frame geometry after Windows applies titlebar/borders."""
        super().showEvent(event)
        if self._post_show_geometry_clamped:
            return
        self._post_show_geometry_clamped = True
        QTimer.singleShot(0, self._clamp_native_frame_visible)

    def _clamp_native_frame_visible(self) -> None:
        if ensure_window_visible(self):
            return
        fit_top_level_to_available(
            self,
            screen_ratio=INITIAL_WINDOW_SCREEN_RATIO,
            fallback_size=DEFAULT_WINDOW_SIZE,
        )

    def closeEvent(self, event) -> None:
        """
        Gracefully terminate all background workers before closing.
        Prevents signals from being emitted to destroyed C++ objects (Pass 145).
        """
        if hasattr(self, "_analysis_worker") and self._analysis_worker and self._analysis_worker.isRunning():
            self._analysis_worker.cancel()
            self._analysis_worker.wait(500)

        # Cancel data loader worker if any (guard: C++ object may already be gone)
        prev_loader = self._current_data_loader_worker()
        if prev_loader is not None and prev_loader.isRunning():
            prev_loader.cancel()
            prev_loader.wait(2000)
            
        # Add cleanup for other workers (e.g. data loaders) if they exist
        # ...
            
        s = self._settings()
        s.beginGroup(SETTINGS_GROUP)
        s.setValue(SETTINGS_GEOMETRY_KEY, self.saveGeometry())
        s.setValue(SETTINGS_STATE_KEY, self.saveState())
        s.endGroup()
        super().closeEvent(event)

    def _on_sidebar_collapse_changed(self, collapsed: bool) -> None:
        """Update splitter sizes when sidebar is collapsed or expanded (two panels)."""
        sizes = self._splitter.sizes()
        if len(sizes) != 2:
            return
        total = sum(sizes)
        left_w = SIDEBAR_WIDTH_COLLAPSED if collapsed else SIDEBAR_WIDTH_EXPANDED
        right_w = max(DATA_LIST_PAGE_MIN_WIDTH, total - left_w)
        left_w = total - right_w
        self._splitter.setSizes([left_w, right_w])

    def _go_to_page(self, stack_index: int) -> None:
        """Switch to page by workspace stack index (0-based). Used by Ctrl+1..8 shortcuts."""
        if 0 <= stack_index < len(STACK_ORDER):
            tab_index = STACK_TO_TAB.get(stack_index)
            if tab_index is None:
                visible_stack = NAV_TO_STACK[STACK_TO_NAV.get(stack_index, 0)]
                tab_index = STACK_TO_TAB.get(visible_stack, 0)
            self.workspace.setCurrentIndex(tab_index)
            nav_i = STACK_TO_NAV.get(stack_index, 0)
            self.navigation.set_current_stack_index(nav_i)
            self._refresh_page_on_entry(stack_index)

    def _current_stack_index(self) -> int:
        """Return the internal stack index represented by the current visible tab."""
        tab_index = self.workspace.currentIndex()
        if 0 <= tab_index < len(TAB_TO_STACK):
            return TAB_TO_STACK[tab_index]
        return 0

    def _on_workspace_current_changed(self, tab_index: int) -> None:
        """Internal workflow container changed; synchronize visible left navigation state."""
        stack_index = TAB_TO_STACK[tab_index] if 0 <= tab_index < len(TAB_TO_STACK) else 0
        nav_i = STACK_TO_NAV.get(stack_index, 0)
        self.navigation.set_current_stack_index(nav_i)
        self._refresh_page_on_entry(stack_index)

    def _refresh_page_on_entry(self, stack_index: int) -> None:
        """Refresh page-owned lists when a workflow page becomes active."""
        page_name = STACK_ORDER[stack_index]
        if page_name == "資料":
            self.pages["資料"].refresh_registered_list()
            self._sync_workorder_master_to_page()
        elif page_name == "量測庫":
            self.pages["量測庫"].refresh()
            self.pages["量測庫"].refresh_coordinates()
            self.pages["量測庫"].refresh_specs()
            self.pages["量測庫"].refresh_suppliers()

    def _on_nav_step_clicked(self, nav_index: int) -> None:
        """Left workflow navigation slot: nav_index 0..7 routes to the matching internal page."""
        if 0 <= nav_index < len(NAV_TO_STACK):
            stack_idx = NAV_TO_STACK[nav_index]
            self.workspace.setCurrentIndex(STACK_TO_TAB.get(stack_idx, 0))
            self.navigation.set_current_stack_index(nav_index)
            self._refresh_page_on_entry(stack_idx)

    def _apply_next_step(self, next_stack_idx: int) -> None:
        """Apply navigation to the given stack index (used after optional Phase 3 confirmation)."""
        self.workspace.setCurrentIndex(STACK_TO_TAB.get(next_stack_idx, 0))
        nav_i = STACK_TO_NAV.get(next_stack_idx, 0)
        self.navigation.set_current_stack_index(nav_i)

    def _on_next_step_clicked(self) -> None:
        """下一步：依流程順序前進（跳過僅由圖表頁進入的「量測」）。"""
        current_stack_idx = self._current_stack_index()
        current_tab_idx = STACK_TO_TAB.get(current_stack_idx, 0)
        next_tab_idx = (current_tab_idx + 1) % len(TAB_TO_STACK)
        next_idx = TAB_TO_STACK[next_tab_idx]
        self._maybe_confirm_then_go_next(next_idx)

    def _maybe_confirm_then_go_next(self, next_idx: int) -> None:
        """Optionally prompt when entering 圖表分析 without coords or 報告輸出 with low match rate; then go to next step."""
        from app.data.session_store import SessionStore
        store = SessionStore()
        next_name = PAGE_NAMES[next_idx]

        from app.ui.theme import apply_dark_palette_to_message_box
        if next_name == "圖表":
            coord_ok = store.coord_meta.get("is_valid", False)
            if not coord_ok:
                mb = QMessageBox(
                    QMessageBox.Icon.Question,
                    "提醒",
                    "尚未載入座標，空間分析將無法使用。是否仍要繼續？",
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                    self,
                )
                mb.setDefaultButton(QMessageBox.StandardButton.Cancel)
                apply_dark_palette_to_message_box(mb)
                reply = mb.exec()
                if reply != QMessageBox.StandardButton.Ok:
                    return
        elif next_name == "報告":
            rate = store.relation_meta.get("match_rate", 0.0)
            if rate >= 0 and rate < 90:
                mb = QMessageBox(
                    QMessageBox.Icon.Question,
                    "提醒",
                    "關聯成功率偏低，報告中的空間資訊可能不完整。是否仍要繼續？",
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                    self,
                )
                mb.setDefaultButton(QMessageBox.StandardButton.Cancel)
                apply_dark_palette_to_message_box(mb)
                reply = mb.exec()
                if reply != QMessageBox.StandardButton.Ok:
                    return

        self._apply_next_step(next_idx)

    def _on_data_setup_start_analysis(self) -> None:
        """Data Setup footer action: sync fields and run refresh analysis immediately."""
        self._sync_page_to_store()
        self.refresh_analysis()
        self.statusBar().showMessage("已開始分析目前資料設定。", 3000)

    def _sync_page_to_store(self):
        """從資料設定頁收集工單/產品資訊並寫入 store 與資料庫中繼。"""
        from app.data.session_store import SessionStore
        from app.services.spec_resolver import resolve_workorder_spec
        from app.data.product_spec_registry import get as get_product_spec
        
        data_page: DataSetupPage = self.pages["資料"]
        info = data_page.get_workorder_info()
        store = SessionStore()
        
        # 寫入工單主檔
        product_name = info["product_name"]
        store.workorder_master = {
            "work_order_no": info["work_order_no"],
            "supplier_work_order_no": info["supplier_work_order_no"],
            "outsource_work_order_no": info["outsource_work_order_no"],
            "product_name": product_name,
            "product_part_no": "", # 料號現在由座標註冊表/量測庫管理
            "supplier": info["supplier"],
            "batch_no": info["batch_no"],
            "batch_qty": info["batch_qty"],
            "paste_type": info["paste_type"],
            "line_name": info["line_name"],
            "production_date": info["production_date"],
        }
        
        # 規格解析
        if product_name and get_product_spec(product_name) is not None:
            workorder_spec, _ = resolve_workorder_spec(product_name)
            if workorder_spec:
                store.workorder_spec = workorder_spec

    def _on_meas_uploaded(self, path: str):
        """新上傳量測檔：先寫入量測庫中繼與 store，再排程載入 CSV。"""
        # 先自動儲存（同步）：確保 batch_no 等已進 store，並取得 session_id 供載入後補 row_count
        self._auto_save_meas_session(path)
        self.start_loading_worker(meas_path=path)
        self.statusBar().showMessage(f"已排程讀取量測檔：{path}", 2000)

    def _on_meas_loaded_from_library(self, path: str):
        """從量測資料庫選取載入：只觸發分析，不重複寫入 DB。"""
        self.start_loading_worker(meas_path=path)
        self.statusBar().showMessage(f"已從資料庫載入量測檔：{path}", 2000)

    def _on_meas_loaded_from_library_with_context(self, path: str, context: Dict[str, Any]) -> None:
        """從量測庫載入（含 metadata）時，同步回填 workorder_master 雙欄位。"""
        if isinstance(context, dict):
            self._apply_measurement_library_context(context)
        self._on_meas_loaded_from_library(path)

    def _apply_measurement_library_context(self, context: Dict[str, Any]) -> None:
        from app.data.session_store import SessionStore

        store = SessionStore()
        if store.workorder_master is None:
            store.workorder_master = {}
        master = store.workorder_master

        supplier_work_order_no = str(context.get("supplier_work_order_no") or "").strip()
        outsource_work_order_no = str(context.get("outsource_work_order_no") or "").strip()
        legacy_work_order_no = str(context.get("work_order_no") or "").strip()
        if not outsource_work_order_no:
            outsource_work_order_no = legacy_work_order_no
        primary_work_order_no = outsource_work_order_no or supplier_work_order_no
        batch_no = str(context.get("batch_no") or "").strip() or primary_work_order_no
        product_name = str(context.get("product_name") or "").strip()
        product_part_no = str(context.get("product_part_no") or "").strip()
        supplier = str(context.get("supplier") or "").strip()

        master["work_order_no"] = ""
        master["supplier"] = supplier
        master["supplier_work_order_no"] = supplier_work_order_no
        master["outsource_work_order_no"] = outsource_work_order_no
        master["batch_no"] = batch_no
        if product_name:
            master["product_name"] = product_name
        if product_part_no:
            master["product_part_no"] = product_part_no
        self._sync_workorder_master_to_page()

    def _on_coord_loaded_from_library(self, path: str):
        """從座標資料庫選取載入：不重複寫入 DB。"""
        self.start_loading_worker(coord_path=path)
        self.statusBar().showMessage(f"已從資料庫載入座標檔：{path}", 2000)

    def _auto_save_meas_session(self, path: str) -> None:
        """上傳量測檔後，自動將記錄儲存至量測資料庫，並記錄 session_id 以便後續更新 row_count。"""
        from app.data.session_store import SessionStore
        store = SessionStore()
        master = store.workorder_master or {}
        product_name = master.get("product_name") or ""
        supplier_work_order_no = master.get("supplier_work_order_no") or ""
        outsource_work_order_no = master.get("outsource_work_order_no") or ""
        batch_no = (master.get("batch_no") or "").strip()
        product_part_no = master.get("product_part_no") or ""
        supplier = master.get("supplier") or ""
        try:
            # 優先從 UI 即時讀取，避免 store 為舊值
            data_setup_page = self.pages["資料"]
            info = data_setup_page.get_workorder_info()
            if not supplier_work_order_no:
                supplier_work_order_no = info.get("supplier_work_order_no", "")
            if not outsource_work_order_no:
                outsource_work_order_no = info.get("outsource_work_order_no", "")
            if not product_name:
                product_name = info["product_name"]
            if not batch_no:
                batch_no = info["batch_no"]
            if not supplier:
                supplier = info.get("supplier", "")
        except (KeyError, AttributeError):
            _log.warning(
                "Workorder info is missing required fields during auto save",
                exc_info=True,
            )
        if store.workorder_master is None:
            store.workorder_master = {}
        store.workorder_master["work_order_no"] = ""
        store.workorder_master["supplier_work_order_no"] = supplier_work_order_no
        store.workorder_master["outsource_work_order_no"] = outsource_work_order_no
        store.workorder_master["batch_no"] = batch_no
        store.workorder_master["supplier"] = supplier
        lib_page: MeasurementLibraryPage = self.pages["量測庫"]
        sid = lib_page.save_and_refresh(
            path,
            product_name=product_name,
            supplier=supplier,
            work_order_no="",
            supplier_work_order_no=supplier_work_order_no,
            outsource_work_order_no=outsource_work_order_no,
            batch_no=batch_no,
            product_part_no=product_part_no,
        )
        # 記下本次 session_id，待 on_load_finished 後補填實際 row_count
        self._pending_meas_session_id: int = sid if sid > 0 else -1
        
    def _on_coord_uploaded(self, path: str):
        self.start_loading_worker(coord_path=path)
        self.statusBar().showMessage(f"已排隊：準備讀取座標檔 ({path})", 2000)

    def _on_product_name_selected(self, name: str):
        """Single source: product name from Data Setup → store."""
        from app.data.session_store import SessionStore
        store = SessionStore()
        if store.workorder_master is None:
            store.workorder_master = {}
        prev = (store.workorder_master.get("product_name") or "").strip()
        new = (name or "").strip()
        store.workorder_master["product_name"] = name or ""
        if prev and new and prev != new:
            store.workorder_master["batch_no"] = ""
            store.workorder_master["work_order_no"] = ""
            store.workorder_master["supplier_work_order_no"] = ""
            store.workorder_master["outsource_work_order_no"] = ""

        # Auto-resolve and sync specs if product has a registered spec
        if name:
            from app.services.spec_resolver import resolve_workorder_spec
            workorder_spec, _ = resolve_workorder_spec(name)
            if workorder_spec:
                store.workorder_spec = workorder_spec

    def _on_manage_specs_requested(self) -> None:
        """導航至資料庫管理頁面的 SPI 規格管理分頁。"""
        # nav_index 1 為「資料庫管理」
        self._on_nav_step_clicked(1)
        # 並切換至該頁的 Tab 3 (索引 2)
        library_page: MeasurementLibraryPage = self.pages["量測庫"]
        library_page.tabs.setCurrentIndex(2)

    def _sync_workorder_master_to_page(self):
        """Sync workorder_master fields from store to DataSetupPage."""
        from app.data.session_store import SessionStore
        store = SessionStore()
        data_page = self.pages["資料"]
        master = store.workorder_master or {}
        data_page.sync_from_store(master)

    def _sync_workorder_spec_to_page(self):
        """Consolidated UI: DataSetupPage already contains StencilSpecEditor; 
         MainWindow can directly call its sync logic if needed, but usually it
         refreshes based on product change.
        """
        pass

    def _current_data_loader_worker(self) -> Any | None:
        """Return ``self.worker`` only if the Qt C++ object is still alive; else clear stale ref and return None."""
        w = self.worker
        if w is None:
            return None
        if not Shiboken.isValid(w):
            self.worker = None
            return None
        return w

    def _start_data_loader_worker(self) -> None:
        """Start the currently selected data loader paths without blocking the UI thread."""
        from app.services.import_service import DataLoaderWorker

        self._loader_restart_queued = False
        self.worker = DataLoaderWorker(self.current_coord_path, self.current_meas_path)
        _lw = self.worker
        # Clear Python ref BEFORE other ``finished`` slots: if ``on_load_finished`` starts a nested loader,
        # we must not leave a stale wrapper after ``deleteLater`` (RuntimeError: Internal C++ object deleted).
        self.worker.finished.connect(
            lambda _ok, _msg, w=_lw: setattr(self, "worker", None) if self.worker is w else None
        )
        self.worker.progress_changed.connect(self._on_loader_progress)
        if hasattr(self.worker, "progress_value_changed"):
            self.worker.progress_value_changed.connect(self._on_loader_progress_value)
        self.worker.finished.connect(self.on_load_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def start_loading_worker(self, coord_path: str | None = None, meas_path: str | None = None) -> None:
        """Unified entry point for both DEMO and REAL data imports triggered by any UI sub-page."""
        
        # When user only uploads ONE file, we must keep the path of the previously uploaded OTHER file if it exists.
        if coord_path is not None:
             self.current_coord_path = coord_path
        if meas_path is not None:
             self.current_meas_path = meas_path
             
        # Also ensure we don't accidentally ask DataLoaderWorker to reload a blank path 
        # wiping out the singleton SessionStore unintentionally.
        # But actually, SessionStore holds df, maybe the DataLoaderWorker should NOT blank them out if path is empty.
             
        # MANDATORY: Cancel previous loader if user clicks re-import (Pass 145).
        prev_loader = self._current_data_loader_worker()
        if prev_loader is not None and prev_loader.isRunning():
            prev_loader.cancel()
            if not self._loader_restart_queued:
                self._loader_restart_queued = True
                with contextlib.suppress(TypeError, RuntimeError):
                    prev_loader.finished.connect(
                        lambda _ok, _msg: QTimer.singleShot(0, self._start_data_loader_worker)
                    )
            self.statusBar().showMessage("正在停止上一個載入作業…", 3000)
            return

        self._start_data_loader_worker()
        
    def on_load_finished(self, success: bool, msg: str) -> None:
        """Handle data-load completion: update UI state and trigger downstream analysis."""
        if not success and msg == "Cancelled":
            self.status_model.set_progress(-2)
            return
        from app.data.session_store import SessionStore
        store = SessionStore()
        # 補填量測資料庫的 row_count（上傳時尚未解析，現在才有實際筆數）
        sid = int(getattr(self, "_pending_meas_session_id", -1))
        if sid > 0:
            try:
                if success:
                    n_rows = 0
                    if store.meas_df is not None and not store.meas_df.empty:
                        n_rows = len(store.meas_df)
                    try:
                        from app.data.master_data_db import db_conn
                        with db_conn() as conn:
                            conn.execute(
                                "UPDATE measurement_sessions SET row_count = ? WHERE id = ?",
                                (n_rows, sid),
                            )
                        self.pages["量測庫"].refresh()
                    except (sqlite3.Error, OSError) as exc:
                        _log.warning(
                            "measurement_sessions row_count update failed (session_id=%s): %s",
                            sid,
                            exc,
                            exc_info=True,
                        )
            finally:
                self._pending_meas_session_id = -1
        if success:
            self.status_widget.update_connection_status(store.coord_meta, store.meas_meta, store.relation_meta)

            # Feed available distinct dropdown features (like BoardNo, RefDes)
            df_to_populate = store.get_analysis_df()
            self.control_panel.populate_conditions(df_to_populate)
            self.control_panel.populate_optional_filters(df_to_populate)
            self.control_panel.set_feature_section_visible(True)

            # Update 資料設定 page（無論資料是否為空，都要回寫 metadata 狀態）
            self.pages["資料"].update_meas_display(store.meas_df, store.meas_meta)
            self.pages["資料"].update_coord_display(store.coord_df, store.coord_meta)
            self.pages["資料"].refresh_stencil_refdes_list()

            # Sync workorder master from store to workorder page after load
            self._sync_workorder_master_to_page()
            # 依產品名稱載入時：若座標路徑變更則清空階梯指派；若有產品規格則帶入 store 並同步工單頁
            product_name = (store.workorder_master or {}).get("product_name") or ""
            if product_name:
                from app.data.stencil_assignment_registry import is_coord_path_changed, clear_by_product
                current_coord_path = (store.coord_meta or {}).get("filepath") or ""
                if is_coord_path_changed(product_name, current_coord_path):
                    clear_by_product(product_name)
                    self.statusBar().showMessage("座標已更新，請在資料設定頁重新指定階梯鋼板精密元件。", 5000)
                from app.services.spec_resolver import resolve_workorder_spec
                workorder_spec, _ = resolve_workorder_spec(product_name)
                if workorder_spec:
                    store.workorder_spec = workorder_spec
                    self._sync_workorder_spec_to_page()

            if self._pending_workorder_save_after_load:
                self._pending_workorder_save_after_load = False
                self._pending_workorder_style_after_refresh = True
                self.refresh_analysis()
                self.statusBar().showMessage("座標已載入，正在分析…", 3000)
            else:
                self.status_model.set_state(STATE_SUCCESS, "資料載入成功")
                self.statusBar().showMessage(
                    "資料載入成功。可前往「統計圖表」檢視結果，或到「資料庫」管理資料。",
                    4000,
                )
        else:
            self.status_widget.update_connection_status(store.coord_meta, store.meas_meta, store.relation_meta)
            if self._pending_workorder_save_after_load:
                self._pending_workorder_save_after_load = False
                self.statusBar().showMessage(f"座標載入失敗：{msg}", 8000)
            else:
                self.statusBar().showMessage(f"載入失敗：{msg}", 10000)
            self.status_model.set_state(STATE_ERROR, f"載入失敗：{msg}")
            
    def refresh_analysis(self) -> None:
        """Schedule immediate refresh (manual «立即重跑»). Sets refresh button to loading until result."""
        self._refresh_button_loading = True
        refresh_btn = self.control_panel.refresh_btn
        refresh_btn.setEnabled(False)
        refresh_btn.setText("計算中…")
        refresh_btn.setProperty("state", "loading")
        refresh_btn.style().unpolish(refresh_btn)
        refresh_btn.style().polish(refresh_btn)
        self._schedule_refresh_analysis(immediate=True)

    def _get_store(self):
        from app.data.session_store import SessionStore
        return SessionStore()

def run_app(splash: Optional[Any] = None) -> None:
    from app.bootstrap.dpi import setup_high_dpi
    setup_high_dpi()
    
    core_app = QApplication.instance()
    if not core_app:
        app = QApplication(sys.argv)
    else:
        app = cast(QApplication, core_app)
        
    from app.ui.theme import apply_app_theme
    from app.ui.debug.ui_runtime_diagnostics import log_ui_diagnostics, ui_diagnostics_enabled

    if splash:
        splash.set_progress(70, "正在配置介面視覺主題...")
        app.processEvents()

    bundled_families = register_qt_bundled_fonts()
    apply_app_theme(app)

    if splash:
        splash.set_progress(80, "正在套用字型設定與語系核心...")
        app.processEvents()

    # Keep Qt fallback consistent with bundled CJK fonts used by chart rendering.
    ui_font_family = preferred_qt_font_family()
    app.setFont(QFont(ui_font_family))
    if bundled_families:
        _log.info("Bundled Qt fonts registered: %s; selected_ui_font=%s", bundled_families, ui_font_family)
    else:
        _log.warning("No bundled Qt fonts detected; selected_ui_font=%s", ui_font_family)

    if splash:
        splash.set_progress(90, "正在建立主視窗與子頁面...")
        app.processEvents()

    window = MainWindow()
    
    if splash:
        splash.set_progress(100, "啟動完成！")
        app.processEvents()
        # 稍微停留一下，給使用者良好的視覺感受
        from PySide6.QtCore import QThread
        QThread.msleep(300)
        splash.finish(window)
        
    window.show()
    if ui_diagnostics_enabled():
        QTimer.singleShot(0, lambda: log_ui_diagnostics(window, reason="startup"))
    sys.exit(app.exec())
