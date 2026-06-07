import contextlib

from app.charts.base_chart import BaseChart
from typing import Dict, Any
from app.ui.theme.tokens import CHART_SERIES, TEXT_SECONDARY


class DensityChart(BaseChart):
    """2D density (hexbin) plot for two measurement columns."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Density / Hexbin",
            xlabel="X",
            ylabel="Y",
            figsize=(6, 4),
        )
        self.cbar = None

    def clear(self) -> None:
        """Clear chart canvas and reset to empty state."""
        if self.cbar is not None:
            with contextlib.suppress(AttributeError, RuntimeError, ValueError):
                # Colorbar may already be removed when canvas has been recreated.
                self.cbar.remove()
            self.cbar = None
        super().clear()

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        data = engine_output.get("data", {})
        stats = engine_output.get("statistics", {})
        mode = str(data.get("mode", "")).strip().lower()
        if mode == "univariate":
            x_grid = data.get("x_grid", [])
            y_density = data.get("density", [])
            col = data.get("col", "Value")
            if not x_grid or not y_density:
                self._show_placeholder("無資料")
                return False
            self.ax.set_xlabel(col)
            self.ax.set_ylabel("Density")
            self.ax.plot(x_grid, y_density, color=CHART_SERIES, linewidth=1.8)
            self.ax.fill_between(x_grid, y_density, color=CHART_SERIES, alpha=0.18)
            # layout handled by BaseChart
            self.canvas.draw()
            return True

        x_vals = data.get("x", [])
        y_vals = data.get("y", [])
        col_x = data.get("col_x", "X")
        col_y = data.get("col_y", "Y")
        gridsize = stats.get("gridsize", 30)
        if not x_vals or not y_vals:
            self._show_placeholder("無資料")
            return False
        self.ax.set_xlabel(col_x)
        self.ax.set_ylabel(col_y)
        hb = self.ax.hexbin(x_vals, y_vals, gridsize=gridsize, cmap="YlGnBu", mincnt=1, edgecolors="none", linewidths=0.0)
        # Unit tests expect exact '計數' label text.
        self.cbar = self.figure.colorbar(hb, ax=self.ax, label="計數")
        self.cbar.ax.yaxis.label.set_color(TEXT_SECONDARY)
        self.cbar.ax.tick_params(colors=TEXT_SECONDARY)
        # layout handled by BaseChart
        self.canvas.draw()
        return True

