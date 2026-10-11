from app.charts.base_chart import BaseChart, annotate_latest_point, draw_reference_line, resolve_target_col
from typing import Dict, Any
from app.ui.theme.tokens import CHART_SERIES, CHART_FONT_LEGEND

# Above this many points a connecting line over oscillating data fills the axis
# into an unreadable band; render translucent markers-only instead.
_DENSE_SERIES_THRESHOLD = 300


class RunChart(BaseChart):
    """Run chart: individual values in run order with center line."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Run Chart（趨勢圖）",
            xlabel="樣本序 (PCB Run Order)",
            ylabel="量測值",
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        target_col = resolve_target_col(engine_output)
        if target_col:
            self.ax.set_ylabel(f"量測值 ({target_col})")
        data = engine_output.get("data", {})
        stats = engine_output.get("statistics", {})
        values = data.get("values", [])
        indices = data.get("indices", list(range(len(values))))
        center = stats.get("center_line", 0)
        if len(values) > _DENSE_SERIES_THRESHOLD:
            # Dense series: markers-only so oscillation doesn't fill the axis.
            self.ax.plot(indices, values, color=CHART_SERIES, linestyle="none",
                         marker="o", markersize=2, alpha=0.35, label="個別值")
        else:
            self.ax.plot(indices, values, color=CHART_SERIES, linestyle="-",
                         linewidth=1, marker="o", markersize=3, label="個別值")
        annotate_latest_point(self.ax, indices, values, label="Latest", color=CHART_SERIES)
        draw_reference_line(self.ax, center, f"中心線: {center:.2f}", semantic="centerline")
        self.ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
        # layout handled by BaseChart
        self.canvas.draw()
        return True
