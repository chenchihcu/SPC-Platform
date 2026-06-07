"""
Sidebar control panel: filter conditions + action buttons.

Flat layout (no card wrapper) — content flows directly within the sidebar background
for maximum density. Styled via QSS: [sidebarPanel="controlDense"].
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QGridLayout, QLineEdit, QSizePolicy,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from app.ui.theme.tokens import (
    SPACING_8,
    SIDEBAR_CONTROL_MIN_WIDTH,
    SIDEBAR_BUTTON_MIN_HEIGHT,
    CONTROL_FORM_COL_SPACING,
    FORM_GRID_ROW_SPACING,
)
from app.utils.constants import FILTER_ALL, RANGE_ALL_BOARDS, RANGE_FIRST, RANGE_LAST, RANGE_SPECIFY

# Column names used for optional filters (when present in df); must match session_store logic
_OPTIONAL_FILTER_COL_PRODUCT = ("Product", "product_id", "ProductId", "ProductName")
_OPTIONAL_FILTER_COL_TIME = ("Time", "Timestamp", "timestamp", "DateTime")
_OPTIONAL_FILTER_COL_LINE = ("Line", "line_id", "LineId", "LineName")


class ClickableLabel(QLabel):
    """A QLabel that emits a clicked signal when left-clicked."""
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ControlPanel(QWidget):
    """
    Sidebar control panel: flat layout with filter combos and action buttons.

    No card wrapper — content sits directly on the sidebar background.
    Optional product/time/line filters shown only when dataframe has corresponding columns.
    Emits optional_filters_changed() when any filter value changes.
    """

    optional_filters_changed = Signal()
    feature_shortcut_toggled = Signal(str)   # "height" | "area" | "volume"

    def __init__(self) -> None:
        super().__init__()
        self.setProperty("sidebarPanel", "controlDense")
        self.setMinimumWidth(SIDEBAR_CONTROL_MIN_WIDTH)
        self._condition_section_collapsed = False
        self._user_toggled = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scroll area for filter conditions and feature shortcut
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; } "
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(SPACING_8, 0, SPACING_8, 0)
        scroll_layout.setSpacing(SPACING_8)

        # Section header
        title = ClickableLabel("分析條件")
        title.setProperty("class", "sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setToolTip("點擊可展開或收合分析條件")
        title.clicked.connect(self._toggle_collapse)
        scroll_layout.addWidget(title)
        self._condition_title = title

        self._condition_container = QWidget()
        condition_layout = QVBoxLayout(self._condition_container)
        condition_layout.setContentsMargins(0, 0, 0, 0)
        condition_layout.setSpacing(SPACING_8)

        # Filter grid (flat — no card)
        self._condition_grid = QGridLayout()
        self._condition_grid.setContentsMargins(0, 0, 0, 0)
        self._condition_grid.setHorizontalSpacing(CONTROL_FORM_COL_SPACING)
        self._condition_grid.setVerticalSpacing(FORM_GRID_ROW_SPACING)
        self._condition_grid.setColumnStretch(0, 0)
        self._condition_grid.setColumnStretch(1, 1)

        self.range_combo = QComboBox()
        self.range_combo.addItems([RANGE_ALL_BOARDS, RANGE_FIRST, RANGE_LAST, RANGE_SPECIFY])
        self.range_combo.setToolTip("選擇分析視角：全批趨勢、首件、末件或指定板號")

        self.range_label = QLabel("範圍")
        self.range_label.setProperty("class", "formLabel")
        self.range_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.board_specify_combo = QComboBox()
        self.board_specify_combo.setToolTip("選擇要分析的板號")
        self.board_specify_combo.setVisible(False)

        self.board_specify_label = QLabel("指定板")
        self.board_specify_label.setProperty("class", "formLabel")
        self.board_specify_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.board_specify_label.setVisible(False)

        self.refdes_combo = QComboBox()
        self.refdes_combo.setEditable(False)
        self.refdes_combo.setToolTip("指定元件 RefDes 進行分析")

        self.refdes_label = QLabel("元件")
        self.refdes_label.setProperty("class", "formLabel")
        self.refdes_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.part_type_combo = QComboBox()
        self.part_type_combo.setToolTip("依類型篩選")

        self.part_type_label = QLabel("類型")
        self.part_type_label.setProperty("class", "formLabel")
        self.part_type_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.range_combo.currentTextChanged.connect(self._on_range_changed)

        self._condition_grid.addWidget(self.range_label, 0, 0)
        self._condition_grid.addWidget(self.range_combo, 0, 1)
        self._condition_grid.addWidget(self.board_specify_label, 1, 0)
        self._condition_grid.addWidget(self.board_specify_combo, 1, 1)
        self._condition_grid.addWidget(self.refdes_label, 2, 0)
        self._condition_grid.addWidget(self.refdes_combo, 2, 1)
        self._condition_grid.addWidget(self.part_type_label, 3, 0)
        self._condition_grid.addWidget(self.part_type_combo, 3, 1)

        # Initialize with "All" to avoid blank boxes before data load
        self.refdes_combo.addItem(FILTER_ALL)
        self.part_type_combo.addItem(FILTER_ALL)
        
        self._ensure_combo_only_refdes_filter()

        # Optional filters (product, time range, line) — visible only when df has columns
        self.optional_filter_widget = QWidget()
        self.optional_filter_widget.setVisible(False)
        opt_grid = QGridLayout(self.optional_filter_widget)
        opt_grid.setContentsMargins(0, 0, 0, 0)
        opt_grid.setHorizontalSpacing(CONTROL_FORM_COL_SPACING)
        opt_grid.setVerticalSpacing(FORM_GRID_ROW_SPACING)
        opt_grid.setColumnStretch(0, 0)
        opt_grid.setColumnStretch(1, 1)
        product_label = QLabel("產品")
        product_label.setProperty("class", "formLabel")
        product_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.product_combo = QComboBox()
        self.product_combo.setToolTip("依產品篩選（資料有該欄位時顯示）")
        time_start_label = QLabel("開始")
        time_start_label.setProperty("class", "formLabel")
        time_start_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.time_start_edit = QLineEdit()
        self.time_start_edit.setPlaceholderText("開始")
        self.time_start_edit.setToolTip("時間範圍起（選填）")
        time_end_label = QLabel("結束")
        time_end_label.setProperty("class", "formLabel")
        time_end_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.time_end_edit = QLineEdit()
        self.time_end_edit.setPlaceholderText("結束")
        self.time_end_edit.setToolTip("時間範圍訖（選填）")
        line_label = QLabel("產線")
        line_label.setProperty("class", "formLabel")
        line_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.line_combo = QComboBox()
        self.line_combo.setToolTip("依產線篩選（資料有該欄位時顯示）")
        opt_grid.addWidget(product_label, 0, 0)
        opt_grid.addWidget(self.product_combo, 0, 1)
        opt_grid.addWidget(time_start_label, 1, 0)
        opt_grid.addWidget(self.time_start_edit, 1, 1)
        opt_grid.addWidget(time_end_label, 2, 0)
        opt_grid.addWidget(self.time_end_edit, 2, 1)
        opt_grid.addWidget(line_label, 3, 0)
        opt_grid.addWidget(self.line_combo, 3, 1)
        for c in (self.product_combo, self.line_combo):
            c.currentTextChanged.connect(self._on_optional_filter_changed)
        self.time_start_edit.textChanged.connect(self._on_optional_filter_changed)
        self.time_end_edit.textChanged.connect(self._on_optional_filter_changed)

        condition_layout.addLayout(self._condition_grid)
        condition_layout.addWidget(self.optional_filter_widget)
        scroll_layout.addWidget(self._condition_container)

        self._condition_summary = ClickableLabel("分析條件已收合，已保留目前篩選值")
        self._condition_summary.setProperty("class", "caption")
        self._condition_summary.setWordWrap(True)
        self._condition_summary.setVisible(False)
        self._condition_summary.setCursor(Qt.CursorShape.PointingHandCursor)
        self._condition_summary.setToolTip("點擊可展開分析條件")
        self._condition_summary.clicked.connect(self._toggle_collapse)
        scroll_layout.addWidget(self._condition_summary)

        # Feature section — visible but disabled until measurement data is loaded
        self._feature_section = QWidget()
        self._feature_section.setEnabled(False)
        _feat_vbox = QVBoxLayout(self._feature_section)
        _feat_vbox.setContentsMargins(0, 0, 0, 0)
        _feat_vbox.setSpacing(SPACING_8)

        _feat_title = QLabel("特徵")
        _feat_title.setProperty("class", "sectionTitle")
        _feat_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        _feat_vbox.addWidget(_feat_title)

        _feat_seg = QFrame()
        _feat_seg.setProperty("class", "segmentedControl")
        _feat_seg_layout = QHBoxLayout(_feat_seg)
        _feat_seg_layout.setContentsMargins(0, 0, 0, 0)
        _feat_seg_layout.setSpacing(0)

        self._btn_height = QPushButton("高度")
        self._btn_height.setCheckable(True)
        self._btn_height.setProperty("class", "featureToggle")
        self._btn_height.setProperty("feature", "height")
        self._btn_height.setProperty("position", "first")
        self._btn_height.setToolTip("分析高度特徵（可複選）")
        self._btn_height.clicked.connect(lambda: self.feature_shortcut_toggled.emit("height"))

        self._btn_area = QPushButton("面積")
        self._btn_area.setCheckable(True)
        self._btn_area.setProperty("class", "featureToggle")
        self._btn_area.setProperty("feature", "area")
        self._btn_area.setProperty("position", "middle")
        self._btn_area.setToolTip("分析面積特徵（可複選）")
        self._btn_area.clicked.connect(lambda: self.feature_shortcut_toggled.emit("area"))

        self._btn_volume = QPushButton("體積")
        self._btn_volume.setCheckable(True)
        self._btn_volume.setProperty("class", "featureToggle")
        self._btn_volume.setProperty("feature", "volume")
        self._btn_volume.setProperty("position", "last")
        self._btn_volume.setToolTip("分析體積特徵（可複選）")
        self._btn_volume.clicked.connect(lambda: self.feature_shortcut_toggled.emit("volume"))

        for btn in (self._btn_height, self._btn_area, self._btn_volume):
            btn.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        _feat_seg_layout.addWidget(self._btn_height, 1)
        _feat_seg_layout.addWidget(self._btn_area, 1)
        _feat_seg_layout.addWidget(self._btn_volume, 1)
        _feat_vbox.addWidget(_feat_seg)
        scroll_layout.addWidget(self._feature_section)

        self.scroll_area.setWidget(scroll_widget)
        root.addWidget(self.scroll_area, 1)

        # Action buttons (fixed at the bottom)
        action_widget = QWidget()
        action_layout = QVBoxLayout(action_widget)
        action_layout.setContentsMargins(SPACING_8, 0, SPACING_8, SPACING_8)
        action_layout.setSpacing(SPACING_8)

        action_title = QLabel("動作")
        action_title.setProperty("class", "sectionTitle")
        action_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        action_layout.addWidget(action_title)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(SPACING_8)

        self.target_btn = QPushButton("下一步")
        self.target_btn.setObjectName("nextStepBtn")
        self.target_btn.setMinimumHeight(SIDEBAR_BUTTON_MIN_HEIGHT)
        self.target_btn.setToolTip("依流程前往下一頁（Ctrl+Right）")
        self.target_btn.setEnabled(True)

        self.refresh_btn = QPushButton("重新分析")
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setMinimumHeight(SIDEBAR_BUTTON_MIN_HEIGHT)
        self.refresh_btn.setToolTip("依目前條件重新執行 SPC 統計（Ctrl+R）")

        btn_layout.addWidget(self.target_btn)
        btn_layout.addWidget(self.refresh_btn)
        action_layout.addLayout(btn_layout)
        
        root.addWidget(action_widget)

    def sync_feature_states(self, selected: list) -> None:
        """Update sidebar feature button checked states; selected is a subset of ['Height','Area','Volume']."""
        for btn, col in (
            (self._btn_height, "Height"),
            (self._btn_area, "Area"),
            (self._btn_volume, "Volume"),
        ):
            btn.blockSignals(True)
            try:
                btn.setChecked(col in selected)
            finally:
                btn.blockSignals(False)

    def set_feature_section_visible(self, visible: bool) -> None:
        """Enable or disable the feature toggle section (enabled after measurement data is loaded)."""
        self._feature_section.setEnabled(visible)

    def set_condition_section_collapsed(self, collapsed: bool) -> None:
        """Hide filters when sidebar height is too tight while preserving their selected values."""
        if collapsed == self._condition_section_collapsed:
            return
        self._condition_section_collapsed = collapsed
        self._condition_title.setText("分析條件（已收合）" if collapsed else "分析條件")
        self._condition_container.setVisible(not collapsed)
        self._condition_summary.setVisible(collapsed)

    def _toggle_collapse(self) -> None:
        """Manually toggle the collapsed state of the condition section and mark as user toggled."""
        self._user_toggled = True
        self.set_condition_section_collapsed(not self._condition_section_collapsed)

    def _on_range_changed(self, text: str) -> None:
        """Toggle board-specify combo visibility based on range selection."""
        is_specify = text == RANGE_SPECIFY
        self.board_specify_label.setVisible(is_specify)
        self.board_specify_combo.setVisible(is_specify)

    def _ensure_combo_only_refdes_filter(self) -> None:
        """The component-name/refdes filter uses a dropdown only; do not keep a QLineEdit in that slot."""
        self.refdes_combo.setEditable(False)
        combo_line_edit = self.refdes_combo.lineEdit()
        if combo_line_edit is not None:
            combo_line_edit.setParent(None)
            combo_line_edit.deleteLater()
        item = self._condition_grid.itemAtPosition(2, 1)
        if item is not None and item.widget() is not self.refdes_combo:
            widget = item.widget()
            if widget is not None:
                self._condition_grid.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
            self._condition_grid.addWidget(self.refdes_combo, 2, 1)

    def _on_optional_filter_changed(self) -> None:
        """Emit signal when any optional filter value changes."""
        self.optional_filters_changed.emit()

    def get_optional_filters(self) -> dict:
        """Return product, time_start, time_end, line for SessionStore and filter_analysis_df."""
        if self.optional_filter_widget.isHidden():
            return {"product": None, "time_start": None, "time_end": None, "line": None}
        product: str | None = self.product_combo.currentText()
        if product == FILTER_ALL:
            product = None
        time_start: str | None = self.time_start_edit.text().strip() or None
        time_end: str | None = self.time_end_edit.text().strip() or None
        line: str | None = self.line_combo.currentText()
        if line == FILTER_ALL:
            line = None
        return {"product": product, "time_start": time_start, "time_end": time_end, "line": line}

    def populate_optional_filters(self, df) -> None:
        """Show and populate product/time/line combos only when df has corresponding columns."""
        if df is None or df.empty:
            self.optional_filter_widget.setVisible(False)
            return
        has_product = any(c in df.columns for c in _OPTIONAL_FILTER_COL_PRODUCT)
        has_time = any(c in df.columns for c in _OPTIONAL_FILTER_COL_TIME)
        has_line = any(c in df.columns for c in _OPTIONAL_FILTER_COL_LINE)
        if not (has_product or has_time or has_line):
            self.optional_filter_widget.setVisible(False)
            return
        self.optional_filter_widget.setVisible(True)
        self.product_combo.blockSignals(True)
        self.line_combo.blockSignals(True)
        try:
            self.product_combo.clear()
            self.line_combo.clear()
            if has_product:
                col = next(c for c in _OPTIONAL_FILTER_COL_PRODUCT if c in df.columns)
                products = [str(x) for x in df[col].dropna().unique()]
                self.product_combo.addItems([FILTER_ALL] + sorted(products))
            else:
                self.product_combo.addItem(FILTER_ALL)
            if has_line:
                col = next(c for c in _OPTIONAL_FILTER_COL_LINE if c in df.columns)
                lines = [str(x) for x in df[col].dropna().unique()]
                self.line_combo.addItems([FILTER_ALL] + sorted(lines))
            else:
                self.line_combo.addItem(FILTER_ALL)
        finally:
            self.product_combo.blockSignals(False)
            self.line_combo.blockSignals(False)

    def populate_conditions(self, df) -> None:
        """Extracts unique categories from the dataframe to make Analysis Conditions selectable."""
        # Use blockSignals to avoid triggering unwanted refreshes during mass update
        self.board_specify_combo.blockSignals(True)
        self.refdes_combo.blockSignals(True)
        self.part_type_combo.blockSignals(True)
        
        try:
            self.board_specify_combo.clear()
            self.refdes_combo.clear()
            self.part_type_combo.clear()

            if df is None or df.empty:
                self.refdes_combo.addItem(FILTER_ALL)
                self.part_type_combo.addItem(FILTER_ALL)
                return

            # Populate board_specify_combo with actual board IDs (used when RANGE_SPECIFY is selected)
            board_col = None
            if "BoardNo" in df.columns:
                board_col = "BoardNo"
            elif "PanelId" in df.columns:
                board_col = "PanelId"
            if board_col:
                boards = [str(x) for x in df[board_col].dropna().unique()]
                self.board_specify_combo.addItems(sorted(boards))

            # Populate RefDes combo
            if "RefDes" in df.columns:
                refdes_list = [str(x) for x in df["RefDes"].dropna().unique()]
                self.refdes_combo.addItems([FILTER_ALL] + sorted(refdes_list))
            else:
                self.refdes_combo.addItem(FILTER_ALL)

            # Populate PartType combo
            if "PartType" in df.columns:
                part_types = [str(x) for x in df["PartType"].dropna().unique()]
                self.part_type_combo.addItems([FILTER_ALL] + sorted(part_types))
            else:
                self.part_type_combo.addItem(FILTER_ALL)

        finally:
            self.board_specify_combo.blockSignals(False)
            self.refdes_combo.blockSignals(False)
            self.part_type_combo.blockSignals(False)
