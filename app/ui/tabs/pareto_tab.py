from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from app.charts.pareto_chart import ParetoChart
from app.analytics.chart_registry import format_chart_description, format_chart_description_compact
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

        self.chart_view.draw_chart(pareto_json_output)
