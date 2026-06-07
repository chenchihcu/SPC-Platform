from app.charts.base_chart import BaseChart
from typing import Dict, Any
import numpy as np
from app.ui.theme.tokens import CHART_SERIES


class ParallelCoordChart(BaseChart):
    """Parallel coordinates: one line per row across 3 feature axes."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Parallel Coordinates（平行座標）",
            xlabel="",
            ylabel="正規化值",
            figsize=(7, 4),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        data = engine_output.get("data", {})
        columns = data.get("columns", [])
        values = data.get("values", [])
        if not columns or not values:
            self._show_placeholder("無資料")
            return False
        n_axes = len(columns)
        x_pos = np.arange(n_axes)
        self.ax.set_xticks(x_pos)
        self.ax.set_xticklabels(columns, rotation=30, ha="right")
        self.ax.set_ylim(-0.05, 1.05)
        alpha = 0.15 if len(values) > 100 else 0.4
        for row in values:
            if len(row) == n_axes:
                self.ax.plot(x_pos, row, color=CHART_SERIES, alpha=alpha, linewidth=0.8)
        stats = engine_output.get("statistics", {})
        if stats.get("sampled_for_display"):
            shown = stats.get("displayed_n", len(values))
            total = stats.get("n", len(values))
            basis = stats.get("normalization_basis", "full_valid_data")
            self.ax.annotate(
                f"顯示抽樣: {shown}/{total}（正規化基準: {basis}）",
                xy=(0.01, 0.97),
                xycoords="axes fraction",
                fontsize=9,
                color=CHART_SERIES,
                va="top",
            )
        # layout handled by BaseChart
        self.canvas.draw()
        return True

