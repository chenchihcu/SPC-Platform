"""
Radar (spider) chart — compares multiple positions (Image locations)
across multiple measurement features (Volume, Area, Height).
"""

import numpy as np
from typing import Any, Dict

from app.charts.base_chart import BaseChart
from app.ui.theme.tokens import (
    CHART_PALETTE_VOLUME_FILL,
    CHART_PALETTE_AREA_FILL,
    CHART_PALETTE_HEIGHT_FILL,
    CHART_PALETTE_OFFSET_X_FILL,
    CHART_PALETTE_OFFSET_Y_FILL,
    CHART_PALETTE_OFFSET_R_FILL,
    CHART_AXES_BG,
    CHART_FONT_ANNOTATION,
    CHART_FONT_LEGEND,
    CHART_GRID,
)

_RADAR_PALETTE = [
    CHART_PALETTE_VOLUME_FILL,
    CHART_PALETTE_AREA_FILL,
    CHART_PALETTE_HEIGHT_FILL,
    CHART_PALETTE_OFFSET_X_FILL,
    CHART_PALETTE_OFFSET_Y_FILL,
    CHART_PALETTE_OFFSET_R_FILL,
]
_MAX_RENDERED_SERIES = 8


class RadarChart(BaseChart):
    """Radar (spider) chart comparing multiple positions across features."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Radar 綜合比較圖",
            xlabel="",
            ylabel="",
            figsize=(5, 5),
        )
        # Lazily create polar projection on first draw (avoids QApp dependency
        # at construction time).
        self._polar_ready = False

    def _ensure_polar(self) -> None:
        """Replace the cartesian axes with a polar projection once."""
        if self._polar_ready:
            return
        self.figure.delaxes(self.ax)
        self.ax = self.figure.add_subplot(111, projection='polar')
        self.ax.set_facecolor(CHART_AXES_BG)
        self._polar_ready = True

    def clear(self) -> None:
        """Clear axes but keep polar projection and radar styling."""
        self._ensure_polar()
        self.ax.clear()
        self.ax.set_facecolor(CHART_AXES_BG)
        self.ax.set_title(self.title_str)

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render radar chart from engine output payload."""
        self._ensure_polar()
        if not super().draw_chart(engine_output):
            return False

        data = engine_output.get("data", {})
        categories = data.get("categories", [])
        all_series = data.get("series", [])
        series_list = all_series[:_MAX_RENDERED_SERIES]

        if not categories or not series_list:
            self._show_placeholder("Radar 圖資料不足")
            return False

        num_vars = len(categories)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]  # close the polygon

        for i, series in enumerate(series_list):
            values = series.get("values", [])
            if not values:
                continue
            values_closed = values + values[:1]
            color = _RADAR_PALETTE[i % len(_RADAR_PALETTE)]
            name = series.get("name", f"Series {i + 1}")
            self.ax.plot(
                angles, values_closed, "o-",
                linewidth=2, color=color, label=name,
            )
            self.ax.fill(angles, values_closed, alpha=0.10, color=color)

        self.ax.set_xticks(angles[:-1])
        self.ax.set_xticklabels(categories, fontsize=CHART_FONT_ANNOTATION)
        if len(all_series) > len(series_list):
            self.ax.text(
                0.5, -0.12,
                f"顯示前 {len(series_list)} / {len(all_series)} 群組",
                transform=self.ax.transAxes,
                ha="center",
                va="top",
                fontsize=CHART_FONT_ANNOTATION,
            )

        # Polar grid: lighter styling
        self.ax.grid(True, color=CHART_GRID, linestyle="-", linewidth=0.5, alpha=0.6)

        # Only add legend if any labeled artists were plotted
        if self.ax.get_legend_handles_labels()[0]:
            self.ax.legend(
                loc="upper right",
                bbox_to_anchor=(1.3, 1.1),
                fontsize=CHART_FONT_LEGEND,
            )
        self.canvas.draw()
        return True
