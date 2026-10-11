from __future__ import annotations

from typing import Any, Dict

from app.charts.base_chart import BaseChart, annotate_latest_point, draw_reference_line
from app.charts.run_order_axis import marker_points, series_axis
from app.ui.theme.tokens import CHART_OOC, CHART_SERIES, CHART_FONT_ANNOTATION

# Above this many points a full-weight line over oscillating data fills the axis
# into a solid band and buries the rule-hit markers; thin it out instead.
_DENSE_SERIES_THRESHOLD = 300


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
        labels = list(data.get("indices", []))
        values = list(data.get("values", []))
        hit_indices = list(data.get("hit_indices", []))
        if not labels or not values:
            self._show_placeholder("型態辨識資料不足")
            return False
        # X = 1-based position in analysis order; labels only locate rule hits.
        indices, label_pos = series_axis(labels, len(values))

        if len(values) > _DENSE_SERIES_THRESHOLD:
            # Dense series: connecting wildly oscillating points fills the axis into a
            # solid band. Drop the line and show a faint scatter so the rule-hit
            # markers and distribution stay legible.
            self.ax.plot(indices, values, color=CHART_SERIES, linestyle="none",
                         marker="o", markersize=1.5, alpha=0.25, label="Series")
        else:
            self.ax.plot(indices, values, color=CHART_SERIES, linewidth=1.2, label="Series")
        hit_x, hit_y = marker_points(hit_indices, label_pos, values, indices)
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
