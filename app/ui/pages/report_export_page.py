from typing import Optional, TYPE_CHECKING, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QFrame,
    QCheckBox,
    QApplication,
    QDialog,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QShowEvent
from app.data.session_store import SessionStore
from app.utils.constants import FEATURE_DISPLAY_NAMES
from app.ui.widgets.page_templates import page_margins_and_spacing, create_status_lamp
from app.ui.theme.tokens import (
    SPACING_XXS,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    PAGE_HEADER_BOTTOM_SPACING,
    GROUP_ACTION_BUTTON_HEIGHT,
    chart_group_style_key,
)
from app.analytics.chart_registry import (
    CHART_ORDER, get_chart_display_name,
    is_chart_available_for_selection, get_incompatible_reason,
    CHART_UI_GROUPS_ORDER, CHART_UI_GROUP_BY_ID,
    TEXT_SUMMARY_GROUP_LABEL, is_text_summary_chart,
)
from app.services.report_service import ENGINEERING_DEFAULT_CHART_IDS, TEMPLATE_ENGINEERING

if TYPE_CHECKING:
    from app.ui.state.app_status_model import AppStatusModel

# 與圖表分析頁保持一致；文字摘要在報告選擇器中獨立成「統計資料」分組。
REPORT_CHART_GROUP_ORDER = [*CHART_UI_GROUPS_ORDER, TEXT_SUMMARY_GROUP_LABEL]


def get_report_chart_group(chart_id: str) -> str:
    if is_text_summary_chart(chart_id):
        return TEXT_SUMMARY_GROUP_LABEL
    return CHART_UI_GROUP_BY_ID.get(chart_id, "比較分析")


def get_grouped_chart_ids(chart_ids: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {group: [] for group in REPORT_CHART_GROUP_ORDER}
    for chart_id in chart_ids:
        grouped[get_report_chart_group(chart_id)].append(chart_id)
    return grouped


def _resolve_report_features(selected: list[str], payload: dict[str, Any]) -> list[str]:
    selected = list(selected or [])
    params = (payload or {}).get("parameters", {}) or {}
    if len(selected) == 1 and isinstance(params, dict) and params:
        ordered = [f for f in FEATURE_DISPLAY_NAMES if f in params]
        if ordered:
            return ordered
    return selected


def _has_valid_report_coordinates(store: SessionStore) -> bool:
    try:
        df = store.get_analysis_df()
    except (AttributeError, TypeError, ValueError):
        return False
    if df is None or getattr(df, "empty", True):
        return False
    columns = getattr(df, "columns", [])
    if "X" not in columns or "Y" not in columns:
        return False
    try:
        return not df[["X", "Y"]].dropna().empty
    except (KeyError, TypeError, ValueError):
        return False


class PptxExportWorker(QThread):
    """Run PPTX generation outside the UI event path."""

    progress_updated = Signal(int, str)
    export_finished = Signal(bool, str)

    def __init__(self, output_path: str, chart_ids: list[str], parent=None) -> None:
        super().__init__(parent)
        self._output_path = output_path
        self._chart_ids = list(chart_ids)

    def run(self) -> None:
        """Generate the PPTX report and emit worker progress/result signals."""
        try:
            from app.services.report_service import ReportService

            ok, err = ReportService().generate_pptx_report(
                output_path=self._output_path,
                template_type=TEMPLATE_ENGINEERING,
                chart_ids_to_export=self._chart_ids,
                progress_callback=lambda val, msg: self.progress_updated.emit(val, msg),
            )
            self.export_finished.emit(bool(ok), str(err or ""))
        except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError, OSError) as exc:
            self.export_finished.emit(False, str(exc))


class ReportExportPage(QWidget):
    """
    Refined high-density Report Export Page.
    Consolidates grouped chart selection into a unified industrial dashboard.
    """
    def __init__(self, parent=None, status_model: Optional["AppStatusModel"] = None) -> None:
        super().__init__(parent)
        self._status_model = status_model
        self._chart_availability: dict[str, dict[str, str]] = {}
        self._export_worker: Optional[PptxExportWorker] = None
        layout = QVBoxLayout(self)
        page_margins_and_spacing(layout)

        # ── Toolbar: Page Title & Global Actions ──────────────────────
        toolbar = QFrame()
        toolbar.setProperty("class", "headerToolbar")
        toolbar.setProperty("headerRole", "utilityHeader")
        toolbar.setProperty("headerDensity", "compact")
        header_inner = QHBoxLayout(toolbar)
        header_inner.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
        header_inner.setSpacing(SPACING_8)

        title_lbl = QLabel("報告匯出")
        title_lbl.setProperty("class", "pageTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_inner.addWidget(title_lbl)

        self.chart_coverage_hint = QLabel("")
        self.chart_coverage_hint.setProperty("class", "caption")
        self.chart_coverage_hint.setVisible(False)
        header_inner.addWidget(self.chart_coverage_hint, 1)

        self._report_lamp = create_status_lamp()
        self._report_status_lbl = QLabel("就緒")
        self._report_status_lbl.setProperty("class", "statusIndicator")
        header_inner.addWidget(self._report_lamp)
        header_inner.addWidget(self._report_status_lbl)

        self.btn_export = QPushButton("匯出 PPTX")
        self.btn_export.setProperty("class", "primary")
        self.btn_export.setToolTip("將選取的圖表匯出為 PowerPoint 報告")
        self.btn_export.clicked.connect(self._export_to_pptx)
        header_inner.addWidget(self.btn_export)

        layout.addWidget(toolbar)
        layout.addSpacing(PAGE_HEADER_BOTTOM_SPACING)

        # ── Main Content: Unified Card ───────────────────────────────
        self.main_card = QFrame()
        self.main_card.setObjectName("reportContent")
        self.main_card.setFrameShape(QFrame.Shape.NoFrame)
        card_layout = QVBoxLayout(self.main_card)
        card_layout.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
        card_layout.setSpacing(SPACING_8)

        # Grid of Chart Groups (Scrollable vertically, no horizontal overflow)
        self.chart_scroll = QScrollArea()
        self.chart_scroll.setWidgetResizable(True)
        self.chart_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chart_scroll.setObjectName("reportChartScroll")
        self.chart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chart_inner = QWidget()
        chart_inner.setMinimumWidth(0)
        self.chart_layout = QGridLayout(chart_inner)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_layout.setSpacing(SPACING_8)
        self.chart_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chart_layout.setColumnStretch(0, 1)
        self.chart_layout.setColumnStretch(1, 1)

        self._group_chart_ids = get_grouped_chart_ids(CHART_ORDER)
        self._group_count_labels = {}
        self._chart_checkboxes = {}

        for group_index, group in enumerate(REPORT_CHART_GROUP_ORDER):
            group_style_key = chart_group_style_key(group)
            chart_ids = self._group_chart_ids.get(group, [])
            group_frame = QFrame()
            group_frame.setObjectName("controlCard")
            group_frame.setProperty("chartGroup", group_style_key)
            group_frame.setMinimumWidth(0)
            group_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            group_layout = QVBoxLayout(group_frame)
            group_layout.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_12)
            group_layout.setSpacing(SPACING_4)

            # Group Header
            gh = QHBoxLayout()
            gh.setContentsMargins(SPACING_4, 0, SPACING_4, 0)
            lbl_group = QLabel(group)
            lbl_group.setProperty("class", "processDashCardTitle")
            gh.addWidget(lbl_group)
            gh.addStretch()
            
            self._group_count_labels[group] = QLabel("0/0")
            self._group_count_labels[group].setProperty("class", "caption")
            gh.addWidget(self._group_count_labels[group])
            group_layout.addLayout(gh)

            for text, action in [("全選", True), ("清除", False)]:
                btn = QPushButton(text)
                btn.setProperty("class", "tertiary")
                btn.setFixedHeight(GROUP_ACTION_BUTTON_HEIGHT)
                btn.clicked.connect(lambda _, g=group, val=action: self._set_group_checked(g, val))
                gh.addWidget(btn)

            # Checkboxes
            cb_container = QVBoxLayout()
            cb_container.setSpacing(SPACING_XXS)
            for cid in chart_ids:
                full_name = get_chart_display_name(cid, lang="zh_only")
                cb = QCheckBox(full_name)
                cb.setToolTip(full_name)
                cb.setProperty("chart_id", cid)
                cb.setProperty("chartGroup", group_style_key)
                cb.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
                cb.toggled.connect(self._on_chart_selection_changed)
                self._chart_checkboxes[cid] = cb
                cb_container.addWidget(cb)
            group_layout.addLayout(cb_container)

            row = group_index // 2
            col = group_index % 2
            self.chart_layout.addWidget(group_frame, row, col, Qt.AlignmentFlag.AlignTop)

        self.chart_scroll.setWidget(chart_inner)
        card_layout.addWidget(self.chart_scroll, 1)

        layout.addWidget(self.main_card, 1)

        self._apply_engineering_defaults()
        self._refresh_group_counts()

    def showEvent(self, event: QShowEvent) -> None:
        """Refresh checkbox availability whenever the page becomes visible."""
        super().showEvent(event)
        self._update_chart_checkboxes_availability()
        self._uncheck_incompatible_disabled()
        self._refresh_group_counts()

    def _set_report_lamp(self, state: str, text: str) -> None:
        self._report_lamp.setProperty("state", state)
        self._report_lamp.style().unpolish(self._report_lamp)
        self._report_lamp.style().polish(self._report_lamp)
        self._report_status_lbl.setText(text)
        self._report_status_lbl.setProperty("state", state)
        self._report_status_lbl.style().unpolish(self._report_status_lbl)
        self._report_status_lbl.style().polish(self._report_status_lbl)

    def _update_chart_checkboxes_availability(self):
        store = SessionStore()
        selected = getattr(store, "selected_features", [])
        payload = getattr(store, "last_analysis_payload", {})
        active = _resolve_report_features(selected, payload)
        has_coordinates = _has_valid_report_coordinates(store)
        
        is_valid = store.meas_meta.get("is_valid", False)
        self.btn_export.setEnabled(is_valid and not self._is_export_running())
        if is_valid:
            self._set_report_lamp("success", "就緒")
        else:
            self._set_report_lamp("error", "缺乏量測資料")

        for cid, cb in self._chart_checkboxes.items():
            base_label = get_chart_display_name(cid, lang="zh_only")
            avail = is_chart_available_for_selection(cid, active) if active else True
            reason = get_incompatible_reason(cid, active) if not avail and active else ""
            if cid == "spatial_heatmap" and not has_coordinates:
                avail = False
                reason = "未納入：缺座標資料"
                cb.setText(f"{base_label}（{reason}）")
            else:
                cb.setText(base_label)
            cb.setEnabled(avail)
            if not avail and reason and cid != "spatial_heatmap":
                cb.setToolTip(f"不相容：{reason}")
            else:
                cb.setToolTip(base_label)
            cb.setProperty("state", "incompatible" if not avail else "")
            cb.style().unpolish(cb)
            cb.style().polish(cb)

        self._refresh_group_counts()

    def _set_group_checked(self, group: str, checked: bool):
        for cid in self._group_chart_ids.get(group, []):
            cb = self._chart_checkboxes.get(cid)
            if cb and cb.isEnabled():
                cb.setChecked(checked)
        self._refresh_group_counts()

    def _on_chart_selection_changed(self, _):
        self._refresh_group_counts()

    def _refresh_group_counts(self):
        selected_all = []
        for group, ids in self._group_chart_ids.items():
            sel = [cid for cid in ids if self._chart_checkboxes[cid].isChecked()]
            selected_all.extend(sel)
            if group in self._group_count_labels:
                self._group_count_labels[group].setText(f"{len(sel)}/{len(ids)}")
        
        # Update summary row
        avail_count = sum(1 for cb in self._chart_checkboxes.values() if cb.isEnabled())
        incompat_count = len(self._chart_checkboxes) - avail_count
        self.chart_coverage_hint.setText(f"目前勾選：{len(selected_all)} 項 | 可用備選：{avail_count} 項 | 不相容：{incompat_count} 項")
        self.chart_coverage_hint.setVisible(bool(self.chart_coverage_hint.text().strip()))

    def _apply_engineering_defaults(self):
        for cid, cb in self._chart_checkboxes.items():
            cb.setChecked(cid in ENGINEERING_DEFAULT_CHART_IDS if cb.isEnabled() else False)

    def _uncheck_incompatible_disabled(self):
        for cb in self._chart_checkboxes.values():
            if not cb.isEnabled() and cb.isChecked():
                cb.setChecked(False)

    def _export_to_pptx(self):
        if self._is_export_running():
            return
        store = SessionStore()
        if not store.meas_meta.get("is_valid"):
            return
        
        ids = [cid for cid, cb in self._chart_checkboxes.items() if cb.isChecked()]
        if not ids:
            ids = [cid for cid in ENGINEERING_DEFAULT_CHART_IDS if cid in self._chart_checkboxes]
        
        path, _ = QFileDialog.getSaveFileName(self, "匯出報告", "SPI_Analysis_Report.pptx", "PowerPoint (*.pptx)")
        if not path:
            return

        from app.ui.dialogs.pptx_export_confirm_dialog import PptxExportConfirmDialog
        if PptxExportConfirmDialog(self, chart_ids=ids, using_fallback=not any(cb.isChecked() for cb in self._chart_checkboxes.values())).exec() != QDialog.DialogCode.Accepted:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self._set_report_lamp("loading", "匯出中…")
        self.btn_export.setEnabled(False)

        worker = PptxExportWorker(path, ids, self)
        self._export_worker = worker
        worker.progress_updated.connect(self._on_export_progress)
        worker.export_finished.connect(self._on_export_finished)
        worker.finished.connect(lambda w=worker: self._clear_export_worker(w))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _is_export_running(self) -> bool:
        worker = self._export_worker
        if worker is None:
            return False
        try:
            return worker.isRunning()
        except RuntimeError:
            self._export_worker = None
            return False

    def _on_export_progress(self, val: int, msg: str) -> None:
        self._set_report_lamp("loading", msg)
        if self._status_model:
            self._status_model.set_state("loading", msg)
            self._status_model.set_progress(val)

    def _on_export_finished(self, ok: bool, err: str) -> None:
        QApplication.restoreOverrideCursor()
        if ok:
            self._set_report_lamp("ok", "已匯出")
            if self._status_model:
                self._status_model.set_state("success", "報告匯出成功")
                self._status_model.set_progress(-2)
        else:
            self._set_report_lamp("error", err or "發生錯誤")
            if self._status_model:
                self._status_model.set_progress(-2)
        self.btn_export.setEnabled(bool(SessionStore().meas_meta.get("is_valid", False)))

    def _clear_export_worker(self, worker: PptxExportWorker) -> None:
        if self._export_worker is worker:
            self._export_worker = None
