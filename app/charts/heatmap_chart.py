from app.charts.base_chart import BaseChart
from typing import Dict, Any
from app.ui.theme.tokens import BORDER, CHART_LINE_STYLE_SECONDARY, TEXT_SECONDARY
class HeatmapChart(BaseChart):
    """
    Renders a spatial 2D scattermap mapping components to X/Y with color-coded SPI Values.
    """
    def __init__(self, parent=None):
        super().__init__(parent, title="PCB 空間分析 (Spatial Heatmap)", xlabel="X軸座標 (X mm)", ylabel="Y軸座標 (Y mm)")
        self.cbar = None

    def clear(self) -> None:
        """Clear chart canvas and reset to empty state."""
        if self.cbar is not None:
            import contextlib
            with contextlib.suppress(Exception):
                self.cbar.remove()
            self.cbar = None
        super().clear()

    _MODE_LABELS = {
        "value": "量測值 (Value)",
        "ucl_density": "UCL 違反密度 (UCL violation)",
        "lcl_density": "LCL 違反密度 (LCL violation)",
        "oos_density": "OOS 密度 (Out of spec)",
        "volume_deviation": "偏離平均 (Deviation from mean)",
    }

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False

        data = engine_output.get("data", {})
        x = data.get("x", [])
        y = data.get("y", [])
        vals = data.get("values", [])

        if not x or not y or not vals:
            self._show_placeholder("無法取得有效的 PCB 座標數據 (Failed to yield spatial scatter points)")
            return False

        mode = (engine_output.get("metadata") or {}).get("mode", "value")
        mode_title = self._MODE_LABELS.get(mode, mode)
        self.ax.set_title(f"PCB 空間分析 — {mode_title}")
        self.ax.set_xlabel(self.xlabel_str)
        self.ax.set_ylabel(self.ylabel_str)

        # scatter() zorder must be a scalar; per-point ordering is not supported.
        scatter = self.ax.scatter(x, y, c=vals, cmap="RdYlBu_r", s=120, edgecolors=BORDER, alpha=0.9, zorder=3)
        self.ax.grid(True, linestyle=CHART_LINE_STYLE_SECONDARY, alpha=0.6, zorder=0)

        cbar_label = self._MODE_LABELS.get(mode)
        if not cbar_label:
            ctx = engine_output.get("analysis_context", {})
            if ctx.get("target_col"):
                cbar_label = f"量測值 ({ctx['target_col']})"
            else:
                cbar_label = "量測值 (Value)"
        self.cbar = self.figure.colorbar(scatter, ax=self.ax, orientation="vertical", label=cbar_label)
        self.cbar.ax.yaxis.label.set_color(TEXT_SECONDARY)
        self.cbar.ax.tick_params(colors=TEXT_SECONDARY)
        stats = engine_output.get("statistics", {})
        if stats.get("sampled_for_display"):
            shown = stats.get("displayed_n", len(x))
            total = stats.get("n", len(x))
            bins = stats.get("aggregation_bins")
            bins_note = f", grid={bins}x{bins}" if bins else ""
            self.ax.annotate(
                f"顯示聚合: {shown}/{total}{bins_note}",
                xy=(0.01, 0.97),
                xycoords="axes fraction",
                fontsize=9,
                color=TEXT_SECONDARY,
                va="top",
            )

        # layout handled by BaseChart
        self.canvas.draw()
        return True

