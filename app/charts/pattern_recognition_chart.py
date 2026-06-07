from __future__ import annotations

from typing import Any, Dict

from app.charts.base_chart import BaseChart, annotate_latest_point, draw_reference_line
from app.ui.theme.tokens import CHART_OOC, CHART_SERIES, CHART_FONT_ANNOTATION


class PatternRecognitionChart(BaseChart):
    """Line chart with Nelson-rule hit markers and summary."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Pattern Recognition (Nelson Rules)",
            xlabel="樣本序 (PCB Run Order)",
            ylabel="Value",
            figsize=(6, 4),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render Nelson-rule hit markers and summary annotation on the series."""
        if not super().draw_chart(engine_output):
            return False

        data = engine_output.get("data") or {}
        stats = engine_output.get("statistics") or {}
        indices = list(data.get("indices", []))
        values = list(data.get("values", []))
        hit_indices = set(data.get("hit_indices", []))
        if not indices or not values:
            self._show_placeholder("Pattern recognition 資料不足。")
            return False

        self.ax.plot(indices, values, color=CHART_SERIES, linewidth=1.2, label="Series")
        hit_x = [idx for idx in indices if idx in hit_indices]
        idx_to_pos = {idx: i for i, idx in enumerate(indices)}
        hit_y = [values[idx_to_pos[idx]] for idx in hit_x]
        if hit_x:
            self.ax.scatter(hit_x, hit_y, color=CHART_OOC, s=24, zorder=5, label="Rule Hit")
        annotate_latest_point(self.ax, indices, values, label="Latest", color=CHART_SERIES)

        mean = stats.get("mean")
        if mean is not None:
            draw_reference_line(
                self.ax,
                float(mean),
                f"Mean: {float(mean):.3f}",
                semantic="centerline",
            )

        rule_count = int(stats.get("rule_count") or 0)
        hit_count = int(stats.get("hit_point_count") or 0)
        self.ax.annotate(
            f"Rules hit: {rule_count}, Hit points: {hit_count}",
            xy=(0.01, 0.98),
            xycoords="axes fraction",
            va="top",
            fontsize=CHART_FONT_ANNOTATION,
        )
        self.ax.legend(loc="lower right")
        # layout handled by BaseChart
        self.canvas.draw()
        return True
