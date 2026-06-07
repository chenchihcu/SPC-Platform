from __future__ import annotations

from typing import Any, Dict

from app.charts.base_chart import (
    BaseChart,
    _apply_mpl_dark_style,
    annotate_latest_point,
    draw_reference_line,
    scatter_state_points,
)
from app.ui.theme.tokens import (
    CHART_SERIES,
    CHART_SERIES_SECONDARY,
    CHART_FONT_LEGEND,
)


class XbarRChart(BaseChart):
    """Render Xbar-R chart using subgroup means/ranges."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Xbar-R 管制圖",
            xlabel="子群",
            ylabel="Xbar",
            figsize=(6, 6),
        )
        self.figure.clear()
        self.ax = self.figure.add_subplot(211)
        self.ax_r = self.figure.add_subplot(212, sharex=self.ax)
        _apply_mpl_dark_style(self.figure, self.ax)
        _apply_mpl_dark_style(self.figure, self.ax_r)

    def clear(self) -> None:
        """Clear both Xbar and R panels and restore baseline axis styling."""
        super().clear()
        # Hide top chart X-axis labels to save space
        self.ax.set_xlabel("")
        self.ax.tick_params(labelbottom=False)
        
        self.ax_r.clear()
        _apply_mpl_dark_style(self.figure, self.ax_r)
        self.ax_r.set_xlabel("子群")
        self.ax_r.set_ylabel("R")

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Draw Xbar and R charts with CL/UCL/LCL and OOC markers."""
        if not super().draw_chart(engine_output):
            return False

        data = engine_output.get("data", {})
        stats = engine_output.get("statistics", {})
        labels = list(data.get("labels", []))
        xbar_values = list(data.get("xbar_values", []))
        r_values = list(data.get("r_values", []))
        if not labels or not xbar_values or not r_values:
            self._show_placeholder("無有效 Xbar-R 子群資料。")
            return False

        x = list(range(len(labels)))
        ooc_xbar = set(data.get("ooc_xbar_indices", []))
        ooc_r = set(data.get("ooc_r_indices", []))

        xbarbar = float(stats.get("xbarbar", 0.0))
        ucl_xbar = float(stats.get("ucl_xbar", 0.0))
        lcl_xbar = float(stats.get("lcl_xbar", 0.0))
        rbar = float(stats.get("rbar", 0.0))
        ucl_r = float(stats.get("ucl_r", 0.0))
        lcl_r = float(stats.get("lcl_r", 0.0))

        self.ax.set_title("Xbar Chart")
        self.ax.plot(x, xbar_values, color=CHART_SERIES, marker="o", linewidth=1.4, label="Xbar")
        if ooc_xbar:
            scatter_state_points(
                self.ax,
                [i for i in x if i in ooc_xbar],
                [xbar_values[i] for i in x if i in ooc_xbar],
                state="ooc",
                label="OOC",
            )
        annotate_latest_point(self.ax, x, xbar_values, label="Latest", color=CHART_SERIES)
        draw_reference_line(self.ax, xbarbar, f"CL: {xbarbar:.3f}", semantic="centerline")
        draw_reference_line(self.ax, ucl_xbar, f"UCL: {ucl_xbar:.3f}", semantic="control_limit")
        draw_reference_line(self.ax, lcl_xbar, f"LCL: {lcl_xbar:.3f}", semantic="control_limit")
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(labels, rotation=45, ha="right")
        self.ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)

        self.ax_r.set_title("R Chart")
        self.ax_r.plot(x, r_values, color=CHART_SERIES_SECONDARY, marker="o", linewidth=1.4, label="R")
        if ooc_r:
            scatter_state_points(
                self.ax_r,
                [i for i in x if i in ooc_r],
                [r_values[i] for i in x if i in ooc_r],
                state="ooc",
                label="OOC",
            )
        annotate_latest_point(self.ax_r, x, r_values, label="Latest", color=CHART_SERIES_SECONDARY)
        draw_reference_line(self.ax_r, rbar, f"CL: {rbar:.3f}", semantic="centerline")
        draw_reference_line(self.ax_r, ucl_r, f"UCL: {ucl_r:.3f}", semantic="control_limit")
        draw_reference_line(self.ax_r, lcl_r, f"LCL: {lcl_r:.3f}", semantic="control_limit")
        self.ax_r.set_xticks(x)
        self.ax_r.set_xticklabels(labels, rotation=45, ha="right")
        self.ax_r.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)

        # layout handled by BaseChart
        self.canvas.draw()
        return True
