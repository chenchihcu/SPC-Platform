from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from typing import Optional
from app.charts.histogram_chart import HistogramChart
from app.analytics.chart_registry import format_chart_description, format_chart_description_compact
from app.ui.theme.tokens import SPACING_SM


class DistributionCapabilityTab(QWidget):
    """
    Renders Histogram distribution and normal overlay for capability analysis.
    Feature selection is handled by the top toolbar (高度/面積/體積).

    Supports two modes forwarded from ChartAnalysisPage:
    - Single-feature : original behaviour; histogram + normal curve + USL/LSL + Cpk.
    - Multi-feature  : 1×N subplots via HistogramChart._draw_multi_feature().
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        self.lbl_desc = QLabel(format_chart_description_compact("histogram_spec"))
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setProperty("class", "chartDescCompact")

        self.lbl_desc.setToolTip(format_chart_description("histogram_spec"))
        self.lbl_desc.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self.lbl_desc)

        self.chart_view = HistogramChart(self)
        layout.addWidget(self.chart_view, 1)

        self._last_payload: dict = {}

    def update_data(self, dist_json_output: dict, cap_json: Optional[dict] = None) -> None:
        """Dispatch to multi-feature or single-feature rendering."""
        self._last_payload = dist_json_output or {}

        if self._last_payload.get("_multi_feature"):
            self._update_multi_feature(self._last_payload)
        else:
            self._update_single_feature(dist_json_output, cap_json)

    def _update_multi_feature(self, data: dict) -> None:
        features = data.get("_features", [])
        desc_ctx = {"selected_features": features}
        self.lbl_desc.setText(format_chart_description_compact("histogram_spec", desc_ctx))
        self.lbl_desc.setToolTip(format_chart_description("histogram_spec", desc_ctx))
        self.chart_view.draw_chart(data)

    def _update_single_feature(self, dist_json_output: dict, cap_json: Optional[dict]) -> None:
        combined = dict(dist_json_output) if dist_json_output else {}
        if cap_json:
            meta = cap_json.get("metadata", {})
            combined["usl"] = meta.get("usl")
            combined["lsl"] = meta.get("lsl")
        ctx = combined.get("analysis_context", {})
        desc_ctx = {"target_col": ctx.get("target_col")}
        self.lbl_desc.setText(format_chart_description_compact("histogram_spec", desc_ctx))
        self.lbl_desc.setToolTip(format_chart_description("histogram_spec", desc_ctx))
        self.chart_view.draw_chart(combined)
