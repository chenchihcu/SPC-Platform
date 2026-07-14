from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PySide6.QtCore import Qt, Signal
from app.charts.pareto_chart import ParetoChart
from app.analytics.chart_registry import (
    CHART_GROUP_VARIANT_LABELS,
    format_chart_description,
    format_chart_description_compact,
    select_chart_group_variant,
)
from app.ui.theme.tokens import SPACING_SM

class ParetoTab(QWidget):
    """
    Renders Pareto analysis charting and 80/20 cumulative checks.
    When chart is in component mode, clicking a bar emits component_selected(component_id).
    Feature selection is handled by the top toolbar (高度/面積/體積).
    """
    component_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        self.lbl_desc = QLabel(format_chart_description_compact("pareto"))
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setProperty("class", "chartDescCompact")

        self.lbl_desc.setToolTip(format_chart_description("pareto"))
        self.lbl_desc.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self.lbl_desc)

        self._group_row = QWidget(self)
        group_layout = QHBoxLayout(self._group_row)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(QLabel("分組方式："))
        self.group_combo = QComboBox(self._group_row)
        self.group_combo.setAccessibleName("柏拉圖分組方式")
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        group_layout.addWidget(self.group_combo)
        group_layout.addStretch(1)
        self._group_row.setVisible(False)
        layout.addWidget(self._group_row)

        self.chart_view = ParetoChart(self)
        self.chart_view.component_selected.connect(self.component_selected.emit)
        layout.addWidget(self.chart_view, 1)

        self._last_payload: dict = {}

    def update_data(self, pareto_json_output: dict) -> None:
        """Update the view with new data payload."""
        self._last_payload = pareto_json_output or {}

        ctx = (pareto_json_output or {}).get("analysis_context", {})
        desc_ctx = {"target_col": ctx.get("target_col")}
        self.lbl_desc.setText(format_chart_description_compact("pareto", desc_ctx))
        self.lbl_desc.setToolTip(format_chart_description("pareto", desc_ctx))

        self._refresh_group_selector()
        self.chart_view.draw_chart(
            select_chart_group_variant(self._last_payload, self.group_combo.currentData())
        )

    def _refresh_group_selector(self) -> None:
        previous = self.group_combo.currentData() or "default"
        variants = self._last_payload.get("_group_variants", {})
        keys = ["default", *[key for key in ("pad", "image") if key in variants]]
        self.group_combo.blockSignals(True)
        try:
            self.group_combo.clear()
            for key in keys:
                self.group_combo.addItem(CHART_GROUP_VARIANT_LABELS[key], key)
            selected = self.group_combo.findData(previous)
            self.group_combo.setCurrentIndex(selected if selected >= 0 else 0)
        finally:
            self.group_combo.blockSignals(False)
        self._group_row.setVisible(len(keys) > 1)

    def _on_group_changed(self, _index: int) -> None:
        if not self._last_payload:
            return
        self.chart_view.draw_chart(
            select_chart_group_variant(self._last_payload, self.group_combo.currentData())
        )
