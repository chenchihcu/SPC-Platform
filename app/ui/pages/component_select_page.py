from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QFrame
from PySide6.QtCore import Signal, Qt
from app.ui.theme.tokens import SPACING_16, SPACING_12, SPACING_8, COMPONENT_SUMMARY_KPI_MIN_HEIGHT
from app.ui.widgets.page_templates import page_margins_and_spacing, setup_two_column_form_page, empty_state_label
from app.utils.constants import FEATURE_COLUMNS, FEATURE_DISPLAY_NAMES
from app.data.session_store import SessionStore


class ComponentSelectPage(QWidget):
    """
    Subflow for users to select one or more measurement features for analysis.
    Supports single (1), dual (2), or triple (Volume+Area+Height) selection.
    Uses two-column layout: left = target features, right = summary and hints.
    """
    selection_changed = Signal(list)  # emits list of selected feature column names

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        page_margins_and_spacing(layout)
        page_layout = setup_two_column_form_page(layout, "特徵選擇")

        # Left column: Target Features selection (Audit Item 37: Use QFrame/stepCard instead of QGroupBox)
        group = QFrame()
        group.setObjectName("stepCard")
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        vbox.setSpacing(SPACING_8)

        group_title = QLabel("分析特徵（1～3 項）")
        group_title.setProperty("class", "stepTitle")
        vbox.addWidget(group_title)

        self._checkboxes = {}
        for col in FEATURE_COLUMNS:
            cb = QCheckBox(FEATURE_DISPLAY_NAMES.get(col, col))
            cb.stateChanged.connect(self._on_selection_changed)
            self._checkboxes[col] = cb
            vbox.addWidget(cb)
        left_layout = page_layout.left_column.layout()
        if left_layout is not None:
            left_layout.addWidget(group)

        # Audit Item 117: Set proper tab order for form accessibility
        if len(FEATURE_COLUMNS) >= 3:
            # Connect the three main feature checkboxes in sequence
            self.setTabOrder(self._checkboxes[FEATURE_COLUMNS[0]], self._checkboxes[FEATURE_COLUMNS[1]])
            self.setTabOrder(self._checkboxes[FEATURE_COLUMNS[1]], self._checkboxes[FEATURE_COLUMNS[2]])

        # Right column: summary and hints
        kpi_card = QFrame()
        kpi_card.setObjectName("stepCard")
        kpi_card.setMinimumHeight(COMPONENT_SUMMARY_KPI_MIN_HEIGHT)
        summary_vbox = QVBoxLayout(kpi_card)
        summary_vbox.setContentsMargins(SPACING_16, SPACING_16, SPACING_16, SPACING_16)
        summary_vbox.setSpacing(SPACING_12)
        summary_title = QLabel("已選")
        summary_title.setProperty("class", "stepTitle")
        summary_vbox.addWidget(summary_title)
        self.lbl_count = QLabel("0")
        self.lbl_count.setProperty("class", "kpiValue")
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_vbox.addWidget(self.lbl_count)
        self.lbl_summary = QLabel("—")
        self.lbl_summary.setProperty("class", "caption")
        self.lbl_summary.setWordWrap(True)
        summary_vbox.addWidget(self.lbl_summary)
        right_layout = page_layout.right_column.layout()
        if right_layout is not None:
            right_layout.addWidget(kpi_card)

        # rules_card 已移除：圖表相容性由圖表分析頁動態顯示

        # Empty state overlay when no measurement data loaded
        self._empty_hint = empty_state_label("請先上傳量測資料")
        layout.addWidget(self._empty_hint)
        self._empty_hint.setVisible(False)

        self._store = SessionStore()
        self._sync_from_store()

    def _sync_from_store(self) -> None:
        """Initialize checkboxes from SessionStore.selected_features."""
        selected = list(self._store.selected_features) if self._store.selected_features else []
        for col in FEATURE_COLUMNS:
            self._checkboxes[col].blockSignals(True)
            try:
                self._checkboxes[col].setChecked(col in selected)
            finally:
                self._checkboxes[col].blockSignals(False)
        self._update_summary_and_store(emit=False)

    def _on_selection_changed(self) -> None:
        self._update_summary_and_store(emit=True)

    def toggle_feature(self, col: str) -> None:
        """在目前勾選基礎上切換指定特徵的選取狀態，仍遵守 1～3 項約束。"""
        if col not in FEATURE_COLUMNS:
            return
        cb = self._checkboxes.get(col)
        if cb is None:
            return
        cb.setChecked(not cb.isChecked())

    def _update_summary_and_store(self, emit: bool = True) -> None:
        selected = [col for col in FEATURE_COLUMNS if self._checkboxes[col].isChecked()]
        # Enforce at least one; if user unchecked the last one, re-check it (keep current)
        if not selected:
            # Restore from store or default to first
            prev = list(self._store.selected_features) if self._store.selected_features else [FEATURE_COLUMNS[0]]
            if prev:
                selected = [prev[0]]
                self._checkboxes[selected[0]].setChecked(True)
            else:
                selected = [FEATURE_COLUMNS[0]]
                self._checkboxes[FEATURE_COLUMNS[0]].setChecked(True)
        # Enforce max three: take first three if more than three checked (by order)
        if len(selected) > 3:
            selected = selected[:3]
            for col in FEATURE_COLUMNS:
                if col not in selected:
                    self._checkboxes[col].blockSignals(True)
                    try:
                        self._checkboxes[col].setChecked(False)
                    finally:
                        self._checkboxes[col].blockSignals(False)
        self._store.selected_features = selected
        names = [FEATURE_DISPLAY_NAMES.get(c, c) for c in selected]
        self.lbl_count.setText(str(len(selected)))
        self.lbl_summary.setText(", ".join(names))
        if emit:
            self.selection_changed.emit(selected)

    def refresh_state(self) -> None:
        """Show/hide empty hint based on whether measurement data is loaded."""
        has_data = self._store.meas_df is not None
        self._empty_hint.setVisible(not has_data)

    def get_selected_features(self) -> list:
        """Return list of selected feature column names (e.g. ['Volume', 'Area'])."""
        return [col for col in FEATURE_COLUMNS if self._checkboxes[col].isChecked()]
