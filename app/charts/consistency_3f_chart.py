from app.charts.base_chart import BaseChart
from typing import Dict, Any
from app.ui.theme.tokens import CHART_BAR_NEUTRAL, CHART_NEUTRAL_LINE


class Consistency3FChart(BaseChart):
    """Standardized residual chart: z(V/A) - z(Height)."""

    def __init__(self, parent=None):
        super().__init__(parent, title="多特徵一致性 (z(V/A) vs z(Height))", xlabel="樣本序", ylabel="z(V/A) − z(Height)", figsize=(6, 4))

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        data = engine_output.get("data", {})
        diff_va_h = data.get("diff_va_h", [])
        indices = data.get("indices", [])
        if not diff_va_h:
            self._show_placeholder("無一致性差異資料")
            return False
        x_values = indices if isinstance(indices, list) and len(indices) == len(diff_va_h) else list(range(len(diff_va_h)))
        self.ax.bar(x_values, diff_va_h, color=CHART_BAR_NEUTRAL, alpha=0.75, edgecolor="none")
        self.ax.axhline(0, color=CHART_NEUTRAL_LINE, linestyle="-", linewidth=1)
        self.ax.set_xlabel("樣本序 (PCB Run Order)")
        self.ax.set_ylabel("z(V/A) − z(Height)")
        # layout handled by BaseChart
        self.canvas.draw()
        return True

