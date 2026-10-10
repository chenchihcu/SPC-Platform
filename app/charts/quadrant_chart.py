from app.charts.base_chart import BaseChart
from typing import Dict, Any
from app.ui.theme.tokens import (
    CHART_BAR_NEUTRAL,
    CHART_FONT_LEGEND,
    CHART_LINE_STYLE_SECONDARY,
    CHART_NEUTRAL_LINE,
    CHART_QUADRANT_Q1,
    CHART_QUADRANT_Q2,
    CHART_QUADRANT_Q3,
    CHART_QUADRANT_Q4,
)

_QUADRANT_STYLE = {
    1: (CHART_QUADRANT_Q1, "Q1 高X高Y"),
    2: (CHART_QUADRANT_Q2, "Q2 低X高Y"),
    3: (CHART_QUADRANT_Q3, "Q3 低X低Y"),
    4: (CHART_QUADRANT_Q4, "Q4 高X低Y"),
}


class QuadrantChart(BaseChart):
    """Four-quadrant scatter with center lines."""

    def __init__(self, parent=None):
        super().__init__(parent, title="四象限分類 (Quadrant)", xlabel="X", ylabel="Y", figsize=(6, 4))

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        data = engine_output.get("data", {})
        meta = engine_output.get("metadata", {})
        col_x = meta.get("col_x", "X")
        col_y = meta.get("col_y", "Y")
        self.ax.set_xlabel(col_x)
        self.ax.set_ylabel(col_y)
        x_vals = data.get("x", [])
        y_vals = data.get("y", [])
        center_x = data.get("center_x")
        center_y = data.get("center_y")
        if not x_vals or not y_vals:
            self._show_placeholder("無資料")
            return False
        if center_x is not None:
            self.ax.axvline(center_x, color=CHART_NEUTRAL_LINE, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1)
        if center_y is not None:
            self.ax.axhline(center_y, color=CHART_NEUTRAL_LINE, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1)
        quadrants = data.get("quadrant") or []
        if len(quadrants) == len(x_vals) == len(y_vals):
            for q, (color, label) in _QUADRANT_STYLE.items():
                idx = [i for i, qq in enumerate(quadrants) if qq == q]
                if not idx:
                    continue
                self.ax.scatter(
                    [x_vals[i] for i in idx], [y_vals[i] for i in idx],
                    alpha=0.65, s=20, color=color, edgecolors="none",
                    label=f"{label} ({len(idx)})",
                )
            self.ax.legend(loc="best", fontsize=CHART_FONT_LEGEND)
        else:
            self.ax.scatter(x_vals, y_vals, alpha=0.65, s=20, color=CHART_BAR_NEUTRAL, edgecolors="none")
        # layout handled by BaseChart
        self.canvas.draw()
        return True

