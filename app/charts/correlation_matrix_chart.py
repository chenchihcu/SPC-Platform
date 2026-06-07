from __future__ import annotations

from typing import Any, Dict

from app.charts.base_chart import BaseChart
from app.ui.theme.tokens import CHART_BAR_NEUTRAL, CHART_OOC, TEXT_SECONDARY


class CorrelationMatrixChart(BaseChart):
    """Ranked pairwise correlation bar chart."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Correlation Matrix (Pair Ranking)",
            xlabel="|r|",
            ylabel="Pair",
            figsize=(6, 4),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render top-ranked pairwise correlations as a horizontal bar chart."""
        if not super().draw_chart(engine_output):
            return False
        pairs = list((engine_output.get("data") or {}).get("pairs_ranked", []))
        if not pairs:
            self._show_placeholder("關聯配對資料不足。")
            return False
        top = pairs[:8]
        labels = [str(item.get("pair", "UNKNOWN")) for item in top]
        values = [float(item.get("corr", 0.0)) for item in top]
        colors = [CHART_OOC if abs(v) >= 0.7 else CHART_BAR_NEUTRAL for v in values]
        y = list(range(len(labels)))
        self.ax.barh(y, values, color=colors, alpha=0.9)
        self.ax.set_yticks(y)
        self.ax.set_yticklabels(labels)
        self.ax.invert_yaxis()
        self.ax.set_xlim(-1.0, 1.0)
        self.ax.axvline(0.0, color=TEXT_SECONDARY, linewidth=1.0)
        self.ax.set_title("Correlation Pair Ranking")
        # layout handled by BaseChart
        self.canvas.draw()
        return True
