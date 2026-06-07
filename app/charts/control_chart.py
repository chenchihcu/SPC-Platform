from app.charts.base_chart import (
    BaseChart,
    _apply_mpl_dark_style,
    annotate_latest_point,
    draw_reference_line,
    resolve_target_col,
    scatter_state_points,
)
from app.ui.theme.tokens import (
    CHART_OOC_MARKER_SIZE,
    CHART_SERIES,
    CHART_SERIES_MARKER_SIZE,
    CHART_FONT_TITLE,
    CHART_FONT_LEGEND,
)
from typing import Dict, Any

# D4 constant for moving range UCL (subgroup size n=2)
_MR_D4 = 3.267


class ControlChart(BaseChart):
    """
    Renders an I-MR Control Chart with two sub-plots:
      top (211) — Individual values chart
      bottom (212) — Moving Range chart
    """
    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="個別值管制圖 (I Chart)",
            xlabel="樣本序 (PCB Run Order)",
            ylabel="量測值 (Measurement)",
            figsize=(6, 6),
        )
        # Replace single-axis layout with two sub-plots
        self.figure.clear()
        self.ax = self.figure.add_subplot(211)
        self.ax_mr = self.figure.add_subplot(212, sharex=self.ax)
        _apply_mpl_dark_style(self.figure, self.ax)
        _apply_mpl_dark_style(self.figure, self.ax_mr)

    def clear(self) -> None:
        """Clear chart canvas and reset to empty state."""
        super().clear()
        # Optimize vertical space: hide redundant top X-axis labels/ticks (Pass 25 audit)
        self.ax.set_xlabel("")
        self.ax.tick_params(labelbottom=False)
        
        self.ax_mr.clear()
        _apply_mpl_dark_style(self.figure, self.ax_mr)
        self.ax_mr.set_xlabel("樣本序 (PCB Run Order)")
        self.ax_mr.set_ylabel("移動極差 (MR)")

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False

        target_col = resolve_target_col(engine_output)
        if target_col:
            self.ax.set_ylabel(f"量測值 ({target_col})")

        data = engine_output.get("data", {})
        stats = engine_output.get("statistics", {})

        y_values = data.get("values", [])
        indices = data.get("indices", list(range(len(y_values))))
        out_of_control = data.get("out_of_control_indices", [])

        cl = stats.get("cl", 0)
        ucl = stats.get("ucl", 0)
        lcl = stats.get("lcl", 0)

        # Adaptive marker: suppress point markers when N is large to avoid visual clutter
        _n = len(y_values)
        _marker = "o" if _n <= 300 else None
        _msize = CHART_SERIES_MARKER_SIZE if _marker else 0

        # ── I chart (top) ────────────────────────────────────────────────────
        self.ax.set_title("個別值管制圖 (I Chart)", fontsize=CHART_FONT_TITLE)
        self.ax.plot(
            indices, y_values,
            marker=_marker, color=CHART_SERIES, linestyle="-",
            markersize=_msize, label="Data",
        )

        if out_of_control:
            idx_to_pos = {idx: i for i, idx in enumerate(indices)}
            ooc_values = [y_values[idx_to_pos[idx]] for idx in out_of_control if idx in idx_to_pos]
            ooc_indices = [idx for idx in out_of_control if idx in idx_to_pos]
            if ooc_indices and ooc_values:
                _ooc_marker_s = CHART_OOC_MARKER_SIZE ** 2 if _n <= 300 else max(3, CHART_OOC_MARKER_SIZE - 4) ** 2
                _ooc_alpha = 1.0 if _n <= 300 else 0.5
                scatter_state_points(
                    self.ax,
                    ooc_indices,
                    ooc_values,
                    state="ooc",
                    label="OOC (Defect)",
                    size=_ooc_marker_s,
                ).set_alpha(_ooc_alpha)

        annotate_latest_point(self.ax, indices, y_values, label="Latest", color=CHART_SERIES)
        draw_reference_line(self.ax, cl, f"CL: {cl:.2f}", semantic="centerline")
        draw_reference_line(self.ax, ucl, f"UCL (3σ): {ucl:.2f}", semantic="control_limit")
        draw_reference_line(self.ax, lcl, f"LCL (3σ): {lcl:.2f}", semantic="control_limit")
        self.ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)

        # ── MR chart (bottom) ────────────────────────────────────────────────
        mr_values = data.get("mr_values", [])
        mr_bar = stats.get("mr_bar", 0)
        if mr_values:
            mr_indices = data.get("mr_indices", list(range(1, len(mr_values) + 1)))
            mr_ucl = mr_bar * _MR_D4
            self.ax_mr.set_title("移動極差管制圖 (MR Chart)", fontsize=CHART_FONT_TITLE)
            _mr_marker = "o" if len(mr_values) <= 300 else None
            _mr_msize = CHART_SERIES_MARKER_SIZE if _mr_marker else 0
            self.ax_mr.plot(
                mr_indices, mr_values,
                marker=_mr_marker, color=CHART_SERIES, linestyle="-",
                markersize=_mr_msize, label="MR",
            )
            annotate_latest_point(self.ax_mr, mr_indices, mr_values, label="Latest MR", color=CHART_SERIES)
            draw_reference_line(self.ax_mr, mr_bar, f"CL (MR平均): {mr_bar:.3f}", semantic="centerline")
            draw_reference_line(self.ax_mr, mr_ucl, f"UCL (D4): {mr_ucl:.3f}", semantic="control_limit")
            self.ax_mr.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)

        # layout handled by BaseChart
        self.canvas.draw()
        return True

