"""
SPC 圖表頁：Dashboard 模式 — 圖表由上向下排列於捲動區，特徵複選，所有圖表同步更新。

重構說明：
- QStackedWidget → QScrollArea Dashboard（所有圖表上下堆疊，顯示/隱藏控制）
- 特徵按鈕：單選 → 複選（可同時選 高度/面積/體積）
- 特徵變動 → 所有可見圖表同步更新
- 多特徵並列時可啟用「標準化顯示」（% of median），方便跨量綱比較
"""
import contextlib
import logging
from types import SimpleNamespace
from typing import Optional, Any
from app.ui.state.app_status_model import AppStatusModel
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QCheckBox,
    QScrollArea,
    QSizePolicy,
    QButtonGroup,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtCore import QEvent

from app.analytics.chart_registry import (
    get_visual_charts_by_ui_group,
    resolve_chart_payload,
    format_chart_description,
    format_chart_description_compact,
    build_chart_interpretation_sections,
    is_chart_available_for_selection,
    get_chart_display_name,
    get_incompatible_reason,
    is_text_summary_chart,
    CHART_ORDER,
    CHART_UI_GROUPS_ORDER,
    CHART_UI_GROUP_BY_ID,
)
from app.data.session_store import SessionStore
from app.utils.constants import FILTER_ALL
from chart_router import ChartContext, get_condition_blocked_ids, ROUTER_TO_REGISTRY_ID
from app.ui.tabs.distribution_capability_tab import DistributionCapabilityTab
from app.ui.tabs.comparison_tab import ComparisonTab
from app.ui.tabs.spatial_tab import SpatialTab
from app.ui.tabs.pareto_tab import ParetoTab
from app.ui.tabs.normality_tab import NormalityTab
from app.ui.widgets.chart_only_page import ChartOnlyPage, DistCapPageWrapper
from app.ui.dialogs.interpretation_dialog import InterpretationDialog
from app.charts.scatter_spec_chart import ScatterSpecChart
from app.charts.quadrant_chart import QuadrantChart
from app.charts.bivariate_outlier_chart import BivariateOutlierChart
from app.charts.anomaly_3f_chart import Anomaly3FChart
from app.charts.consistency_3f_chart import Consistency3FChart
from app.charts.ewma_chart import EWMAChart
from app.charts.cusum_chart import CUSUMChart
from app.charts.run_chart import RunChart
from app.charts.xbar_r_chart import XbarRChart
from app.charts.subgroup_chart import SubgroupChart
from app.charts.repeated_offender_chart import RepeatedOffenderChart
from app.charts.density_chart import DensityChart
from app.charts.correlation_matrix_chart import CorrelationMatrixChart
from app.charts.correlation_heatmap_chart import CorrelationHeatmapChart
from app.charts.anova_parttype_chart import AnovaPartTypeChart
from app.charts.pattern_recognition_chart import PatternRecognitionChart
from app.charts.parallel_coord_chart import ParallelCoordChart
from app.charts.pass_fail_chart import PassFailChart
from app.charts.run_chart_3f_chart import RunChart3F
from app.charts.imr_3f_chart import IMR3F
from app.charts.ewma_3f_chart import EWMA3F
from app.charts.cusum_3f_chart import CUSUM3F
from app.charts.boxplot_chart import BoxplotChart
from app.ui.theme.tokens import (
    SPACING_4,
    SPACING_8,
    SPACING_SM,
    SPACING_16,
    CHART_MAIN_MIN_HEIGHT,
    CHART_SELECTOR_COMPACT_MAX_HEIGHT,
    CHART_SELECTOR_CONTENT_MARGIN,
    CHART_SELECTOR_GROUP_SPACING,
    CHART_SELECTOR_OPTION_COLUMNS,
    CHART_CARD_HEADER_BUTTON_HEIGHT,
    RECO_CHIP_STRIP_HEIGHT,
    chart_group_style_key,
)
from app.ui.widgets.page_templates import (
    empty_state_label,
    page_margins_and_spacing,
)
from app.ui.widgets.imr_histogram_split_page import ImrHistogramSplitPage
from app.viewmodels.chart_analysis_viewmodel import SUMMARY_MODE_MANAGER, SUMMARY_MODE_ENGINEER


def _catalog_by_id():
    """Return cached catalog by ID (from chart_registry module-level cache)."""
    from app.analytics.chart_registry import _CATALOG_BY_ID
    return _CATALOG_BY_ID


def _resolve_selection_override_ids(last_payload: dict, display_features: list[str]) -> tuple[set[str], set[str]]:
    """Return (dual_override_ids, triple_override_ids) for selector availability."""
    payload_selected = (last_payload or {}).get("selected_features") or []
    dual_override_ids: set[str] = set()
    triple_override_ids: set[str] = set()
    if len(payload_selected) != 1:
        return dual_override_ids, triple_override_ids

    # Distribution/capability + normality + boxplot charts are rendered in multi-feature mode
    # when payload["parameters"] contains per-feature results.
    # However chart_registry marks them as single-feature, so we override availability
    # for the "single-feature analysis -> user expands display to 2/3 features" workflow.
    params = (last_payload or {}).get("parameters")
    if isinstance(params, dict):
        if len(display_features) == 2:
            available = [f for f in display_features if f in params]
            if len(available) == 2:
                dual_override_ids |= {"histogram_spec", "normality", "boxplot"}
        elif len(display_features) == 3:
            available = [f for f in display_features if f in params]
            if len(available) == 3:
                triple_override_ids |= {"histogram_spec", "normality", "boxplot"}

    dual_params = (last_payload or {}).get("dual_parameters", {})
    if len(display_features) == 2 and dual_params:
        f0, f1 = display_features[0], display_features[1]
        if f"{f0}+{f1}" in dual_params or f"{f1}+{f0}" in dual_params:
            dual_override_ids |= {
                "scatter_spec",
                "quadrant",
                "bivariate_outlier",
                "density",
                "correlation_matrix",
                "correlation_heatmap",
            }

    triple_params = (last_payload or {}).get("triple_parameters", {})
    if len(display_features) == 3 and triple_params:
        triple_override_ids |= {
            "anomaly_3f", "consistency_3f", "parallel_coord", "pass_fail_matrix",
            "imr_3f", "run_chart_3f", "ewma_3f", "cusum_3f", "boxplot_3f",
        }
    return dual_override_ids, triple_override_ids


class _DetailsHintWorker(QThread):
    """Compute root-cause / anomaly / suggestions off the main thread."""
    result_ready = Signal(str)

    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self._payload = payload
        self._is_cancelled = False
        
    def cancel(self) -> None:
        """Request cancellation of the in-flight task."""
        self._is_cancelled = True

    def run(self) -> None:
        """Execute the background task."""
        try:
            if self._is_cancelled:
                return
            from app.analytics.root_cause_engine import infer_root_cause_hints
            from app.analytics.optimization_suggestions import get_optimization_suggestions
            from app.analytics.anomaly_classifier import classify_anomalies
        except (ImportError, TypeError, ValueError, KeyError) as e:
            logging.getLogger(__name__).debug("分析明細背景計算失敗 (Pass 6): %s", e)
            self.result_ready.emit("分析明細")
            return
        except (AttributeError, RuntimeError, OSError) as e:
            # Fallback for unexpected math/infra errors
            logging.getLogger(__name__).error("分析明細遇到非預期錯誤: %s", e, exc_info=True)
            self.result_ready.emit("分析明細 (計算錯誤)")
            return
        if not self._payload:
            self.result_ready.emit("分析明細")
            return
        hints = infer_root_cause_hints(self._payload)
        anomalies = classify_anomalies(self._payload)
        suggestions = get_optimization_suggestions(self._payload)
        parts: list[str] = []
        if hints:
            items = " / ".join((h.get("hint") or "") for h in hints[:3])
            parts.append(f"根因：{items}")
        if anomalies:
            items = " / ".join(
                f"{a.get('label', '')}" + (f"({a['confidence']:.0%})" if a.get("confidence") is not None else "")
                for a in anomalies[:3]
            )
            parts.append(f"異常：{items}")
        if suggestions:
            items = " / ".join((s.get("text") or "") for s in suggestions[:3])
            parts.append(f"建議：{items}")
        self.result_ready.emit("　｜　".join(parts) if parts else "分析明細")


class ChartAnalysisPage(QWidget):
    pareto_component_selected = Signal(str)
    summary_mode_changed = Signal(str)  # emitted when user toggles manager/engineer mode

    _LOGICAL_TO_COL = {"height": "Height", "area": "Area", "volume": "Volume"}

    _SINGLE_TO_TRIPLE_CHART_ID: dict[str, str] = {
        "imr": "imr_3f",
        "run_chart": "run_chart_3f",
        "ewma": "ewma_3f",
        "cusum": "cusum_3f",
        "boxplot": "boxplot_3f",
    }
    _FEATURE_TAB_COUNTS: tuple[int, int, int] = (1, 2, 3)
    _FEATURE_TAB_LABELS: dict[int, str] = {1: "單特徵", 2: "雙特徵", 3: "三特徵"}
    _FEATURE_TAB_BASE_MIN_WIDTH = 68
    _FEATURE_TAB_FIXED_HEIGHT = 41
    _FEATURE_TAB_EXTRA_BUFFER = SPACING_8
    _SELECTION_FEEDBACK_DURATION_MS = 900
    _MODE_STEP_TEXT = "顯示模式"
    _NORMALIZE_LABEL = "多特徵標準化"
    _STATUS_READY = "Ready"
    _STATUS_INCOMPATIBLE = "Incompatible"
    _STATUS_NODATA = "NoData"
    _STATUS_ERROR = "Error"
    _STATUS_DISPLAY_TEXT = {
        _STATUS_READY: "可顯示",
        _STATUS_INCOMPATIBLE: "不適用",
        _STATUS_NODATA: "無資料",
        _STATUS_ERROR: "錯誤",
    }
    _OPERATION_HINT_TEXT = "先選特徵與顯示模式，再勾選要檢視的圖表。"

    def __init__(self, parent=None, status_model: Optional[AppStatusModel] = None) -> None:
        super().__init__(parent)
        self._payload: dict[str, Any] = {}
        # Initialized early because __init__ calls _refresh_chart_selector(None),
        # which builds context from _last_payload.
        self._last_payload: dict[str, Any] = {}
        self._status_model = status_model
        self._is_cancelled = False
        self._chart_id_to_checkbox: dict[str, QCheckBox] = {}
        self._selected_chart_ids: list[str] = []
        # Remember which "single-feature chart family" the user was on (e.g. imr),
        # so we can switch to its *_3f counterpart when display features become 3.
        self._last_single_feature_chart_preference_ids: list[str] = []
        self._display_features: list[str] = []   # multi-select (replaces _display_feature)
        self._normalize_multi: bool = False
        self._active_feature_tab_count: int = 1
        self._autoswitch_reason: str = ""
        self._pending_autoswitch_reason: str = ""
        self._selection_feedback_text: str = ""
        self._selection_feedback_target: str = ""
        self._selection_feedback_timer = QTimer(self)
        self._selection_feedback_timer.setSingleShot(True)
        self._selection_feedback_timer.timeout.connect(self._clear_selection_feedback)
        self._render_status_by_chart: dict[str, dict[str, str]] = {}
        self._summary_mode = SUMMARY_MODE_MANAGER
        self._chart_catalog = _catalog_by_id()
        self._chart_widgets: dict[str, Optional[QWidget]] = {
            chart_id: None for chart_id in CHART_ORDER
        }  # chart_id → page widget, created on first visible use
        self._dashboard_cards: dict[str, QFrame] = {}     # chart_id → card frame
        self._card_interpret_buttons: dict[str, QPushButton] = {}
        self._card_status_labels: dict[str, QLabel] = {}  # chart_id → status label
        self._card_reason_labels: dict[str, QLabel] = {}  # chart_id → reason label
        self._accordion_panels: dict[str, tuple] = {}     # group_label → (header_btn, content_w, content_layout)
        self._feature_tab_buttons: dict[int, QPushButton] = {}
        self._details_label = QLabel("分析明細")
        self._details_label.setWordWrap(True)
        self._details_label.setProperty("class", "chartDetailsStrip")
        self._details_worker: Optional[Any] = None  # _DetailsHintWorker | None
        self._interpretation_dialog = InterpretationDialog(self)
        self._ui_state: dict[str, Any] = {
            "active_features": [],
            "selected_chart_ids": [],
            "autoswitch_reason": "",
            "feature_tab_count": self._active_feature_tab_count,
            "render_status": {},
        }

        layout = QVBoxLayout(self)
        page_margins_and_spacing(layout)

        # ── Top bar ──────────────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setProperty("class", "headerToolbar")
        top_bar.setProperty("headerRole", "utilityHeader")
        top_bar.setProperty("headerDensity", "compact")
        top_toolbar_layout = QVBoxLayout(top_bar)
        top_toolbar_layout.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
        top_toolbar_layout.setSpacing(0)

        # Tools row (single line, compact): 顯示模式 / 標準化顯示 / 單特徵 / 雙特徵 / 三特徵
        # Feature selection (高度/面積/體積) has moved to the left sidebar ControlPanel.
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(SPACING_8)

        self._mode_step_label = self._make_toolbar_step_label(self._MODE_STEP_TEXT)
        top_row.addWidget(self._mode_step_label)

        self.chk_normalize = QCheckBox(self._NORMALIZE_LABEL)
        self.chk_normalize.setMinimumHeight(self._FEATURE_TAB_FIXED_HEIGHT)
        self.chk_normalize.setToolTip("雙特徵/三特徵比較時，以 Z-score 對齊不同量綱")
        self.chk_normalize.setVisible(False)
        self.chk_normalize.toggled.connect(self._on_normalize_toggled)
        top_row.addWidget(self.chk_normalize)

        # ── Feature split tabs (單特徵 / 雙特徵 / 三特徵) ───────────────
        # Keep tabs in the same compact toolbar row to avoid a large middle gap.
        self.feature_tab_group = QButtonGroup(self)
        self.feature_tab_group.setExclusive(True)
        for count in self._FEATURE_TAB_COUNTS:
            label_text = self._FEATURE_TAB_LABELS.get(count, f"{count}F")
            btn = QPushButton(label_text)
            btn.setCheckable(True)
            btn.setProperty("class", "secondary")
            btn.setProperty("variant", "featureTab")
            # Enlarge by ~20%: height 34->41, font 10.5->13; width is computed dynamically.
            btn.setFixedHeight(self._FEATURE_TAB_FIXED_HEIGHT)
            btn.setToolTip(label_text)
            btn.clicked.connect(lambda _checked=False, c=count: self._on_feature_tab_clicked(c))
            self.feature_tab_group.addButton(btn)
            self._feature_tab_buttons[count] = btn
            top_row.addWidget(btn)
        top_row.addStretch(1)
        self._recompute_feature_tab_button_widths()

        top_toolbar_layout.addLayout(top_row)
        layout.addWidget(top_bar)


        # ── Chart group selector (四大分類橫排) ─────────────────────────
        self.accordion_area = QFrame()
        self.accordion_area.setObjectName("accordionArea")
        self.accordion_area.setProperty("layoutDensity", "compact")
        self.accordion_area.setMaximumHeight(CHART_SELECTOR_COMPACT_MAX_HEIGHT)
        accordion_outer = QHBoxLayout(self.accordion_area)
        accordion_outer.setContentsMargins(
            CHART_SELECTOR_CONTENT_MARGIN,
            CHART_SELECTOR_CONTENT_MARGIN,
            CHART_SELECTOR_CONTENT_MARGIN,
            CHART_SELECTOR_CONTENT_MARGIN,
        )
        accordion_outer.setSpacing(CHART_SELECTOR_GROUP_SPACING)

        for group_label in CHART_UI_GROUPS_ORDER:
            group_style_key = chart_group_style_key(group_label)
            group_frame = QFrame()
            group_frame.setObjectName("accordionGroup")
            group_frame.setProperty("chartGroup", group_style_key)
            group_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            group_vbox = QVBoxLayout(group_frame)
            group_vbox.setContentsMargins(0, 0, 0, 0)
            group_vbox.setSpacing(SPACING_4)

            header_btn = QPushButton(f"▾  {group_label}")
            header_btn.setCheckable(True)
            header_btn.setChecked(True)
            header_btn.setProperty("class", "accordionHeader")
            header_btn.setProperty("chartGroup", group_style_key)
            group_vbox.addWidget(header_btn)

            content_w = QWidget()
            content_layout = QGridLayout(content_w)
            content_layout.setContentsMargins(
                CHART_SELECTOR_CONTENT_MARGIN,
                CHART_SELECTOR_CONTENT_MARGIN,
                CHART_SELECTOR_CONTENT_MARGIN,
                CHART_SELECTOR_CONTENT_MARGIN,
            )
            content_layout.setHorizontalSpacing(SPACING_4)
            content_layout.setVerticalSpacing(SPACING_4)
            content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            for column in range(CHART_SELECTOR_OPTION_COLUMNS):
                content_layout.setColumnStretch(column, 1)
            group_vbox.addWidget(content_w)

            header_btn.toggled.connect(
                lambda checked, cw=content_w, btn=header_btn, gl=group_label:
                self._on_accordion_toggle(gl, checked, cw, btn)
            )
            self._accordion_panels[group_label] = (header_btn, content_w, content_layout)
            accordion_outer.addWidget(group_frame, stretch=1)

        layout.addWidget(self.accordion_area)

        # ── Recommendation Chip Strip ─────────────────────────────────
        reco_row = QHBoxLayout()
        reco_row.setContentsMargins(0, 0, 0, 0)
        reco_row.setSpacing(SPACING_8)
        self._reco_header = QLabel("建議查看")
        self._reco_header.setProperty("class", "statusIndicator")
        self._reco_header.setVisible(False)
        reco_row.addWidget(self._reco_header)
        self._reco_inner = QWidget()
        self._reco_layout = QHBoxLayout(self._reco_inner)
        self._reco_layout.setContentsMargins(0, 0, 0, 0)
        self._reco_layout.setSpacing(SPACING_4)
        self._reco_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._reco_scroll = QScrollArea()
        self._reco_scroll.setWidget(self._reco_inner)
        self._reco_scroll.setWidgetResizable(True)
        self._reco_scroll.setFixedHeight(RECO_CHIP_STRIP_HEIGHT)
        self._reco_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._reco_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._reco_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._reco_scroll.setVisible(False)
        reco_row.addWidget(self._reco_scroll, 1)
        layout.addLayout(reco_row)

        # ── Autoswitch Hint ──────────────────────────────────────────
        self._autoswitch_hint = QLabel("")
        self._autoswitch_hint.setWordWrap(True)
        self._autoswitch_hint.setProperty("class", "chartDetailsStrip")
        self._autoswitch_hint.setVisible(False)
        layout.addWidget(self._autoswitch_hint)

        # ── Operation Hint & Chart Context Strip ─────────────────────
        self._operation_hint = QLabel(self._OPERATION_HINT_TEXT)
        self._operation_hint.setWordWrap(True)
        self._operation_hint.setProperty("class", "chartDetailsStrip")
        self._operation_hint.setVisible(False)
        layout.addWidget(self._operation_hint)

        self._chart_context_strip = QLabel("")
        self._chart_context_strip.setWordWrap(True)
        self._chart_context_strip.setProperty("class", "chartDetailsStrip")
        self._chart_context_strip.setVisible(True)
        layout.addWidget(self._chart_context_strip)


        # ── Dashboard scroll area ─────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.dashboard_widget = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_widget)
        self.dashboard_layout.setContentsMargins(0, SPACING_8, 0, SPACING_8)
        self.dashboard_layout.setSpacing(SPACING_16)
        self.dashboard_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Standard empty state (Audit Item 33)
        self._empty_hint = empty_state_label("請選擇圖表")
        # Backward-compatible alias: older code references `_empty_label`.
        self._empty_label = self._empty_hint
        self.dashboard_layout.addWidget(self._empty_hint) # Added to dashboard_layout for correct placement
        self._empty_hint.setVisible(True)

        self.scroll_area.setWidget(self.dashboard_widget)
        layout.addWidget(self.scroll_area, 2)

        # ── Root cause panel ──────────────────────────────────────────
        self.root_cause_panel = SimpleNamespace(update_hints=self._update_details_hints)

        self.set_summary_mode(SUMMARY_MODE_ENGINEER)  # 統一使用完整工程模式
        self._sync_feature_tab_buttons()
        self._refresh_chart_selector(None)

    def cancel(self) -> None:
        """Request cancellation of the in-flight task."""
        self._is_cancelled = True

    def changeEvent(self, event: QEvent) -> None:
        """Recompute tab widths when font/style changes affect text metrics."""
        super().changeEvent(event)
        if event.type() in (
            QEvent.Type.FontChange,
            QEvent.Type.ApplicationFontChange,
            QEvent.Type.StyleChange,
        ):
            self._recompute_feature_tab_button_widths()

    def _recompute_feature_tab_button_widths(self) -> None:
        """Keep feature-tab buttons equal-width with DPI-safe minimum size."""
        if not self._feature_tab_buttons:
            return

        text_widths: list[int] = []
        for btn in self._feature_tab_buttons.values():
            btn.ensurePolished()
            text_widths.append(btn.fontMetrics().horizontalAdvance(btn.text()))
        max_text_width = max(text_widths, default=0)
        # Match secondary button horizontal padding (left+right) and add extra buffer
        # to avoid crowding under high DPI / enlarged fonts.
        required_width = max_text_width + (2 * SPACING_SM) + self._FEATURE_TAB_EXTRA_BUFFER
        target_width = max(self._FEATURE_TAB_BASE_MIN_WIDTH, required_width)

        for btn in self._feature_tab_buttons.values():
            btn.setMinimumWidth(target_width)
            btn.setFixedHeight(self._FEATURE_TAB_FIXED_HEIGHT)

    def _make_toolbar_step_label(self, text: str) -> QLabel:
        """Return a compact inline step label for the chart toolbar."""
        label = QLabel(text)
        label.setProperty("class", "statusIndicator")
        return label

    def _on_mode_clicked(self, mode: str) -> None:
        self.set_summary_mode(mode)
        self.summary_mode_changed.emit(mode)

    def set_summary_mode(self, mode: str) -> None:
        """Switch the chart summary display mode (e.g. table / chart / split)."""
        if mode not in (SUMMARY_MODE_MANAGER, SUMMARY_MODE_ENGINEER):
            return
        self._summary_mode = mode

    def get_ui_state_snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot of chart-page UI state."""
        return {
            "active_features": list(self._ui_state.get("active_features", [])),
            "selected_chart_ids": list(self._ui_state.get("selected_chart_ids", [])),
            "autoswitch_reason": str(self._ui_state.get("autoswitch_reason", "")),
            "feature_tab_count": int(self._ui_state.get("feature_tab_count", 1)),
            "render_status": dict(self._ui_state.get("render_status", {})),
        }

    def _sync_ui_state(self) -> None:
        active_features = list(self._get_active_tab_features())
        self._ui_state["active_features"] = active_features
        self._ui_state["selected_chart_ids"] = list(self._selected_chart_ids)
        self._ui_state["autoswitch_reason"] = self._autoswitch_reason
        self._ui_state["feature_tab_count"] = self._active_feature_tab_count
        self._ui_state["render_status"] = dict(self._render_status_by_chart)

        parts = []
        if not self._selected_chart_ids:
            parts.append(self._OPERATION_HINT_TEXT)
        if active_features:
            parts.append(" / ".join(active_features))
        
        mode_str = self._FEATURE_TAB_LABELS.get(self._active_feature_tab_count, f"{self._active_feature_tab_count}特徵")
        parts.append(f"顯示模式: {mode_str}")
        parts.append(f"已選圖表: {len(self._selected_chart_ids)} 張")
        
        if self._active_feature_tab_count == 1:
            norm_str = "待雙/三特徵模式"
        else:
            norm_str = "開啟" if self._normalize_multi else "關閉"
        parts.append(f"多特徵標準化: {norm_str}")
        
        batch = self._last_payload.get("_ctx_batch")
        if batch:
            parts.append(f"批次: {batch}")
            
        part_type = self._last_payload.get("_ctx_part_type")
        if part_type:
            parts.append(f"PartType: {part_type}")

        if self._selection_feedback_text:
            parts.append(f"更新: {self._selection_feedback_text}")
            
        self._chart_context_strip.setText(" | ".join(parts))

    def _restyle_widget(self, widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _set_interaction_state(self, widget: QWidget, active: bool) -> None:
        widget.setProperty("interactionState", "changed" if active else "")
        self._restyle_widget(widget)

    def _clear_selection_feedback(self) -> None:
        self._selection_feedback_text = ""
        self._selection_feedback_target = ""
        for widget in (
            self._mode_step_label,
            self._chart_context_strip,
        ):
            self._set_interaction_state(widget, False)
        self._sync_ui_state()

    def _show_selection_feedback(self, text: str, *, target: str) -> None:
        feedback = text.strip()
        if not feedback:
            return
        self._selection_feedback_text = feedback
        self._selection_feedback_target = target
        self._set_interaction_state(self._chart_context_strip, True)
        self._set_interaction_state(self._mode_step_label, target in ("feature", "mode"))
        self._sync_ui_state()
        self._selection_feedback_timer.start(self._SELECTION_FEEDBACK_DURATION_MS)

    def _feature_feedback_text(self, col: str) -> str:
        selected = " / ".join(self._display_features) or col
        mode_label = self._FEATURE_TAB_LABELS.get(
            self._active_feature_tab_count,
            f"{self._active_feature_tab_count}特徵",
        )
        return f"特徵 {selected}，{mode_label}"

    def _mode_feedback_text(self) -> str:
        mode_label = self._FEATURE_TAB_LABELS.get(
            self._active_feature_tab_count,
            f"{self._active_feature_tab_count}特徵",
        )
        return f"顯示模式 {mode_label}"

    def _normalization_feedback_text(self) -> str:
        state = "開啟" if self._normalize_multi else "關閉"
        return f"標準化 {state}"

    def _chart_feedback_text(self, chart_id: str, checked: bool) -> str:
        action = "加入" if checked else "移除"
        chart_name = get_chart_display_name(chart_id, lang="zh_only")
        return f"圖表{action} {chart_name}"

    def _selector_features_for_current_state(self) -> list[str]:
        """Return the feature slice that should drive selector availability."""
        active = self._get_active_tab_features()
        if active:
            return active
        return list((self._last_payload or {}).get("selected_features") or [])

    def _sync_selection_ui(self, *, rebuild_selector: bool) -> None:
        """Synchronize chart-page selection controls, cards, and context text."""
        self._sync_normalize_visibility()
        self._sync_feature_tab_buttons()
        if rebuild_selector:
            self._refresh_chart_selector(self._selector_features_for_current_state())
            return
        self._refresh_card_visibility()
        if self._last_payload:
            self._update_all_dashboard_charts()
        else:
            self._sync_ui_state()

    def _sync_feature_tab_buttons(self) -> None:
        available_count = max(1, min(3, len(self._display_features) if self._display_features else 1))
        for count, btn in self._feature_tab_buttons.items():
            btn.blockSignals(True)
            try:
                btn.setEnabled(count <= available_count)
                btn.setChecked(count == self._active_feature_tab_count)
            finally:
                btn.blockSignals(False)

    def _set_active_feature_tab(
        self,
        count: int,
        *,
        refresh_selector: bool,
    ) -> None:
        available_count = max(1, min(3, len(self._display_features) if self._display_features else 1))
        safe_count = min(max(1, count), available_count)
        if safe_count == self._active_feature_tab_count and not refresh_selector:
            self._sync_feature_tab_buttons()
            self._sync_ui_state()
            return
        self._active_feature_tab_count = safe_count
        self._sync_selection_ui(rebuild_selector=refresh_selector)

    def _on_feature_tab_clicked(self, count: int) -> None:
        previous_count = self._active_feature_tab_count
        self._set_active_feature_tab(count, refresh_selector=True)
        if self._active_feature_tab_count != previous_count:
            self._show_selection_feedback(self._mode_feedback_text(), target="mode")

    def _get_active_tab_features(self) -> list[str]:
        source = self._display_features or list((self._last_payload or {}).get("selected_features") or [])
        if not source:
            return []
        if self._active_feature_tab_count <= 1:
            return [source[0]]
        return list(source[: self._active_feature_tab_count])

    def _set_autoswitch_reason(self, text: str) -> None:
        self._autoswitch_reason = text.strip()
        self._autoswitch_hint.setText(self._autoswitch_reason)
        self._autoswitch_hint.setVisible(bool(self._autoswitch_reason))
        self._sync_ui_state()

    def _build_autoswitch_reason(self, from_ids: list[str], to_id: str, selected_features: list[str]) -> str:
        if not from_ids or not to_id:
            return ""
        from_name = get_chart_display_name(from_ids[0], lang="zh_only")
        to_name = get_chart_display_name(to_id, lang="zh_only")
        mode_label = self._FEATURE_TAB_LABELS.get(len(selected_features), f"{len(selected_features)}F")
        reason = get_incompatible_reason(from_ids[0], selected_features or []) or "特徵組合切換造成不相容"
        return (
            f"已依顯示模式自動改選：{from_name} -> {to_name}。"
            f"原因：目前為{mode_label}，{reason}"
        )

    def _is_nodata_error(self, message: str) -> bool:
        if not message:
            return True
        lowered = message.lower()
        zh_markers = ("無", "缺", "不足", "至少")
        en_markers = ("empty", "no data", "not enough", "missing")
        return any(token in message for token in zh_markers) or any(token in lowered for token in en_markers)

    def _classify_render_status(self, chart_id: str, data: dict, active_features: list[str]) -> tuple[str, str]:
        meta = (data or {}).get("metadata", {}) if isinstance(data, dict) else {}
        is_enabled = chart_id in self._chart_id_to_checkbox and self._chart_id_to_checkbox[chart_id].isEnabled()
        if not is_enabled:
            reason = get_incompatible_reason(chart_id, active_features) or "目前特徵組合不相容。"
            return self._STATUS_INCOMPATIBLE, reason
        if bool(meta.get("is_valid", False)):
            return self._STATUS_READY, ""
        err = str(meta.get("error", "") or "").strip()
        if bool(meta.get("incompatible", False)):
            return self._STATUS_INCOMPATIBLE, err or "特徵不相容"
        if self._is_nodata_error(err):
            return self._STATUS_NODATA, err or "資料不足。"
        return self._STATUS_ERROR, err or "渲染失敗。"

    def _apply_card_render_status(self, chart_id: str, status: str, reason: str) -> None:
        status_lbl = self._card_status_labels.get(chart_id)
        reason_lbl = self._card_reason_labels.get(chart_id)
        if status_lbl is not None:
            status_lbl.setText(self._STATUS_DISPLAY_TEXT.get(status, status))
            status_lbl.setProperty("state", status.lower())
            status_lbl.style().unpolish(status_lbl)
            status_lbl.style().polish(status_lbl)
        if reason_lbl is not None:
            reason_lbl.setText(reason)
            reason_lbl.setVisible(bool(reason))

    def _refresh_card_visibility(self) -> None:
        for chart_id, cb in self._chart_id_to_checkbox.items():
            if cb is not None and cb.isChecked():
                self._ensure_dashboard_card(chart_id)
        for chart_id, card in self._dashboard_cards.items():
            checkbox = self._chart_id_to_checkbox.get(chart_id)
            card.setVisible(checkbox is not None and checkbox.isChecked())
        self._update_empty_state()
        self._sync_ui_state()

    # ── Dashboard card ────────────────────────────────────────────────

    def _make_dashboard_card(self, chart_id: str, page: QWidget) -> QFrame:
        """Wrap a chart page in a fixed-height card frame for the dashboard."""
        card = QFrame()
        card.setObjectName("chartDashboardCard")
        card.setProperty("class", "accentBlue")
        card.setProperty("chartId", chart_id)
        card.setProperty("chartGroup", chart_group_style_key(CHART_UI_GROUP_BY_ID.get(chart_id, "")))
        card.setMinimumHeight(CHART_MAIN_MIN_HEIGHT)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(SPACING_4, SPACING_4, SPACING_4, SPACING_4)
        card_layout.setSpacing(SPACING_4)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        chart_title = QLabel(get_chart_display_name(chart_id, lang="zh_only"))
        chart_title.setProperty("class", "caption")
        header_row.addWidget(chart_title)
        header_row.addStretch()
        interpret_btn = QPushButton("解讀")
        interpret_btn.setProperty("class", "secondary")
        interpret_btn.setProperty("variant", "chartCardAction")
        interpret_btn.setFixedHeight(CHART_CARD_HEADER_BUTTON_HEIGHT)
        interpret_btn.setToolTip("開啟圖表解讀：用途、公式、資料來源與 SMT 判讀")
        interpret_btn.clicked.connect(lambda _checked=False, cid=chart_id: self._open_chart_interpretation(cid))
        self._card_interpret_buttons[chart_id] = interpret_btn
        header_row.addWidget(interpret_btn)
        status_lbl = QLabel(self._STATUS_DISPLAY_TEXT[self._STATUS_READY])
        status_lbl.setProperty("class", "chartCardStatus")
        status_lbl.setProperty("state", self._STATUS_READY.lower())
        header_row.addWidget(status_lbl)
        card_layout.addLayout(header_row)
        reason_lbl = QLabel("")
        reason_lbl.setProperty("class", "caption")
        reason_lbl.setWordWrap(True)
        reason_lbl.setVisible(False)
        card_layout.addWidget(reason_lbl)
        card_layout.addWidget(page)
        self._card_status_labels[chart_id] = status_lbl
        self._card_reason_labels[chart_id] = reason_lbl
        return card

    def _ensure_dashboard_card(self, chart_id: str) -> Optional[QFrame]:
        """Create the chart page/card only when the chart becomes visible."""
        existing = self._dashboard_cards.get(chart_id)
        if existing is not None:
            return existing
        page = self._make_page(chart_id, self._chart_catalog.get(chart_id, {}))
        card = self._make_dashboard_card(chart_id, page)
        card.setVisible(False)
        self.dashboard_layout.addWidget(card)
        self._chart_widgets[chart_id] = page
        self._dashboard_cards[chart_id] = card
        return card

    def _open_chart_interpretation(self, chart_id: str) -> None:
        """Open full chart interpretation dialog for the selected chart card."""
        active_features = self._get_active_tab_features()
        if not active_features:
            active_features = list((self._last_payload or {}).get("selected_features") or [])

        is_incompatible = not is_chart_available_for_selection(chart_id, active_features)
        context = {
            "target_col": active_features[0] if len(active_features) == 1 else None,
            "selected_features": active_features if len(active_features) > 1 else None,
            "is_incompatible": is_incompatible,
        }

        status = self._render_status_by_chart.get(chart_id, {}).get("status", "")
        reason = self._render_status_by_chart.get(chart_id, {}).get("reason", "")
        if not status:
            if is_incompatible:
                status = self._STATUS_INCOMPATIBLE
                reason = get_incompatible_reason(chart_id, active_features) or ""
            elif not self._last_payload:
                status = self._STATUS_NODATA
                reason = "尚未執行分析，僅顯示解讀框架。"
            else:
                status = self._STATUS_READY
                reason = ""

        sections = build_chart_interpretation_sections(
            chart_id,
            context=context,
            render_status={"status": status, "reason": reason},
        )
        sections_for_dialog: list[dict[str, Any]] = [dict(section) for section in sections]
        # Inject live chart screenshot into 圖表用途 section (first section)
        chart_widget = self._chart_widgets.get(chart_id)
        if chart_widget is not None and sections_for_dialog:
            px = chart_widget.grab()
            if not px.isNull():
                sections_for_dialog[0]["illustration_pixmap"] = px
                sections_for_dialog[0].pop("illustration", None)
        chart_name = get_chart_display_name(chart_id, lang="zh_only")
        context_lines = [
            "互動模式：預設隱藏說明，按鈕開啟完整解讀視窗。",
        ]
        self._interpretation_dialog.open_for_chart(
            chart_name=chart_name,
            sections=sections_for_dialog,
            context_lines=context_lines,
        )

    # ── Accordion toggle ──────────────────────────────────────────────

    def _on_accordion_toggle(self, group_label: str, checked: bool, content_w: QWidget, btn: QPushButton) -> None:
        content_w.setVisible(checked)
        btn.setText(f"{'▾' if checked else '▸'}  {group_label}")

    # ── Feature display-only fast path ───────────────────────────────
    # Physical buttons moved to sidebar (trigger re-analysis); this method handles
    # the display-only optimization when the feature is already in the payload.

    def _on_feature_shortcut_clicked(self, logical_name: str) -> None:
        """Toggle feature in/out of _display_features without re-analysis.
        Only acts when the feature is already computed in the current payload.
        Sidebar buttons handle the analysis-level toggle via MainWindow."""
        col = self._LOGICAL_TO_COL.get(logical_name)
        parameters = (self._last_payload or {}).get("parameters")
        if not parameters or not col or col not in parameters:
            return
        if col in self._display_features:
            if len(self._display_features) <= 1:
                return  # Keep at least one; no button to re-check (buttons live in sidebar)
            self._display_features.remove(col)
        else:
            self._display_features.append(col)
        if len(self._display_features) == 3:
            source_ids = self._last_single_feature_chart_preference_ids or self._selected_chart_ids
            if source_ids:
                mapped: list[str] = []
                for cid in source_ids:
                    mapped.append(self._SINGLE_TO_TRIPLE_CHART_ID.get(cid, cid))
                seen: set[str] = set()
                deduped: list[str] = []
                for x in mapped:
                    if x in seen:
                        continue
                    seen.add(x)
                    deduped.append(x)
                if deduped and deduped != source_ids:
                    self._pending_autoswitch_reason = self._build_autoswitch_reason(
                        source_ids,
                        deduped[0],
                        self._display_features,
                    )
                self._selected_chart_ids = deduped
        self._set_active_feature_tab(len(self._display_features), refresh_selector=True)
        self._show_selection_feedback(self._feature_feedback_text(col), target="feature")

    def _on_normalize_toggled(self, checked: bool) -> None:
        self._normalize_multi = checked
        self._sync_selection_ui(rebuild_selector=False)
        self._show_selection_feedback(self._normalization_feedback_text(), target="mode")

    def _sync_normalize_visibility(self) -> None:
        self.chk_normalize.setVisible(len(self._display_features) > 1)

    # ── Dashboard card visibility ─────────────────────────────────────

    def _apply_selection_and_show_first(self) -> None:
        self._selected_chart_ids = [cid for cid, cb in self._chart_id_to_checkbox.items() if cb.isChecked()]

        # Update preference only when we're in single-display mode.
        # This lets the *_3f auto-switch follow the user's last process-monitoring intention.
        if len(self._display_features) == 1:
            for cid in self._selected_chart_ids:
                if cid in self._SINGLE_TO_TRIPLE_CHART_ID:
                    self._last_single_feature_chart_preference_ids = [cid]
                    break

        self._sync_selection_ui(rebuild_selector=False)

    def _update_empty_state(self) -> None:
        has_visible = any(not card.isHidden() for card in self._dashboard_cards.values())
        self._empty_label.setVisible(not has_visible)

    # ── Checkbox handler ──────────────────────────────────────────────

    def _make_checkbox_handler(self, chart_id: str):
        def _on_toggled(checked: bool) -> None:
            self._set_autoswitch_reason("")
            self._selected_chart_ids = [
                cid for cid, cb in self._chart_id_to_checkbox.items() if cb.isChecked()
            ]
            if checked and len(self._display_features) == 1 and chart_id in self._SINGLE_TO_TRIPLE_CHART_ID:
                self._last_single_feature_chart_preference_ids = [chart_id]
            self._sync_selection_ui(rebuild_selector=False)
            self._show_selection_feedback(self._chart_feedback_text(chart_id, checked), target="chart")
        return _on_toggled

    # ── Chart selector rebuild ────────────────────────────────────────

    def _build_chart_context(self, selected_features: list | None) -> ChartContext:
        store = SessionStore()
        batch = (self._last_payload or {}).get("_ctx_batch", "")
        part_type = (self._last_payload or {}).get("_ctx_part_type", "")
        return ChartContext(
            meas_loaded=store.meas_df is not None and not store.meas_df.empty,
            mapping_done=bool((store.meas_meta or {}).get("is_valid", False)),
            coord_loaded=bool((store.relation_meta or {}).get("can_do_spatial", False)),
            has_batch=bool(batch and batch != FILTER_ALL),
            has_component_type=bool(part_type and part_type != FILTER_ALL),
            n_selected=len(selected_features) if selected_features else 0,
        )

    def _refresh_chart_selector(self, selected_features: list | None) -> None:
        prev_selected = list(self._selected_chart_ids)
        # Clear stale autoswitch hint on every rebuild; end of method may set a fresh reason.
        self._set_autoswitch_reason("")
        for cb in self._chart_id_to_checkbox.values():
            cb.setParent(None)
            with contextlib.suppress(TypeError, RuntimeError):
                cb.toggled.disconnect()
        self._chart_id_to_checkbox.clear()

        # Clear each accordion panel's content (supports both VBox and Grid layouts)
        for _hdr, _cw, cl in self._accordion_panels.values():
            while cl.count():
                item = cl.takeAt(0)
                w = item.widget() if item else None
                if w is not None:
                    w.setParent(None)

        ctx = self._build_chart_context(selected_features)
        condition_blocked_registry: frozenset[str] = frozenset(
            ROUTER_TO_REGISTRY_ID.get(k, k) for k in get_condition_blocked_ids(ctx)
        )
        grouped = get_visual_charts_by_ui_group(selected_features)

        # Fetch badge states from recommendation presenter
        from app.analytics.chart_recommendation_presenter import get_chart_recommendations
        _reco = get_chart_recommendations(self._last_payload or {}, self._display_features)
        _chart_status = _reco.get("chart_status") or {}

        # For n=1 analysis with precomputed dual/triple data, override availability
        # so that selecting 2 or 3 display features enables the corresponding charts.
        _dual_override_ids, _triple_override_ids = _resolve_selection_override_ids(
            self._last_payload or {}, self._display_features
        )

        for group_label in CHART_UI_GROUPS_ORDER:
            if group_label not in self._accordion_panels:
                continue
            _hdr, _cw, content_layout = self._accordion_panels[group_label]
            option_index = 0
            for item in grouped.get(group_label, []):
                chart_id = item["id"]
                if chart_id in condition_blocked_registry:
                    continue
                if chart_id in _dual_override_ids or chart_id in _triple_override_ids:
                    available = True
                    reason = ""
                else:
                    available = item.get("available", True)
                    reason = item.get("incompatible_reason", "")
                short_name = item.get("short_name", chart_id)
                badge = _chart_status.get(chart_id, "")
                display_name = f"★ {short_name}" if badge == "recommended" else short_name
                cb = QCheckBox(display_name)
                cb.setProperty("dataChartId", chart_id)
                cb.setProperty("chartGroup", chart_group_style_key(group_label))
                if not available:
                    cb.setEnabled(False)
                    cb.setProperty("state", "incompatible")
                    cb.setToolTip(f"目前不適用：{reason}" if reason else "請在元件/量測選定頁調整特徵數。")
                else:
                    cb.setProperty("state", badge)
                    base_tip = item.get("name", "")
                    if badge == "recommended":
                        base_tip = f"[建議] {base_tip}"
                    elif badge == "insufficient_data":
                        base_tip = f"[資料不足] {base_tip}"
                    cb.setToolTip(base_tip)
                cb.toggled.connect(self._make_checkbox_handler(chart_id))
                self._chart_id_to_checkbox[chart_id] = cb
                row = option_index // CHART_SELECTOR_OPTION_COLUMNS
                column = option_index % CHART_SELECTOR_OPTION_COLUMNS
                content_layout.addWidget(cb, row, column)
                option_index += 1

        restored = [
            cid
            for cid in prev_selected
            if cid in self._chart_id_to_checkbox and self._chart_id_to_checkbox[cid].isEnabled()
        ]
        first_available = next(
            (cid for cid, cb in self._chart_id_to_checkbox.items() if cb.isEnabled()),
            None,
        )
        if not restored and first_available:
            restored = [first_available]

        for cid in restored:
            checkbox = self._chart_id_to_checkbox.get(cid)
            if checkbox is None:
                continue
            checkbox.blockSignals(True)
            try:
                checkbox.setChecked(True)
            finally:
                checkbox.blockSignals(False)

        autoswitch_text = ""
        if self._pending_autoswitch_reason:
            autoswitch_text = self._pending_autoswitch_reason
        elif prev_selected and restored:
            dropped = [cid for cid in prev_selected if cid not in restored]
            if dropped:
                autoswitch_text = self._build_autoswitch_reason(dropped, restored[0], selected_features or [])
        self._pending_autoswitch_reason = ""
        if autoswitch_text:
            self._set_autoswitch_reason(autoswitch_text)
        self._apply_selection_and_show_first()

    # ── Chart page factory ────────────────────────────────────────────

    def _make_page(self, chart_id: str, entry: dict) -> QWidget:
        desc = format_chart_description_compact(chart_id)
        if chart_id == "imr":
            return ImrHistogramSplitPage(self)
        if chart_id == "xbar_r":
            return ChartOnlyPage(XbarRChart(self), desc, self)
        if chart_id == "run_chart":
            return ChartOnlyPage(RunChart(self), desc, self)
        if chart_id == "subgroup":
            return ChartOnlyPage(SubgroupChart(self), desc, self)
        if chart_id == "repeated_offender":
            return ChartOnlyPage(RepeatedOffenderChart(self), desc, self)
        if chart_id == "histogram_spec":
            return DistCapPageWrapper(DistributionCapabilityTab(self), self)
        if chart_id == "boxplot":
            return ComparisonTab(self)
        if chart_id == "normality":
            return NormalityTab(self)
        if chart_id == "spatial_heatmap":
            return SpatialTab(self)
        if chart_id == "pareto":
            tab = ParetoTab(self)
            tab.component_selected.connect(self.pareto_component_selected.emit)
            return tab
        if chart_id == "ewma":
            return ChartOnlyPage(EWMAChart(self), desc, self)
        if chart_id == "cusum":
            return ChartOnlyPage(CUSUMChart(self), desc, self)
        if chart_id == "scatter_spec":
            return ChartOnlyPage(ScatterSpecChart(self), desc, self)
        if chart_id == "correlation_matrix":
            return ChartOnlyPage(CorrelationMatrixChart(self), desc, self)
        if chart_id == "correlation_heatmap":
            return ChartOnlyPage(CorrelationHeatmapChart(self), desc, self)
        if chart_id == "anova_parttype":
            return ChartOnlyPage(AnovaPartTypeChart(self), desc, self)
        if chart_id == "quadrant":
            return ChartOnlyPage(QuadrantChart(self), desc, self)
        if chart_id == "bivariate_outlier":
            return ChartOnlyPage(BivariateOutlierChart(self), desc, self)
        if chart_id == "density":
            return ChartOnlyPage(DensityChart(self), desc, self)
        if chart_id == "pattern_recognition":
            return ChartOnlyPage(PatternRecognitionChart(self), desc, self)
        if chart_id == "anomaly_3f":
            return ChartOnlyPage(Anomaly3FChart(self), desc, self)
        if chart_id == "consistency_3f":
            return ChartOnlyPage(Consistency3FChart(self), desc, self)
        if chart_id == "parallel_coord":
            return ChartOnlyPage(ParallelCoordChart(self), desc, self)
        if chart_id == "pass_fail_matrix":
            return ChartOnlyPage(PassFailChart(self), desc, self)
        if chart_id == "run_chart_3f":
            return ChartOnlyPage(RunChart3F(self), desc, self)
        if chart_id == "imr_3f":
            return ChartOnlyPage(IMR3F(self), desc, self)
        if chart_id == "ewma_3f":
            return ChartOnlyPage(EWMA3F(self), desc, self)
        if chart_id == "cusum_3f":
            return ChartOnlyPage(CUSUM3F(self), desc, self)
        if chart_id == "boxplot_3f":
            return ChartOnlyPage(BoxplotChart(self), desc, self)
        return QWidget()

    # ── Data resolution ───────────────────────────────────────────────

    def _resolve_multi_feature_data(self, chart_id: str, features: list[str]) -> dict:
        """Return chart data from shared UI/report resolver."""
        return resolve_chart_payload(
            self._last_payload,
            chart_id,
            features=features,
            normalized=self._normalize_multi,
            context="ui",
        )

    # ── Dashboard broadcast ───────────────────────────────────────────

    def _update_all_dashboard_charts(self) -> None:
        """Push fresh data to every currently visible chart widget."""
        if not self._last_payload:
            return
        active_features = self._get_active_tab_features()
        render_status: dict[str, dict[str, str]] = {}
        for chart_id, card in self._dashboard_cards.items():
            if not card.isVisible():
                continue
            page = self._chart_widgets.get(chart_id)
            if page is None or not hasattr(page, "update_data"):
                continue
            data = self._resolve_multi_feature_data(chart_id, active_features)
            try:
                page.update_data(data)
            except (AttributeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
                logging.getLogger(__name__).error("Dashboard update_data failed for %s: %s", chart_id, exc, exc_info=True)
                data = {
                    "metadata": {
                        "is_valid": False,
                        "error": str(exc),
                    }
                }
            status, reason = self._classify_render_status(chart_id, data, active_features)
            self._apply_card_render_status(chart_id, status, reason)
            render_status[chart_id] = {"status": status, "reason": reason}
            # Sync description label for pages that support it
            if hasattr(page, "update_description"):
                selected = self._last_payload.get("selected_features") or []
                ctx = {
                    "target_col": None if len(active_features) != 1 else active_features[0],
                    "selected_features": active_features if len(active_features) > 1 else selected,
                    "is_incompatible": not is_chart_available_for_selection(chart_id, active_features),
                }
                page.update_description(format_chart_description_compact(chart_id, ctx))
                if hasattr(page, "set_full_description"):
                    page.set_full_description(format_chart_description(chart_id, ctx))
        self._render_status_by_chart = render_status
        self._sync_ui_state()

    # ── Public entry point (called by ViewModel) ──────────────────────

    def update_all_charts(self, payload: dict) -> None:
        """Refresh all chart panels with the current session data."""
        self._payload = payload or {}
        self._last_payload = payload or {}

        # Initialise or validate _display_features from payload
        params = self._last_payload.get("parameters", {})
        payload_selected = self._last_payload.get("selected_features") or []
        dist_ctx = (self._last_payload.get("dist") or {}).get("analysis_context", {})
        new_col = dist_ctx.get("target_col") if isinstance(dist_ctx, dict) else None

        if not params:
            # n>=2: no per-feature parameters dict — mirror the analysis selection exactly
            self._display_features = list(payload_selected)
        elif not self._display_features:
            # n==1, first init: start with analyzed feature(s) present in params
            avail = [f for f in payload_selected if f in params]
            self._display_features = avail or ([new_col] if new_col else [])
        else:
            # n==1, update: retain current display features still in params; add newly analyzed
            retained = [f for f in self._display_features if f in params]
            added = [f for f in payload_selected if f in params and f not in retained]
            self._display_features = retained + added
            if not self._display_features:
                self._display_features = [new_col] if new_col else []

        # Selector availability should follow the current display feature count.
        # This avoids keeping單特徵圖被勾選（或顯示舊的資料切片）
        # when user has toggled multiple display features via shortcuts.
        self._set_active_feature_tab(len(self._display_features) or 1, refresh_selector=True)
        self._refresh_recommendation_strip(payload)
        self._update_details_hints(payload)

    # ── Recommendation strip ──────────────────────────────────────────

    def _refresh_recommendation_strip(self, payload: dict) -> None:
        """Rebuild the 'Recommended Charts' chip strip from diagnostic_evidence_matrix."""
        from app.analytics.chart_recommendation_presenter import get_chart_recommendations

        # Remove old chips
        while self._reco_layout.count():
            item = self._reco_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.setParent(None)

        reco = get_chart_recommendations(payload or {}, self._display_features)
        chip_groups = reco.get("chip_groups") or []

        chips_added = 0
        for group in chip_groups:
            flabel = group.get("feature_label") or ""
            feature_set = group.get("feature_set") or []
            for entry in group.get("chart_entries") or []:
                chart_id = str(entry.get("chart_id") or "")
                chart_name = str(entry.get("chart_name") or chart_id)
                severity = str(entry.get("severity") or "info")
                metric = str(entry.get("metric_snapshot") or "")
                if not chart_id or is_text_summary_chart(chart_id):
                    continue
                label = f"{flabel} → {chart_name}" if flabel else chart_name
                btn = QPushButton(label)
                btn.setProperty("class", "recoChip")
                btn.setProperty("severity", severity)
                tooltip = metric if metric and metric != "—" else chart_name
                btn.setToolTip(tooltip)
                btn.clicked.connect(
                    lambda _checked=False, cid=chart_id, fs=list(feature_set):
                        self._on_reco_chip_clicked(cid, fs)
                )
                self._reco_layout.addWidget(btn)
                chips_added += 1

        visible = chips_added > 0
        self._reco_header.setVisible(visible)
        self._reco_scroll.setVisible(visible)

    def _on_reco_chip_clicked(self, chart_id: str, feature_set: list) -> None:
        """Check the chart checkbox and scroll dashboard to the chart card."""
        cb = self._chart_id_to_checkbox.get(chart_id)
        if cb is not None and cb.isEnabled():
            if not cb.isChecked():
                cb.setChecked(True)
            # Scroll to the dashboard card
            card = self._ensure_dashboard_card(chart_id)
            if card is not None and card.isVisible():
                self.scroll_area.ensureWidgetVisible(card)
        elif cb is None or not cb.isEnabled():
            # Chart may not be in current selector (e.g. feature mismatch) — just scroll if visible
            card = self._dashboard_cards.get(chart_id)
            if card is not None and card.isVisible():
                self.scroll_area.ensureWidgetVisible(card)

    def select_recommended_charts(self, chart_ids: list, feature_set: list) -> None:
        """Public: navigate to chart page chart(s); used by MainWindow for cross-page nav."""
        first_visible_checked = False
        for chart_id in chart_ids:
            cb = self._chart_id_to_checkbox.get(chart_id)
            if cb is not None and cb.isEnabled():
                if not cb.isChecked():
                    cb.setChecked(True)
                if not first_visible_checked:
                    card = self._ensure_dashboard_card(chart_id)
                    if card is not None:
                        card.setVisible(True)
                        self.scroll_area.ensureWidgetVisible(card)
                    first_visible_checked = True

    # ── Background hints ──────────────────────────────────────────────

    def _update_details_hints(self, payload: dict) -> None:
        if not payload:
            self._details_label.setText("分析明細")
            return
        self._details_label.setText("分析明細（計算中…）")
        
        # Cancel previous hint worker; guard isRunning() against deleteLater use-after-free.
        if self._details_worker is not None:
            try:
                if self._details_worker.isRunning():
                    self._details_worker.cancel()
                    self._details_worker.wait(500)
            except RuntimeError:
                self._details_worker = None

        self._details_worker = _DetailsHintWorker(payload, self)
        self._details_worker.result_ready.connect(self._details_label.setText)
        _w = self._details_worker
        self._details_worker.finished.connect(
            lambda w=_w: setattr(self, "_details_worker", None)
            if self._details_worker is w else None
        )
        self._details_worker.finished.connect(self._details_worker.deleteLater)
        self._details_worker.start()
