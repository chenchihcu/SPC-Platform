from app.charts.base_chart import BaseChart, resolve_target_col, build_sparse_tick_labels
from typing import Dict, Any
import numpy as np
from app.ui.theme.tokens import (
    CHART_BAR_NEUTRAL,
    CHART_FILL_EDGE,
    CHART_WARNING_MARK,
    CHART_FONT_ANNOTATION,
)


class SubgroupChart(BaseChart):
    """Bar chart of subgroup means with optional violation rate annotation."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Subgroup 比較 (依類型/RefDes)",
            xlabel="子組",
            ylabel="平均值",
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        target_col = resolve_target_col(engine_output)
        if target_col:
            self.ax.set_ylabel(f"平均 ({target_col})")
        data = engine_output.get("data", {})
        labels = data.get("labels", [])
        means = data.get("means", [])
        violation_rates = data.get("violation_rates", [])
        if not labels or not means:
            self._show_placeholder("無子群資料 (No Subgroup Data)")
            return False
        x = np.arange(len(labels))
        bars = self.ax.bar(x, means, color=CHART_BAR_NEUTRAL, edgecolor=CHART_FILL_EDGE, linewidth=0.5)
        self.ax.set_xticks(x)
        display_labels = build_sparse_tick_labels(labels, threshold=30, step_small=5, step_large=10)
        self.ax.set_xticklabels(display_labels, rotation=45, ha="right")
        if violation_rates and any(v > 0 for v in violation_rates):
            for i, (bar, vr) in enumerate(zip(bars, violation_rates)):
                if vr > 0:
                    self.ax.annotate(f"{vr:.0f}%", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                                     ha="center", va="bottom", fontsize=CHART_FONT_ANNOTATION, color=CHART_WARNING_MARK)
        # layout handled by BaseChart
        self.canvas.draw()
        return True
