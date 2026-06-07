from app.charts.base_chart import BaseChart, draw_reference_line, scatter_state_points
from typing import Dict, Any
from app.ui.theme.tokens import (
    CHART_BAR_NEUTRAL,
    CHART_CENTERLINE,
    CHART_FONT_LEGEND,
    CHART_LINE_STYLE_SECONDARY,
    CHART_SPEC_LIMITS,
)


def _as_float(value: Any) -> float | None:
    """Return a numeric value for plotting/comparison, or None when unavailable."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ScatterSpecChart(BaseChart):
    """Scatter plot with optional USL/LSL spec zones for two features."""

    def __init__(self, parent=None):
        super().__init__(parent, title="Scatter + Spec Zones", xlabel="X", ylabel="Y", figsize=(6, 4))

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
        if len(x_vals) == 0 or len(y_vals) == 0:
            self._show_placeholder("無散點資料")
            return False
        usl_x = _as_float(data.get("usl_x"))
        lsl_x = _as_float(data.get("lsl_x"))
        usl_y = _as_float(data.get("usl_y"))
        lsl_y = _as_float(data.get("lsl_y"))
        spec_bounds: tuple[float, float, float, float] | None = None
        if usl_x is not None and lsl_x is not None and usl_y is not None and lsl_y is not None:
            spec_bounds = (lsl_x, usl_x, lsl_y, usl_y)
        if spec_bounds is not None:
            lsl_x_spec, usl_x_spec, lsl_y_spec, usl_y_spec = spec_bounds
            from matplotlib.patches import Rectangle
            self.ax.add_patch(
                Rectangle(
                    (lsl_x_spec, lsl_y_spec),
                    usl_x_spec - lsl_x_spec,
                    usl_y_spec - lsl_y_spec,
                    fill=True,
                    facecolor=CHART_CENTERLINE,
                    alpha=0.12,
                    edgecolor=CHART_SPEC_LIMITS,
                    linestyle=CHART_LINE_STYLE_SECONDARY,
                )
            )
            draw_reference_line(
                self.ax,
                lsl_x_spec,
                f"LSL {col_x}: {lsl_x_spec:.3g}",
                orientation="v",
                semantic="spec_limit",
            )
            draw_reference_line(
                self.ax,
                usl_x_spec,
                f"USL {col_x}: {usl_x_spec:.3g}",
                orientation="v",
                semantic="spec_limit",
            )
            draw_reference_line(
                self.ax,
                lsl_y_spec,
                f"LSL {col_y}: {lsl_y_spec:.3g}",
                semantic="spec_limit",
            )
            draw_reference_line(
                self.ax,
                usl_y_spec,
                f"USL {col_y}: {usl_y_spec:.3g}",
                semantic="spec_limit",
            )
        # Adaptive alpha for high-density plots (Item 61)
        n_pts = len(x_vals)
        alpha = max(0.1, min(0.65, 500.0 / n_pts)) if n_pts > 500 else 0.65
        if spec_bounds is not None:
            lsl_x_spec, usl_x_spec, lsl_y_spec, usl_y_spec = spec_bounds
            in_x, in_y, oos_x, oos_y = [], [], [], []
            for x_val, y_val in zip(x_vals, y_vals):
                x_num = _as_float(x_val)
                y_num = _as_float(y_val)
                is_oos = (
                    x_num is not None
                    and y_num is not None
                    and (
                        x_num < lsl_x_spec
                        or x_num > usl_x_spec
                        or y_num < lsl_y_spec
                        or y_num > usl_y_spec
                    )
                )
                if is_oos:
                    oos_x.append(x_val)
                    oos_y.append(y_val)
                else:
                    in_x.append(x_val)
                    in_y.append(y_val)
            if in_x:
                self.ax.scatter(
                    in_x,
                    in_y,
                    alpha=alpha,
                    s=20,
                    color=CHART_BAR_NEUTRAL,
                    edgecolors="none",
                    label="In spec",
                )
            if oos_x:
                scatter_state_points(self.ax, oos_x, oos_y, state="oos", label="OOS")
            self.ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
        else:
            self.ax.scatter(x_vals, y_vals, alpha=alpha, s=20, color=CHART_BAR_NEUTRAL, edgecolors="none")
        # layout handled by BaseChart
        self.canvas.draw()
        return True
