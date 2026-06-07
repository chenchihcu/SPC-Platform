from __future__ import annotations

from typing import Any, Dict

from app.charts.base_chart import BaseChart
from app.ui.theme.tokens import CHART_BAR_NEUTRAL, CHART_OOC, CHART_FONT_ANNOTATION, TEXT_SECONDARY


class AnovaPartTypeChart(BaseChart):
    """One-way ANOVA summary chart (means by group + significance annotation)."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="ANOVA (PartType)",
            xlabel="Group",
            ylabel="Mean",
            figsize=(6, 4),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Draw ANOVA mean-by-group bars and significance annotation."""
        if not super().draw_chart(engine_output):
            return False

        data = engine_output.get("data") or {}
        stats = engine_output.get("statistics") or {}
        labels = list(data.get("group_labels", []))
        means = list(data.get("mean_by_group", []))
        if not labels or not means:
            self._show_placeholder("ANOVA 分組資料不足。")
            return False
        colors = [CHART_BAR_NEUTRAL for _ in labels]
        self.ax.bar(labels, means, color=colors, alpha=0.85)
        self.ax.set_title("ANOVA by PartType")
        self.ax.tick_params(axis="x", rotation=45)

        p_value = stats.get("p_value")
        f_stat = stats.get("f_stat")
        if p_value is not None and f_stat is not None:
            sig = "significant" if float(p_value) < 0.05 else "not significant"
            color = CHART_OOC if float(p_value) < 0.05 else TEXT_SECONDARY
            self.ax.annotate(
                f"F={float(f_stat):.3f}, p={float(p_value):.4f} ({sig})",
                xy=(0.01, 0.98),
                xycoords="axes fraction",
                va="top",
                fontsize=CHART_FONT_ANNOTATION,
                color=color,
            )
        # layout handled by BaseChart
        self.canvas.draw()
        return True
