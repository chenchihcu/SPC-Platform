
from app.charts.base_chart import BaseChart, _apply_mpl_app_style, get_feature_color
from typing import Dict, Any
from app.ui.theme.tokens import CHART_FONT_LABEL, CHART_SERIES, TEXT_SECONDARY


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
        self._safe_remove_artist("cbar")
        if len(self.figure.axes) > 1:
            # Leaving 3F subplot mode: drop the extra axes before single-axis drawing.
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
        super().clear()

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        if engine_output.get("_multi_feature") and engine_output.get("_feature_data"):
            return self._draw_multi_feature(engine_output)
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

    def _draw_multi_feature(self, engine_output: Dict[str, Any]) -> bool:
        """Render one univariate KDE subplot per feature (3F density semantics)."""
        features = list(engine_output.get("_features") or [])
        feature_data = engine_output.get("_feature_data") or {}
        self._safe_remove_artist("cbar")
        self.figure.clear()
        n = len(features)
        if n == 0:
            self.ax = self.figure.add_subplot(111)
            _apply_mpl_app_style(self.figure, self.ax)
            self._show_placeholder("無多特徵資料")
            self.canvas.draw()
            return False
        drawn = False
        for i, feat in enumerate(features):
            ax = self.figure.add_subplot(1, n, i + 1)
            _apply_mpl_app_style(self.figure, ax)
            data = (feature_data.get(feat) or {}).get("data", {})
            x_grid = data.get("x_grid", [])
            y_density = data.get("density", [])
            ax.set_title(str(feat), fontsize=CHART_FONT_LABEL)
            ax.set_xlabel(str(data.get("col") or feat))
            ax.set_ylabel("Density" if i == 0 else "")
            if str(data.get("mode", "")).strip().lower() != "univariate" or not x_grid or not y_density:
                ax.text(0.5, 0.5, f"{feat}\n無資料", ha="center", va="center", transform=ax.transAxes)
                continue
            color, _edge = get_feature_color(str(feat), i)
            ax.plot(x_grid, y_density, color=color, linewidth=1.8)
            ax.fill_between(x_grid, y_density, color=color, alpha=0.18)
            drawn = True
        # figure.clear() invalidated the old axes; keep self.ax valid for BaseChart.clear().
        self.ax = self.figure.axes[0]
        self._show_canvas()
        self.canvas.draw()
        return drawn
