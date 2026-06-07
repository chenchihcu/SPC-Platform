from app.charts.base_chart import BaseChart, build_sparse_tick_labels
from typing import Dict, Any
import numpy as np
from app.ui.theme.tokens import (
    CHART_BAR_PASS,
    CHART_FILL_EDGE,
    CHART_FONT_LABEL,
)


class PassFailChart(BaseChart):
    """Pass/fail summary per feature (bar chart)."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Pass / Fail Summary（合格率）",
            xlabel="特徵",
            ylabel="合格率 (%)",
            figsize=(6, 4),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        data = engine_output.get("data", {})
        labels = data.get("labels", [])
        pass_rates = data.get("pass_rates", [])
        if not labels or not pass_rates:
            self._show_placeholder("無資料")
            return False
        x = np.arange(len(labels))
        bars = self.ax.bar(x, pass_rates, color=CHART_BAR_PASS, edgecolor=CHART_FILL_EDGE, linewidth=0.5)
        self.ax.set_xticks(x)
        display_labels = build_sparse_tick_labels(labels, threshold=30, step_small=5, step_large=10)
        self.ax.set_xticklabels(display_labels, rotation=25, ha="right")
        self.ax.set_ylabel("合格率 (%)")
        self.ax.set_ylim(0, 105)
        for bar, rate in zip(bars, pass_rates):
            self.ax.annotate(f"{rate:.0f}%", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                             ha="center", va="bottom", fontsize=CHART_FONT_LABEL)
        # layout handled by BaseChart
        self.canvas.draw()
        return True

