from app.charts.base_chart import BaseChart, resolve_target_col, build_sparse_tick_labels
from typing import Dict, Any
import numpy as np
from app.ui.theme.tokens import CHART_BAR_FAIL, CHART_FILL_EDGE, CHART_ANNOTATION, CHART_FONT_ANNOTATION


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
            self._show_placeholder("無違規紀錄或無資料 (No Violations)")
            return False
        x = np.arange(len(labels))
        self.ax.bar(x, counts, color=CHART_BAR_FAIL, edgecolor=CHART_FILL_EDGE, linewidth=0.5)
        self.ax.set_xticks(x)
        display_labels = build_sparse_tick_labels(labels, threshold=30, step_small=5, step_large=10)
        self.ax.set_xticklabels(display_labels, rotation=45, ha="right")
        if target_col:
            self.ax.set_ylabel(f"違規次數 ({target_col})")
        stats = engine_output.get("statistics", {})
        if stats.get("sampled_for_display"):
            shown = stats.get("displayed_n", len(labels))
            total = stats.get("n_refdes_with_violations", len(labels))
            top_n = stats.get("top_n")
            top_note = f", top_n={top_n}" if top_n else ""
            self.ax.annotate(
                f"顯示截取: {shown}/{total}{top_note}",
                xy=(0.01, 0.97),
                xycoords="axes fraction",
                fontsize=CHART_FONT_ANNOTATION,
                color=CHART_ANNOTATION,
                va="top",
            )
        # layout handled by BaseChart
        self.canvas.draw()
        return True

