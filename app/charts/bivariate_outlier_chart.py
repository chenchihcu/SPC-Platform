from app.charts.base_chart import BaseChart
from typing import Dict, Any
from app.ui.theme.tokens import (
    CHART_BAR_NEUTRAL,
    CHART_OOC,
    CHART_AXES_BG,
    CHART_ANNOTATION,
    CHART_FONT_ANNOTATION,
    CHART_FONT_LEGEND,
)


class BivariateOutlierChart(BaseChart):
    """Scatter with Mahalanobis-distance outliers highlighted."""

    def __init__(self, parent=None):
        super().__init__(parent, title="雙變量離群 (Bivariate Outlier)", xlabel="X", ylabel="Y", figsize=(6, 4))

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        data = engine_output.get("data", {})
        meta = engine_output.get("metadata", {})
        col_x = meta.get("col_x", "X")
        col_y = meta.get("col_y", "Y")
        self.ax.set_xlabel(col_x)
        self.ax.set_ylabel(col_y)
        x_vals = data.get("x", [])
        y_vals = data.get("y", [])
        is_outlier = data.get("is_outlier", [])
        stats = engine_output.get("statistics", {})
        method = (meta.get("method") or "").strip()
        if not x_vals or not y_vals:
            self._show_placeholder("無資料")
            return False
        in_x, in_y, out_x, out_y = [], [], [], []
        for i, (x, y) in enumerate(zip(x_vals, y_vals)):
            if i < len(is_outlier) and is_outlier[i]:
                out_x.append(x)
                out_y.append(y)
            else:
                in_x.append(x)
                in_y.append(y)
        if in_x:
            self.ax.scatter(in_x, in_y, alpha=0.65, s=20, color=CHART_BAR_NEUTRAL, label="正常", edgecolors="none")
        if out_x:
            self.ax.scatter(out_x, out_y, alpha=0.85, s=30, color=CHART_OOC, label="離群", edgecolors=CHART_AXES_BG)
        threshold = stats.get("threshold_d2")
        if threshold is not None:
            self.ax.set_title(f"雙變量離群（d²>{float(threshold):.2f}）")
        if method:
            self.ax.annotate(
                f"method={method}",
                xy=(0.01, 0.98), xycoords="axes fraction",
                fontsize=CHART_FONT_ANNOTATION, color=CHART_ANNOTATION, va="top",
            )
        self.ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
        # layout handled by BaseChart
        self.canvas.draw()
        return True

