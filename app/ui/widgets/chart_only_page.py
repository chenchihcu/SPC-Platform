"""
Single-chart page for Phase 2 stacked workspace.
Compact: 1-line description (caption) above the chart; chart widget fills remaining space.
Full 4-section description available via tooltip on the description label.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from typing import Dict, Any, cast
from app.ui.theme.tokens import SPACING_4


class ChartOnlyPage(QWidget):
    """Holds a compact description label and one chart widget; chart is maximized."""

    def __init__(self, chart_widget: QWidget, description: str, parent=None) -> None:
        super().__init__(parent)
        self._chart = chart_widget
        self._full_description = description  # store full text for tooltip

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_4)

        # Compact description — 1-2 lines, caption size, with full text as tooltip
        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setProperty("class", "chartDescCompact")
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_desc.setToolTip(description)
        layout.addWidget(self.lbl_desc)

        # Chart fills all remaining space
        layout.addWidget(self._chart, 1)

    def update_data(self, data: Dict[str, Any]) -> None:
        """Update the view with new data payload."""
        if hasattr(self._chart, "draw_chart"):
            self._chart.draw_chart(data or {})

    def update_description(self, text: str) -> None:
        """Update the description label. text is compact; full description set via set_full_description."""
        self.lbl_desc.setText(text or "")

    def set_full_description(self, full_text: str) -> None:
        """Update the tooltip with the full 4-section description."""
        self._full_description = full_text
        self.lbl_desc.setToolTip(full_text)


class DistCapPageWrapper(QWidget):
    """Wraps DistributionCapabilityTab so it accepts single merged slice: update_data(slice) -> tab.update_data(slice, None)."""

    def __init__(self, dist_cap_tab: QWidget, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(dist_cap_tab)
        self._tab = dist_cap_tab

    def update_data(self, data: Dict[str, Any]) -> None:
        """Update the view with new data payload."""
        tab = cast(Any, self._tab)
        tab.update_data(data or {}, None)
