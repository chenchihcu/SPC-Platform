from app.charts.base_chart import BaseChart, annotate_latest_point, draw_reference_line, resolve_target_col, scatter_state_points
from typing import Dict, Any
from app.ui.theme.tokens import CHART_SERIES, CHART_FONT_LEGEND
class EWMAChart(BaseChart):
    """Renders EWMA control chart (exponentially weighted moving average)."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="EWMA 管制圖",
            xlabel="樣本序 (PCB Run Order)",
            ylabel="EWMA 值",
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        target_col = resolve_target_col(engine_output)
        if target_col:
            self.ax.set_ylabel(f"EWMA ({target_col})")
        data = engine_output.get("data", {})
        stats = engine_output.get("statistics", {})
        values = data.get("values", [])
        indices = data.get("indices", list(range(len(values))))
        ooc = data.get("out_of_control_indices", [])
        cl = stats.get("cl", 0)
        ucl = stats.get("ucl", 0)
        lcl = stats.get("lcl", 0)
        self.ax.plot(indices, values, color=CHART_SERIES, linestyle="-", linewidth=1.5, label="EWMA")
        if ooc:
            idx_to_pos = {idx: i for i, idx in enumerate(indices)}
            ooc_vals = [values[idx_to_pos[idx]] for idx in ooc if idx in idx_to_pos]
            ooc_idx = [idx for idx in ooc if idx in idx_to_pos]
            if ooc_idx and ooc_vals:
                scatter_state_points(self.ax, ooc_idx, ooc_vals, state="ooc", label="OOC")
        annotate_latest_point(self.ax, indices, values, label="Latest", color=CHART_SERIES)
        draw_reference_line(self.ax, cl, f"CL: {cl:.2f}", semantic="centerline")
        draw_reference_line(self.ax, ucl, f"UCL: {ucl:.2f}", semantic="control_limit")
        draw_reference_line(self.ax, lcl, f"LCL: {lcl:.2f}", semantic="control_limit")
        self.ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
        # layout handled by BaseChart
        self.canvas.draw()
        return True
