from __future__ import annotations

from typing import Any, Dict

import numpy as np

from app.charts.base_chart import BaseChart
from app.ui.theme.tokens import CHART_FONT_ANNOTATION, TEXT_SECONDARY


class CorrelationHeatmapChart(BaseChart):
    """Heatmap for feature correlation matrix."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="Correlation Heatmap",
            xlabel="Feature",
            ylabel="Feature",
            figsize=(6, 5),
        )
        self._cbar = None

    def clear(self) -> None:
        """Reset axes and remove any existing color bar."""
        if self._cbar is not None:
            import contextlib
            with contextlib.suppress(Exception):
                self._cbar.remove()
            self._cbar = None
        super().clear()

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Draw the correlation heatmap with cell annotations."""
        if not super().draw_chart(engine_output):
            return False
        data = engine_output.get("data", {})
        labels = list(data.get("labels", []))
        matrix = np.array(data.get("matrix", []), dtype=float)
        if len(labels) < 2 or matrix.size == 0:
            self._show_placeholder("Correlation matrix 資料不足。")
            return False

        im = self.ax.imshow(matrix, cmap="RdYlBu_r", vmin=-1.0, vmax=1.0)
        self.ax.set_xticks(range(len(labels)))
        self.ax.set_yticks(range(len(labels)))
        self.ax.set_xticklabels(labels, rotation=45, ha="right")
        self.ax.set_yticklabels(labels)
        self.ax.set_title("Correlation Heatmap")
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                self.ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=CHART_FONT_ANNOTATION)
        self._cbar = self.figure.colorbar(im, ax=self.ax, orientation="vertical", label="Correlation")
        self._cbar.ax.yaxis.label.set_color(TEXT_SECONDARY)
        self._cbar.ax.tick_params(colors=TEXT_SECONDARY)
        # layout handled by BaseChart
        self.canvas.draw()
        return True
