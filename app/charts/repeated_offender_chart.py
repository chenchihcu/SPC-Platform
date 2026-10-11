from app.charts.base_chart import BaseChart, resolve_target_col, build_sparse_tick_labels
from typing import Dict, Any
import numpy as np
from app.ui.theme.tokens import CHART_BAR_FAIL, CHART_FILL_EDGE


class RepeatedOffenderChart(BaseChart):
    """Bar chart of RefDes ranked by violation count (repeated offenders)."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Repeated Offender（違規次數排名）",
            xlabel="RefDes",
            ylabel="違規次數",
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        target_col = resolve_target_col(engine_output)
        data = engine_output.get("data", {})
        labels = data.get("labels", [])
        counts = data.get("counts", [])
        if not labels or not counts:
            self._show_placeholder("無違規紀錄")
            return False
        x = np.arange(len(labels))
        self.ax.bar(x, counts, color=CHART_BAR_FAIL, edgecolor=CHART_FILL_EDGE, linewidth=0.5)
        self.ax.set_xticks(x)
        display_labels = build_sparse_tick_labels(labels, threshold=30, step_small=5, step_large=10)
        self.ax.set_xticklabels(display_labels, rotation=45, ha="right")
        if target_col:
            self.ax.set_ylabel(f"違規次數 ({target_col})")
        # layout handled by BaseChart
        self.canvas.draw()
        return True

