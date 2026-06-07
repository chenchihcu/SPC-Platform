from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout
from PySide6.QtCore import Qt
from app.charts.heatmap_chart import HeatmapChart
from app.analytics.chart_registry import format_chart_description, format_chart_description_compact
from app.analytics.spatial_engine import SpatialEngine
from app.ui.theme.tokens import SPACING_SM, CHART_MAIN_MIN_HEIGHT

_HEATMAP_MODE_LABELS = {
    SpatialEngine.MODE_VALUE: "量測值 (Value)",
    SpatialEngine.MODE_UCL_DENSITY: "UCL 違反密度",
    SpatialEngine.MODE_LCL_DENSITY: "LCL 違反密度",
    SpatialEngine.MODE_OOS_DENSITY: "OOS 密度",
    SpatialEngine.MODE_VOLUME_DEVIATION: "偏離平均",
}

class SpatialTab(QWidget):
    """
    Renders Spatial / PCB Heatmap with parameter selector and mode selector (value, UCL/LCL/OOS density, deviation).
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        self.lbl_desc = QLabel(format_chart_description_compact("spatial_heatmap"))
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setProperty("class", "chartDescCompact")

        self.lbl_desc.setToolTip(format_chart_description("spatial_heatmap"))
        self.lbl_desc.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self.lbl_desc)

        self.mode_combo = QComboBox()
        self.mode_combo.setToolTip("選擇熱圖著色模式")
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self._mode_label = QLabel("熱圖模式：")
        self._mode_label.setProperty("class", "formLabel")
        row = QHBoxLayout()
        row.addWidget(self._mode_label)
        row.addWidget(self.mode_combo)
        row.addStretch()
        layout.addLayout(row)

        self.chart_view = HeatmapChart(self)
        self.chart_view.setMinimumHeight(CHART_MAIN_MIN_HEIGHT)
        layout.addWidget(self.chart_view, 1)

        self._last_payload: dict = {}
        self._mode_key_for_display: dict = {}

    def _on_mode_changed(self) -> None:
        mode_key = getattr(self, "_mode_key_for_display", {}).get(self.mode_combo.currentText())
        if mode_key is None or not self._last_payload:
            return
        modes = self._last_payload.get("modes", {})
        if mode_key not in modes:
            return
        payload = dict(self._last_payload)
        payload["data"] = modes[mode_key]
        payload["metadata"] = dict(payload.get("metadata", {}))
        payload["metadata"]["mode"] = mode_key
        self.chart_view.draw_chart(payload)
        
    def update_data(self, spatial_json: dict) -> None:
        """Update the view with new data payload."""
        self._last_payload = spatial_json or {}
        ctx = (spatial_json or {}).get("analysis_context", {})
        desc_ctx = {"target_col": ctx.get("target_col")}
        self.lbl_desc.setText(format_chart_description_compact("spatial_heatmap", desc_ctx))
        self.lbl_desc.setToolTip(format_chart_description("spatial_heatmap", desc_ctx))

        # Display main chart
        modes = self._last_payload.get("modes", {})
        self.mode_combo.blockSignals(True)
        try:
            self.mode_combo.clear()
            self._mode_key_for_display = {}
            for key in SpatialEngine.HEATMAP_MODES:
                if key in modes:
                    label = _HEATMAP_MODE_LABELS.get(key, key)
                    self.mode_combo.addItem(label)
                    self._mode_key_for_display[label] = key
        finally:
            self.mode_combo.blockSignals(False)
        if self._last_payload.get("data"):
            self.chart_view.draw_chart(self._last_payload)
        elif modes:
            first_key = next(iter(modes))
            payload = dict(self._last_payload)
            payload["data"] = modes[first_key]
            payload["metadata"] = dict(payload.get("metadata", {}))
            payload["metadata"]["mode"] = first_key
            self.chart_view.draw_chart(payload)
