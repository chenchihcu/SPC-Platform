from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt
from app.charts.control_chart import ControlChart
from app.analytics.chart_registry import format_chart_description_compact
from app.ui.theme.tokens import CHART_DESC_MIN_HEIGHT, SPACING_SM

class ControlChartTab(QWidget):
    """
    Renders the I-MR / Xbar Control Chart view within the Analysis Workspace.
    Feature selection is handled by the top toolbar (高度/面積/體積).
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        self.lbl_desc = QLabel(format_chart_description_compact("imr"))
        self.lbl_desc.setWordWrap(False)
        self.lbl_desc.setProperty("class", "chartDescCompact")
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_desc.setMinimumHeight(CHART_DESC_MIN_HEIGHT)
        self.lbl_desc.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.lbl_desc)

        self.chart_view = ControlChart(self)
        layout.addWidget(self.chart_view, 1)

        self._last_payload: dict = {}

    def update_data(self, spc_json_output: dict) -> None:
        """Called by the presenter/viewmodel to render new outputs"""
        self._last_payload = spc_json_output or {}

        ctx = (spc_json_output or {}).get("analysis_context", {})
        self.lbl_desc.setText(format_chart_description_compact("imr", {"target_col": ctx.get("target_col")}))

        self.chart_view.draw_chart(spc_json_output)
