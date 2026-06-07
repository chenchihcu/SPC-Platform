"""
I-MR + Histogram split view: horizontal QSplitter with Control Chart ~65% and Histogram ~35%.
Receives full payload and passes imr slice to control tab and histogram_spec slice to dist tab.
Shows component analysis context (PartType) when filtering by component.
"""
from PySide6.QtWidgets import QWidget, QSplitter, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from app.analytics.chart_registry import get_payload_slice
from app.ui.tabs.control_chart_tab import ControlChartTab
from app.ui.tabs.distribution_capability_tab import DistributionCapabilityTab
from app.utils.constants import FILTER_ALL
from app.ui.theme.tokens import IMR_HISTOGRAM_TAB_MIN_W


class ImrHistogramSplitPage(QWidget):
    """
    Left 65%: Control Chart (I-MR). Right 35%: Histogram (distribution/capability).
    update_data(payload) expects full payload; updates both children from payload slices.
    Shows "目前為元件分析：PartType X" when _ctx_part_type is set (component SPC context).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._ctx_label = QLabel()
        self._ctx_label.setProperty("class", "caption")
        self._ctx_label.setVisible(False)
        layout.addWidget(self._ctx_label)
        self._control_tab = ControlChartTab(self)
        self._histogram_tab = DistributionCapabilityTab(self)
        self._split = QSplitter(Qt.Orientation.Horizontal)
        self._split.addWidget(self._control_tab)
        self._split.addWidget(self._histogram_tab)
        # Default 65% control, 35% histogram.
        self._split.setStretchFactor(0, 65)
        self._split.setStretchFactor(1, 35)
        # Keep histogram readable under narrow window widths.
        self._split.setChildrenCollapsible(False)
        self._histogram_tab.setMinimumWidth(IMR_HISTOGRAM_TAB_MIN_W)
        layout.addWidget(self._split, 1)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Adjust chart split layout on widget resize."""
        super().resizeEvent(event)
        # Re-apply intended ratio when the split is first laid out.
        sizes = self._split.sizes()
        if len(sizes) == 2 and all(s == 0 for s in sizes):
            total = max(1, self._split.width())
            left = int(total * 0.65)
            right = max(1, total - left)
            self._split.setSizes([left, right])

    def update_data(self, payload: dict) -> None:
        """Update both charts from full payload (imr slice -> control, histogram_spec slice -> histogram)."""
        part_type = (payload or {}).get("_ctx_part_type", "")
        if part_type and part_type != FILTER_ALL:
            self._ctx_label.setText("目前為元件分析：" + str(part_type))
            self._ctx_label.setVisible(True)
        else:
            self._ctx_label.setVisible(False)
        if not payload:
            self._control_tab.update_data({})
            self._histogram_tab.update_data({}, None)
            return
        imr_slice = get_payload_slice(payload, "imr")
        hist_slice = get_payload_slice(payload, "histogram_spec")
        self._control_tab.update_data(imr_slice)
        # DistributionCapabilityTab.update_data(dist_json, cap_json=None); merged slice has usl/lsl
        self._histogram_tab.update_data(hist_slice, None)
