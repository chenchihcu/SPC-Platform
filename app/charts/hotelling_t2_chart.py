"""
Hotelling T² multivariate control chart renderer.
Phase 3 P2: multivariate outlier / shift detection.
"""
import numpy as np
from typing import Dict, Any

from app.charts.base_chart import BaseChart
from app.ui.theme.tokens import (
    CHART_ANNOTATION,
    CHART_CONTROL_LIMITS,
    CHART_FONT_ANNOTATION,
    CHART_FONT_LEGEND,
    CHART_LINE_STYLE_SECONDARY,
    CHART_NEUTRAL_LINE,
    CHART_OOC,
    CHART_SERIES,
)


class HotellingT2Chart(BaseChart):
    """Renders Hotelling T² multivariate control chart with UCL."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Hotelling T² 多變量管制圖",
            xlabel="樣本序 (Sample Index)",
            ylabel="T²",
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render T² values with UCL and OOC markers."""
        if not super().draw_chart(engine_output):
            return False

        data = engine_output.get("data", {})
        stats = engine_output.get("statistics", {})

        indices = data.get("indices", [])
        t2_values = data.get("t2_values", [])
        ooc_flags = data.get("ooc_flags", [])

        ucl_value = stats.get("ucl_value", 0.0)
        mean_t2 = stats.get("mean_t2", 0.0)

        # Convert to numpy arrays for boolean indexing
        indices_arr = np.asarray(indices)
        t2_arr = np.asarray(t2_values)
        ooc_arr = np.asarray(ooc_flags, dtype=bool)

        # Main T² series as blue line with circle markers
        self.ax.plot(
            indices_arr,
            t2_arr,
            color=CHART_SERIES,
            linestyle="-",
            linewidth=1,
            marker="o",
            markersize=4,
            label="T²",
        )

        # Upper control limit (UCL) as red dashed line
        self.ax.axhline(
            ucl_value,
            color=CHART_CONTROL_LIMITS,
            linestyle="--",
            linewidth=1.5,
            label=f"UCL: {ucl_value:.2f}",
        )

        # Mean T² as neutral dashed-dot line
        self.ax.axhline(
            mean_t2,
            color=CHART_NEUTRAL_LINE,
            linestyle=CHART_LINE_STYLE_SECONDARY,
            linewidth=0.8,
            label=f"Mean T²: {mean_t2:.2f}",
        )

        # OOC markers in red
        if np.any(ooc_arr):
            self.ax.scatter(
                indices_arr[ooc_arr],
                t2_arr[ooc_arr],
                color=CHART_OOC,
                s=28,
                zorder=6,
                marker="x",
                linewidths=1.5,
                label=f"OOC ({int(np.sum(ooc_arr))})",
            )

        # Add OOC count annotation
        ooc_count = stats.get("ooc_count", 0)
        ooc_pct = stats.get("ooc_pct", 0.0)
        self.ax.annotate(
            f"OOC: {ooc_count} / {ooc_pct:.1f}%",
            xy=(0.01, 0.97),
            xycoords="axes fraction",
            fontsize=CHART_FONT_ANNOTATION,
            color=CHART_ANNOTATION,
            va="top",
        )

        self.ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
        self.canvas.draw()
        return True
