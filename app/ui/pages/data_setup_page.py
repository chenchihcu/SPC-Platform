"""
資料設定頁：整合為「參數配置中心」。
核心策略：
1) 全域產品選擇（單一來源）；
2) 三步驟卡片（座標 / 規格 / 量測）；
3) 頁底 readiness summary + Start Analysis gate。
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime

from PySide6 import QtWidgets
from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from app.data.coordinate_registry import list_registered
from app.data.supplier_library import list_supplier_names
from app.ui.pages.coordinate_manager_page import CoordinateManagerPage
from app.ui.pages.data_upload_page import DataUploadPage
from app.ui.theme.tokens import (
    DATA_SETUP_PAGE_MARGIN_H,
    DATA_SETUP_PAGE_MARGIN_V,
    DATA_SETUP_PRODUCT_COMBO_MIN_WIDTH,
    DATA_SETUP_TABLE_GAP,
    DATA_SETUP_TABLE_LEFT_MIN_WIDTH,
    DATA_SETUP_TABLE_MAIN_MIN_HEIGHT,
    DATA_SETUP_TABLE_RIGHT_MIN_WIDTH,
    DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
    DATA_SETUP_TABLE_SECTION_MIN_HEIGHT,
    DATA_SETUP_TABLE_WORKORDER_MIN_HEIGHT,
    SPACING_4,
    SPACING_8,
    DATA_SETUP_WORKORDER_MIN_WIDTH,
    DATA_SETUP_PASTE_TYPE_MIN_WIDTH,
    DATA_SETUP_INLINE_LABEL_WIDTH,
    DATA_SETUP_PATH_ACTION_MIN_WIDTH,
    HEADER_TOOLBAR_MIN_HEIGHT,
    NAV_STEP_BTN_HEIGHT,
)
from app.ui.widgets.page_templates import (
    apply_status_accessibility,
    bind_label_to_widget,
    create_status_lamp,
)
from app.ui.widgets.stencil_spec_editor import StencilSpecEditor


def layout_tier_from_width(w: int) -> int:
    """回傳響應式布局層級：固定回傳 1 以採行高密度列排版模式。"""
    return 1


@dataclass(frozen=True)
class DataSetupLayoutBudget:
    """Computed geometry budget for the one-page Data Setup table layout."""

    total_width: int
    total_height: int
    content_width: int
    content_height: int
    workorder_height: int
    main_height: int
    left_width: int
    right_width: int
    right_top_height: int
    right_bottom_height: int
    label_width: int
    input_width: int
    action_width: int
    row_height: int

    def to_dict(self) -> dict[str, int]:
        """Return a plain dict for diagnostics and tests."""
        return asdict(self)


class DataSetupPage(QWidget):
    """
    Single-page data setup view with:
    - global product selector
    - three step cards
    - readiness summary footer
    """

    meas_uploaded = Signal(str)
    coord_uploaded = Signal(str)
    product_name_selected = Signal(str)
    start_analysis_requested = Signal()
    spec_saved = Signal(str)
    manage_specs_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("dataPage", "dataSetup")
        self._current_tier = 1
        self._diagnostic_page_inner_width = 0
        self._diagnostic_available_width = 0
        self._diagnostic_content_host_width = 0
        self._current_product = ""
        self._coord_ready = False
        self._meas_ready = False
        self._spec_ready = False
        self._batch_qty_value = ""

        self._grid_layout: QGridLayout | None = None # 用於響應式切換

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_content.setObjectName("dataSetupScrollContent")
        self.scroll_content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QtWidgets.QVBoxLayout(self.scroll_content)
        outer.setContentsMargins(
            DATA_SETUP_PAGE_MARGIN_H,
            DATA_SETUP_PAGE_MARGIN_V,
            DATA_SETUP_PAGE_MARGIN_H,
            SPACING_4, # Bottom margin tighter
        )
        outer.setSpacing(SPACING_8)

        # ── Step cards initialization (must be before layout) ──
        self._coord_content = CoordinateManagerPage(self, embedded=True)
        self._coord_content.set_external_product_mode(True)
        self._stencil_content = StencilSpecEditor(self, embedded=True)
        self._stencil_content.set_external_product_mode(True)
        self._upload_content = DataUploadPage(self, embedded=True)
        for compact_section in (self._coord_content, self._stencil_content, self._upload_content):
            compact_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # ── 頁首：標題 + 全域產品 + mini 狀態儀表 ──────────────────────
        header_card = QFrame()
        header_card.setProperty("class", "headerToolbar")
        header_card.setProperty("headerRole", "workflowHeader")
        header_card.setProperty("headerDensity", "compact")
        header_card.setMinimumHeight(HEADER_TOOLBAR_MIN_HEIGHT + SPACING_4)
        self._header_card = header_card
        header_lay = QHBoxLayout(header_card)
        header_lay.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
        header_lay.setSpacing(SPACING_8)

        self.header_lbl = QLabel("資料設定")
        self.header_lbl.setProperty("class", "pageTitle")
        self.header_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_lay.addWidget(self.header_lbl, 0)

        lbl_prod = QLabel("分析產品")
        lbl_prod.setProperty("class", "caption")
        lbl_prod.setMinimumWidth(DATA_SETUP_INLINE_LABEL_WIDTH)
        lbl_prod.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_lay.addWidget(lbl_prod, 0)
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(DATA_SETUP_PRODUCT_COMBO_MIN_WIDTH)
        self.product_combo.currentIndexChanged.connect(self._on_product_changed)
        header_lay.addWidget(self.product_combo, 1)
        
        self.btn_new_product = QPushButton("新增產品")
        self.btn_new_product.setProperty("class", "secondary")
        self.btn_new_product.setToolTip("新增產品並綁定座標檔")
        self.btn_new_product.clicked.connect(self._on_new_product_clicked)
        header_lay.addWidget(self.btn_new_product, 0)
        header_lay.addStretch(1)

        def _status_pair(label_text: str) -> tuple[QFrame, QLabel]:
            lamp = create_status_lamp()
            label = QLabel(label_text)
            label.setProperty("class", "statusIndicator")
            apply_status_accessibility(lamp, label, state="idle", text=label_text)
            header_lay.addWidget(lamp, 0)
            header_lay.addWidget(label, 0)
            return lamp, label

        self.coord_lamp, self.coord_status_lbl = _status_pair("座標")
        self.spec_lamp, self.spec_status_lbl = _status_pair("規格")
        self.meas_lamp, self.meas_status_lbl = _status_pair("量測")
        self._status_label_by_lamp: dict[QFrame, QLabel] = {
            self.coord_lamp: self.coord_status_lbl,
            self.spec_lamp: self.spec_status_lbl,
            self.meas_lamp: self.meas_status_lbl,
        }
        outer.addWidget(header_card)

        # ── 核心內容區：一頁式量化表格布局 ───────────────────────────
        self.main_content_card = QFrame()
        self.main_content_card.setObjectName("dataSetupTable")
        self.main_content_card.setProperty("class", "dataSetupTable")
        self._grid_layout = QGridLayout(self.main_content_card)
        self._grid_layout.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
        self._grid_layout.setHorizontalSpacing(DATA_SETUP_TABLE_GAP)
        self._grid_layout.setVerticalSpacing(DATA_SETUP_TABLE_GAP)

        # ── 專案/工單細節 (分散整合自舊工單頁) ──
        self._workorder_wrap = QWidget()
        self._workorder_grid = QGridLayout(self._workorder_wrap)
        self._workorder_grid.setContentsMargins(0, SPACING_4, 0, SPACING_4)
        self._workorder_grid.setHorizontalSpacing(SPACING_8)
        self._workorder_grid.setVerticalSpacing(SPACING_8)

        self.supplier_work_order_input = QtWidgets.QLineEdit()
        self.supplier_work_order_input.setProperty("class", "largeInput")
        self.supplier_work_order_input.setPlaceholderText("供應商工單號")
        self.supplier_work_order_input.setMinimumWidth(DATA_SETUP_WORKORDER_MIN_WIDTH)
        self.supplier_work_order_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.outsource_work_order_input = QtWidgets.QLineEdit()
        self.outsource_work_order_input.setProperty("class", "largeInput")
        self.outsource_work_order_input.setPlaceholderText("醫電製令工單號")
        self.outsource_work_order_input.setMinimumWidth(DATA_SETUP_WORKORDER_MIN_WIDTH)
        self.outsource_work_order_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.supplier_input = QComboBox()
        self.supplier_input.setProperty("class", "largeInput")
        self.supplier_input.addItem("請選擇供應商…", "")
        self.supplier_input.setCurrentIndex(0)
        self.supplier_input.setMinimumWidth(DATA_SETUP_WORKORDER_MIN_WIDTH)
        self.supplier_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.paste_type_combo = QComboBox()
        self.paste_type_combo.addItems(["Type 3", "Type 4", "Type 5", "Type 6"])
        self.paste_type_combo.setMinimumWidth(DATA_SETUP_PASTE_TYPE_MIN_WIDTH)
        self.line_name_combo = QComboBox()
        self.line_name_combo.addItem("請選擇線別", "")
        self.line_name_combo.addItems(["Line 1", "Line 2", "Line 3", "Line 4"])
        self.line_name_combo.setMinimumWidth(DATA_SETUP_PASTE_TYPE_MIN_WIDTH)
        self.production_date_edit = QDateEdit()
        self.production_date_edit.setCalendarPopup(True)
        self.production_date_edit.setDisplayFormat("yy/MM/dd")
        self.production_date_edit.setDate(QDate.currentDate())
        self.production_date_edit.setMinimumWidth(DATA_SETUP_PASTE_TYPE_MIN_WIDTH)
        self.production_date_edit.setMinimumHeight(NAV_STEP_BTN_HEIGHT)
        cal = self.production_date_edit.calendarWidget()
        if cal is not None:
            cal.setVerticalHeaderFormat(QtWidgets.QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
            cal.setGridVisible(True)
            cal.setMinimumSize(320, 280)

        self.batch_qty_display = QtWidgets.QLineEdit()
        self.batch_qty_display.setReadOnly(True)
        self.batch_qty_display.setProperty("class", "readOnlyInput")
        self.batch_qty_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.batch_qty_display.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.batch_qty_lbl = self.batch_qty_display # Keep reference for backward calls if any
        self._set_batch_qty_display("")
        self.batch_qty_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._date_field = self._make_inline_field("生產日期", self.production_date_edit)
        self._supplier_wo_field = self._make_inline_field("供應商工單", self.supplier_work_order_input)
        self._outsource_wo_field = self._make_inline_field("醫電工單", self.outsource_work_order_input)
        self._supplier_field = self._make_inline_field("供應商", self.supplier_input)
        self._paste_field = self._make_inline_field("錫膏類型", self.paste_type_combo)
        self._line_field = self._make_inline_field("線別", self.line_name_combo)
        self._batch_field = self._make_inline_field("批量", self.batch_qty_lbl)

        self._workorder_items: list[tuple[QWidget, int]] = [
            (self._date_field, 4),        # Row 1 (4/12)
            (self._supplier_wo_field, 4), # Row 1 (4/12)
            (self._outsource_wo_field, 4),# Row 1 (4/12) -> End Row 1
            (self._supplier_field, 6),    # Row 2 (6/12)
            (self._paste_field, 6),       # Row 2 (6/12) -> End Row 2
            (self._line_field, 6),        # Row 3 (6/12)
            (self._batch_field, 6),       # Row 3 (6/12) -> End Row 3
        ]
        self._workorder_wrap.setObjectName("dataSetupWorkorderRegion")
        self._workorder_wrap.setProperty("class", "dataSetupTableRegion")
        self._grid_layout.addWidget(self._workorder_wrap, 0, 0, 1, 2)
        self._reflow_workorder_items()

        self._coord_region = self._make_table_region("座標", self._coord_content, "dataSetupCoordinateRegion")
        self._spec_region = self._make_table_region("鋼板規格", self._stencil_content, "dataSetupSpecRegion")
        self._upload_region = self._make_table_region("量測", self._upload_content, "dataSetupMeasurementRegion")

        self._grid_layout.addWidget(self._coord_region, 1, 0, 2, 1)
        self._grid_layout.addWidget(self._spec_region, 1, 1)
        self._grid_layout.addWidget(self._upload_region, 2, 1)
        self._grid_layout.setColumnStretch(0, 5)
        self._grid_layout.setColumnStretch(1, 6)
        self._grid_layout.setRowStretch(1, 1)
        self._grid_layout.setRowStretch(2, 1)

        self._content_host = self.main_content_card
        self._content_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._latest_layout_budget = self._compute_layout_budget()
        outer.addWidget(self._content_host, 1)

        # ── Footer summary ────────────────────────────────────────────
        footer = QFrame()
        footer.setProperty("class", "headerToolbar")
        footer.setProperty("headerRole", "utilityHeader")
        footer.setProperty("headerDensity", "compact")
        self._footer_card = footer
        footer_lay = QtWidgets.QHBoxLayout(footer)
        footer_lay.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
        footer_lay.setSpacing(SPACING_8)
        self.readiness_lbl = QLabel("尚未完成")
        self.readiness_lbl.setProperty("class", "statusIndicator")
        self.readiness_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.btn_start_analysis = QPushButton("開始分析")
        self.btn_start_analysis.setProperty("class", "primary")
        self.btn_start_analysis.setEnabled(False)
        self.btn_start_analysis.clicked.connect(self.start_analysis_requested.emit)
        footer_lay.addWidget(self.readiness_lbl, 1)
        footer_lay.addWidget(self.btn_start_analysis, 0)
        outer.addWidget(footer, 0)

        # ── 訊號轉發 + readiness 同步 ─────────────────────────────────
        self._upload_content.meas_uploaded.connect(self._on_meas_uploaded)
        self._coord_content.coord_uploaded.connect(self._on_coord_uploaded)
        self._stencil_content.thickness_validity_changed.connect(self._on_spec_validity_changed)
        self._coord_content.registry_changed.connect(self._reload_product_options)
        self._stencil_content.spec_saved.connect(self.spec_saved.emit)
        self._stencil_content.manage_requested.connect(self.manage_specs_requested.emit)

        self._reload_product_options()
        self._reload_supplier_options()
        self._on_spec_validity_changed(self._stencil_content.has_valid_main_thickness())
        self._refresh_readiness()
        
        self.scroll_area.setWidget(self.scroll_content)
        main_lay = QtWidgets.QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.addWidget(self.scroll_area)

        self._update_layout_tier(layout_tier_from_width(self.width()))

    @staticmethod
    def _make_table_region(title_text: str, content: QWidget, object_name: str) -> QFrame:
        """Create one region in the Data Setup table without nested card chrome."""
        region = QFrame()
        region.setObjectName(object_name)
        region.setProperty("class", "dataSetupTableRegion")
        region.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QtWidgets.QVBoxLayout(region)
        layout.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
        layout.setSpacing(SPACING_4)
        title = QLabel(title_text)
        title.setProperty("class", "sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(title, 0)
        layout.addWidget(content, 1)
        return region

    def _compute_layout_budget(self) -> DataSetupLayoutBudget:
        """Compute explicit area and row budgets for diagnostics and layout gates."""
        content_width = max(0, self._content_host.width() if hasattr(self, "_content_host") else self.width())
        content_height = max(0, self._content_host.height() if hasattr(self, "_content_host") else self.height())
        available_columns = max(0, content_width - DATA_SETUP_TABLE_GAP)
        min_columns = DATA_SETUP_TABLE_LEFT_MIN_WIDTH + DATA_SETUP_TABLE_RIGHT_MIN_WIDTH
        if available_columns >= min_columns:
            left_width = max(DATA_SETUP_TABLE_LEFT_MIN_WIDTH, int(available_columns * 0.46))
            right_width = max(DATA_SETUP_TABLE_RIGHT_MIN_WIDTH, available_columns - left_width)
        else:
            left_width = int(available_columns * 0.45)
            right_width = max(0, available_columns - left_width)

        workorder_height = max(
            DATA_SETUP_TABLE_WORKORDER_MIN_HEIGHT,
            self._workorder_wrap.sizeHint().height() if hasattr(self, "_workorder_wrap") else 0,
        )
        main_height = max(
            DATA_SETUP_TABLE_MAIN_MIN_HEIGHT,
            content_height - workorder_height - DATA_SETUP_TABLE_GAP,
        )
        right_top_height = max(DATA_SETUP_TABLE_SECTION_MIN_HEIGHT, int(main_height * 0.52))
        right_bottom_height = max(
            DATA_SETUP_TABLE_SECTION_MIN_HEIGHT,
            main_height - right_top_height - DATA_SETUP_TABLE_GAP,
        )
        input_width = max(
            DATA_SETUP_WORKORDER_MIN_WIDTH,
            left_width - DATA_SETUP_INLINE_LABEL_WIDTH - DATA_SETUP_TABLE_GAP,
        )
        return DataSetupLayoutBudget(
            total_width=max(0, self.width()),
            total_height=max(0, self.height()),
            content_width=content_width,
            content_height=content_height,
            workorder_height=workorder_height,
            main_height=main_height,
            left_width=left_width,
            right_width=right_width,
            right_top_height=right_top_height,
            right_bottom_height=right_bottom_height,
            label_width=DATA_SETUP_INLINE_LABEL_WIDTH,
            input_width=input_width,
            action_width=DATA_SETUP_PATH_ACTION_MIN_WIDTH,
            row_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
        )

    def _apply_layout_budget(self, budget: DataSetupLayoutBudget) -> None:
        """Apply computed geometry constraints without allowing the footer to scroll away."""
        if self._grid_layout is None:
            return
        self._grid_layout.setColumnMinimumWidth(0, DATA_SETUP_TABLE_LEFT_MIN_WIDTH)
        self._grid_layout.setColumnMinimumWidth(1, DATA_SETUP_TABLE_RIGHT_MIN_WIDTH)
        self._grid_layout.setRowMinimumHeight(0, DATA_SETUP_TABLE_WORKORDER_MIN_HEIGHT)
        self._grid_layout.setRowMinimumHeight(1, DATA_SETUP_TABLE_SECTION_MIN_HEIGHT)
        self._grid_layout.setRowMinimumHeight(2, DATA_SETUP_TABLE_SECTION_MIN_HEIGHT)
        self._coord_region.setMinimumHeight(DATA_SETUP_TABLE_MAIN_MIN_HEIGHT)
        self._spec_region.setMinimumHeight(DATA_SETUP_TABLE_SECTION_MIN_HEIGHT)
        self._upload_region.setMinimumHeight(DATA_SETUP_TABLE_SECTION_MIN_HEIGHT)

    def latest_layout_budget(self) -> DataSetupLayoutBudget:
        """Return the most recent Data Setup layout budget."""
        return self._latest_layout_budget

    def resizeEvent(self, event) -> None:
        """Update responsive layout tier when page size changes."""
        super().resizeEvent(event)
        self._update_layout_tier(layout_tier_from_width(self.width()))

    def showEvent(self, event) -> None:
        """Recompute responsive tier after the widget becomes visible."""
        super().showEvent(event)
        self._update_layout_tier(layout_tier_from_width(self.width()))
        QTimer.singleShot(0, lambda: self._update_layout_tier(layout_tier_from_width(self.width())))
        
    def _sync_layout_from_width(self) -> None:
        """Alias for test compatibility."""
        self._update_layout_tier(layout_tier_from_width(self.width()))

    @property
    def _coord_page(self) -> CoordinateManagerPage:
        return self._coord_content

    @property
    def _stencil_editor(self) -> StencilSpecEditor:
        return self._stencil_content

    @property
    def _upload_page(self) -> DataUploadPage:
        return self._upload_content

    # ── UI handlers ─────────────────────────────────────────────────

    def _reload_product_options(self) -> None:
        keep = self._current_product
        self.product_combo.blockSignals(True)
        try:
            self.product_combo.clear()
            self.product_combo.addItem("請選擇產品…", "")
            for entry in list_registered():
                name = (entry.get("product_name") or "").strip()
                if name:
                    self.product_combo.addItem(name, name)
            if keep:
                idx = self.product_combo.findData(keep)
                if idx >= 0:
                    self.product_combo.setCurrentIndex(idx)
        finally:
            self.product_combo.blockSignals(False)

    def _reload_supplier_options(self, keep_value: str = "") -> None:
        keep = keep_value.strip()
        self.supplier_input.blockSignals(True)
        try:
            self.supplier_input.clear()
            self.supplier_input.addItem("請選擇供應商…", "")
            for supplier_name in list_supplier_names():
                name = supplier_name.strip()
                if name:
                    self.supplier_input.addItem(name, name)
            if keep:
                idx = self.supplier_input.findData(keep)
                if idx < 0:
                    self.supplier_input.addItem(keep, keep)
                    idx = self.supplier_input.findData(keep)
                self.supplier_input.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.supplier_input.blockSignals(False)

    def _set_lamp_state(self, lamp: QFrame, state: str) -> None:
        lamp.setProperty("state", state)
        label = self._status_label_by_lamp.get(lamp)
        if label is not None:
            apply_status_accessibility(lamp, label, state=state)
        lamp.style().unpolish(lamp)
        lamp.style().polish(lamp)

    def _on_product_changed(self) -> None:
        product = str(self.product_combo.currentData() or "")
        self._current_product = product

        self._coord_content.set_selected_product(product)
        self._stencil_content.set_selected_product(product)
        self._coord_content.reset_upload_state()
        self._upload_content.reset_upload_state()
        self._stencil_content.load_selected_product_spec()

        self._coord_ready = False
        self._meas_ready = False
        self._spec_ready = self._stencil_content.has_valid_main_thickness()
        self.spec_status_lbl.setText("規格 未設定" if not self._spec_ready else "規格 已就緒")
        self._set_lamp_state(self.coord_lamp, "idle")
        self._set_lamp_state(self.meas_lamp, "idle")
        self._set_lamp_state(self.spec_lamp, "success" if self._spec_ready else "warning")

        self.product_name_selected.emit(product)
        self._refresh_readiness()

    def _on_new_product_clicked(self) -> None:
        """Trigger 'New Product' mode by expanding registration section."""
        self._coord_content.show_registration(True)
        self._stencil_content.set_summary_mode(False) # 開放編輯規格
        # Ensure focus is on name edit
        self._coord_content.product_name_edit.setFocus()
        self.statusBar().showMessage("請先選擇座標檔，驗證成功後輸入產品名稱並儲存綁定。", 4000)

    def statusBar(self) -> QtWidgets.QStatusBar:
        """Helper to find the main window's status bar."""
        win = self.window()
        if isinstance(win, QtWidgets.QMainWindow):
            return win.statusBar()
        return QtWidgets.QStatusBar() # Fallback

    def _on_coord_uploaded(self, path: str) -> None:
        has_path = bool(path)
        self._coord_ready = False
        self.coord_status_lbl.setText("座標 載入中…" if has_path else "座標 未完成")
        self._set_lamp_state(self.coord_lamp, "loading" if has_path else "idle")
        self.coord_uploaded.emit(path)
        self._refresh_readiness()

    def _on_meas_uploaded(self, path: str) -> None:
        has_path = bool(path)
        self._meas_ready = False
        self.meas_status_lbl.setText("量測 載入中…" if has_path else "量測 未完成")
        self._set_lamp_state(self.meas_lamp, "loading" if has_path else "idle")
        self.meas_uploaded.emit(path)
        self._refresh_readiness()

    def _on_spec_validity_changed(self, valid: bool) -> None:
        self._spec_ready = bool(valid)
        self.spec_status_lbl.setText("規格 已就緒" if valid else "規格 需設定厚度")
        self._set_lamp_state(self.spec_lamp, "success" if valid else "warning")
        self._refresh_readiness()

    def _update_layout_tier(self, tier: int) -> None:
        """Refresh the one-page table layout budget."""
        self._current_tier = tier
        self._reflow_workorder_items()
        self._latest_layout_budget = self._compute_layout_budget()
        self._apply_layout_budget(self._latest_layout_budget)

    @staticmethod
    def _make_inline_field(label_text: str, field: QWidget) -> QWidget:
        host = QWidget()
        lay = QtWidgets.QHBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SPACING_8)
        lbl = QLabel(label_text)
        lbl.setProperty("class", "caption")
        lbl.setMinimumWidth(DATA_SETUP_INLINE_LABEL_WIDTH)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bind_label_to_widget(lbl, field, label_text)
        lay.addWidget(lbl, 0)
        lay.addWidget(field, 1)
        host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        return host

    @staticmethod
    def _max_workorder_units(width: int) -> int:
        """Fixed 12-unit grid to support 3-row layout (3-2-2)."""
        return 12

    def _reflow_workorder_items(self) -> None:
        if not hasattr(self, "_workorder_grid") or not hasattr(self, "_workorder_items"):
            return
        grid = self._workorder_grid
        while grid.count():
            grid.takeAt(0)
        units = self._max_workorder_units(self._available_content_width())
        row = 0
        col = 0
        for widget, span in self._workorder_items:
            use_span = min(span, units)
            if col and (col + use_span > units):
                row += 1
                col = 0
            grid.addWidget(widget, row, col, 1, use_span)
            col += use_span
        for i in range(units):
            grid.setColumnStretch(i, 1)

    def _refresh_readiness(self) -> None:
        readiness_checks = [
            bool(self._current_product),
            bool(self._coord_ready),
            bool(self._meas_ready),
            bool(self._spec_ready),
        ]
        done_count = sum(1 for ok in readiness_checks if ok)
        readiness_pct = int((done_count / len(readiness_checks)) * 100)
        is_ready = (
            bool(self._current_product)
            and self._coord_ready
            and self._meas_ready
            and self._spec_ready
        )
        if is_ready:
            self.readiness_lbl.setText("已準備就緒，可開始分析")
            readiness_state = "success"
        else:
            missing = []
            if not self._current_product:
                missing.append("產品")
            if not self._coord_ready:
                missing.append("座標檔")
            if not self._meas_ready:
                missing.append("量測檔")
            if not self._spec_ready:
                missing.append("鋼板規格")
            self.readiness_lbl.setText(f"準備度 {readiness_pct}%｜未完成：{' / '.join(missing)}")
            readiness_state = "warning" if done_count else "disabled"
        self.readiness_lbl.setProperty("state", readiness_state)
        self.readiness_lbl.style().unpolish(self.readiness_lbl)
        self.readiness_lbl.style().polish(self.readiness_lbl)
        self.btn_start_analysis.setEnabled(is_ready)

    def _available_content_width(self) -> int:
        """Helper to get reliable width measurement for responsiveness."""
        return self.width() - (DATA_SETUP_PAGE_MARGIN_H * 2)

    def _set_batch_qty_display(self, value: object) -> None:
        """Render batch quantity while keeping raw value separately."""
        raw = str(value).strip() if value is not None else ""
        self._batch_qty_value = "" if raw in {"", "--"} else raw
        display = self._batch_qty_value or "--"
        # Removed "批量:" prefix from text because it's now in the field label
        self.batch_qty_lbl.setText(f"{display} 片 (PCS)")
        self.batch_qty_lbl.setAccessibleDescription(f"批量顯示：{self.batch_qty_lbl.text()}")

    @staticmethod
    def _format_timestamp_from_path(filepath: str) -> str | None:
        if not filepath:
            return None
        try:
            ts = os.path.getmtime(filepath)
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except OSError:
            return None

    # ── 公開 API（保持與 MainWindow 介面一致）───────────────────────

    def update_meas_display(self, meas_df, meas_meta: dict) -> None:
        """Update measurement metadata/status after loader finished."""
        meta = meas_meta or {}
        filepath = str(meta.get("filepath") or "")
        filename = os.path.basename(filepath) if filepath else None
        rows = meta.get("total_rows")
        timestamp = self._format_timestamp_from_path(filepath)
        self._upload_content.set_metadata(filename, rows, timestamp)
        if rows is not None:
            self._set_batch_qty_display(rows)
        is_valid = bool(meta.get("is_valid"))
        if is_valid:
            self._meas_ready = True
            self.meas_status_lbl.setText("量測 已就緒")
            self._set_lamp_state(self.meas_lamp, "success")
        elif filepath:
            self._meas_ready = False
            self.meas_status_lbl.setText(self._format_invalid_status("量測", meta))
            self._set_lamp_state(self.meas_lamp, "warning")
        else:
            self._meas_ready = False
            self.meas_status_lbl.setText("量測 待上傳")
            self._set_lamp_state(self.meas_lamp, "idle")
        self._refresh_readiness()

    def update_coord_display(self, coord_df, coord_meta: dict) -> None:
        """Update coordinate metadata/status after loader finished."""
        meta = coord_meta or {}
        filepath = str(meta.get("filepath") or "")
        filename = os.path.basename(filepath) if filepath else None
        rows = meta.get("total_rows")
        timestamp = self._format_timestamp_from_path(filepath)
        self._coord_content.set_metadata(filename, rows, timestamp)
        self._coord_content.set_current_coord_path(filepath)
        is_valid = bool(meta.get("is_valid"))
        if is_valid:
            self._coord_ready = True
            self.coord_status_lbl.setText("座標 已就緒")
            self._set_lamp_state(self.coord_lamp, "success")
        else:
            self._coord_ready = False
            self.coord_status_lbl.setText(self._format_invalid_status("座標", meta))
            self._set_lamp_state(self.coord_lamp, "warning" if filepath else "idle")
        self._refresh_readiness()

    @staticmethod
    def _format_invalid_status(label: str, meta: dict) -> str:
        """Format a human-readable error status string for a data component."""
        missing = meta.get("missing_required")
        if missing and isinstance(missing, list):
            reason = f"缺欄位：{', '.join(missing)}"
        else:
            reason = str(meta.get("error") or meta.get("reason") or "格式錯誤")
        return f"{label} 錯誤：{reason}"

    def refresh_registered_list(self) -> None:
        """Reload the product dropdown from the coordinate registry.

        Called by MainWindow when navigating to the 資料 page so the combo
        always reflects any products added/removed since last visit.
        """
        keep_supplier = self.supplier_input.currentData() or self.supplier_input.currentText()
        self._reload_product_options()
        self._reload_supplier_options(str(keep_supplier or ""))

    def refresh_stencil_refdes_list(self) -> None:
        """Refresh the RefDes checkbox list inside StencilSpecEditor.

        Called by MainWindow after a successful data load so the stencil
        editor reflects the RefDes available in the newly loaded coordinate file.
        """
        self._stencil_content.refresh_refdes_list()

    def sync_from_store(self, master: dict) -> None:
        """同步工單/產品資訊到 UI 欄位。"""
        product_name = (master.get("product_name") or "").strip()
        self.product_combo.blockSignals(True)
        try:
            idx = self.product_combo.findData(product_name) if product_name else -1
            self.product_combo.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.product_combo.blockSignals(False)
        self._current_product = product_name
        self._coord_content.set_selected_product(product_name)
        self._stencil_content.set_selected_product(product_name)
        self._stencil_content.load_selected_product_spec()
        self._spec_ready = self._stencil_content.has_valid_main_thickness()
        self.spec_status_lbl.setText("規格 已就緒" if self._spec_ready else "規格 需設定厚度")
        self._set_lamp_state(self.spec_lamp, "success" if self._spec_ready else "warning")

        self.supplier_work_order_input.setText(
            master.get("supplier_work_order_no")
            or ""
        )
        self.outsource_work_order_input.setText(
            master.get("outsource_work_order_no")
            or master.get("work_order_no")
            or ""
        )
        self._reload_supplier_options(str(master.get("supplier") or ""))
        self._set_batch_qty_display(master.get("batch_qty", ""))
        # Paste type sync if needed
        paste = master.get("paste_type")
        if paste:
            idx = self.paste_type_combo.findText(paste)
            if idx >= 0:
                self.paste_type_combo.setCurrentIndex(idx)

        line_name = (master.get("line_name") or "").strip()
        line_idx = self.line_name_combo.findText(line_name)
        self.line_name_combo.setCurrentIndex(line_idx if line_idx >= 0 else 0)

        production_date = str(master.get("production_date") or "").strip()
        parsed_date = QDate.fromString(production_date, "yy/MM/dd")
        if not parsed_date.isValid():
            parsed_date = QDate.fromString(production_date, "yyyy-MM-dd")
        if parsed_date.isValid():
            self.production_date_edit.setDate(parsed_date)
        self._refresh_readiness()

    def get_workorder_info(self) -> dict:
        """回傳目前 UI 上的工單資訊。"""
        supplier_work_order_no = self.supplier_work_order_input.text().strip()
        outsource_work_order_no = self.outsource_work_order_input.text().strip()
        primary_work_order_no = outsource_work_order_no or supplier_work_order_no
        return {
            "work_order_no": "",
            "supplier_work_order_no": supplier_work_order_no,
            "outsource_work_order_no": outsource_work_order_no,
            "product_name": self._current_product,
            "supplier": str(self.supplier_input.currentData() or self.supplier_input.currentText()).strip(),
            # Backward compatibility: legacy consumers still read batch_no.
            "batch_no": primary_work_order_no,
            "batch_qty": self._batch_qty_value,
            "paste_type": self.paste_type_combo.currentText(),
            "line_name": self.line_name_combo.currentText().strip() if self.line_name_combo.currentIndex() > 0 else "",
            "production_date": self.production_date_edit.date().toString("yy/MM/dd"),
        }
