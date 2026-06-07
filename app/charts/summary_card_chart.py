from __future__ import annotations

from typing import Any, Dict

from app.charts.base_chart import BaseChart
from app.ui.theme.tokens import CHART_FONT_ANNOTATION, TEXT_PRIMARY


class SummaryCardChart(BaseChart):
    """Simple summary-card chart for textual analysis payloads."""

    def __init__(self, parent=None, *, title: str = "Analysis Summary"):
        super().__init__(parent, title=title, xlabel="", ylabel="", figsize=(6, 3))

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render summary bullet lines from the analysis payload."""
        if not super().draw_chart(engine_output):
            return False
        data = engine_output.get("data") or {}
        lines = list(data.get("summary_lines", []))
        if not lines:
            self._show_placeholder("無摘要資料。")
            return False
        self.ax.set_axis_off()
        top = 0.95
        step = 0.18
        for i, line in enumerate(lines[:5]):
            self.ax.text(
                0.02,
                top - i * step,
                f"- {line}",
                transform=self.ax.transAxes,
                fontsize=CHART_FONT_ANNOTATION + 1,
                color=TEXT_PRIMARY,
                va="top",
            )
        # layout handled by BaseChart
        self.canvas.draw()
        return True
