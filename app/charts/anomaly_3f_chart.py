from app.charts.base_chart import BaseChart
from typing import Dict, Any
from app.ui.theme.tokens import CHART_BAR_NEUTRAL


class Anomaly3FChart(BaseChart):
    """Bar or line chart of composite 3-feature anomaly score per point."""

    def __init__(self, parent=None):
        super().__init__(parent, title="三特徵異常分數 (3-Feature Anomaly Score)", xlabel="樣本序", ylabel="異常分數", figsize=(6, 4))

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        data = engine_output.get("data", {})
        scores = data.get("scores", [])
        indices = data.get("indices", [])
        if not scores:
            self._show_placeholder("無異常分數資料")
            return False
        x_values = indices if isinstance(indices, list) and len(indices) == len(scores) else list(range(len(scores)))
        self.ax.bar(x_values, scores, color=CHART_BAR_NEUTRAL, alpha=0.75, edgecolor="none")
        self.ax.set_xlabel("樣本序 (PCB Run Order)")
        self.ax.set_ylabel("異常分數 (Anomaly Score)")
        # layout handled by BaseChart
        self.canvas.draw()
        return True

