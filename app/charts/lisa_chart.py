"""
lisa_chart.py — LISA 空間自相關圖表

繪製 PCB 空間點散佈圖，依 LISA 分類著色（HH=紅, LL=藍, HL=橙, LH=青, NS=灰）。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.charts.base_chart import BaseChart
from app.ui.theme.tokens import (
    CHART_FONT_ANNOTATION,
    CHART_FONT_LEGEND,
    CHART_GRID,
    CHART_LISA_HH,
    CHART_LISA_HL,
    CHART_LISA_LH,
    CHART_LISA_LL,
    CHART_LISA_NS,
    TEXT_SECONDARY,
)

LISA_COLORS: Dict[str, str] = {
    "HH": CHART_LISA_HH,  # red — high-high cluster
    "LL": CHART_LISA_LL,  # blue — low-low cluster
    "HL": CHART_LISA_HL,  # orange — high-low outlier
    "LH": CHART_LISA_LH,  # cyan — low-high outlier
    "NS": CHART_LISA_NS,  # gray — not significant
}

_LISA_LABELS: Dict[str, str] = {
    "HH": "HH (高-高)",
    "LL": "LL (低-低)",
    "HL": "HL (高-低)",
    "LH": "LH (低-高)",
    "NS": "NS (不顯著)",
}


class LisaChart(BaseChart):
    """LISA 空間自相關圖表 — 顯示 PCB 點位與其 LISA 分類簇。"""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="LISA 空間自相關 (LISA Cluster Map)",
            xlabel="X 軸座標 (mm)",
            ylabel="Y 軸座標 (mm)",
            figsize=(6, 5),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the LISA cluster map from an engine payload."""
        if not super().draw_chart(engine_output):
            return False

        data = engine_output.get("data", {}) or {}
        meta = engine_output.get("metadata", {}) or {}

        # Try payload format with "points" list first, then fall back to
        # separate x/y/classifications arrays from the engine.
        points: List[Dict[str, Any]] = data.get("points", [])
        if not points:
            # Fall back to flat arrays
            xs: List[float] = data.get("x", [])
            ys: List[float] = data.get("y", [])
            categories: List[str] = data.get("classifications", [])
            if xs and ys and categories:
                points = [
                    {"x": float(x), "y": float(y), "category": str(c)}
                    for x, y, c in zip(xs, ys, categories)
                ]

        if not points:
            self._show_placeholder("無 LISA 空間點位資料。")
            return False

        # Extract per-category point lists
        category_points: Dict[str, List[Dict[str, Any]]] = {k: [] for k in LISA_COLORS}
        for pt in points:
            cat = str(pt.get("category", "NS"))
            if cat in category_points:
                category_points[cat].append(pt)
            else:
                category_points["NS"].append(pt)

        # Plot each category as a separate scatter series
        for cat in ("HH", "LL", "HL", "LH", "NS"):
            pts = category_points.get(cat, [])
            if not pts:
                continue
            xs_cat = [float(p["x"]) for p in pts]
            ys_cat = [float(p["y"]) for p in pts]
            self.ax.scatter(
                xs_cat,
                ys_cat,
                c=LISA_COLORS[cat],
                label=_LISA_LABELS.get(cat, cat),
                s=60,
                alpha=0.8,
                edgecolors="none",
                zorder=3,
            )

        # --- Legend with metadata ---
        global_i = data.get("global_i")
        p_value = data.get("p_value")
        k_neighbors = meta.get("k_neighbors", data.get("k"))

        legend_lines: List[str] = []
        if global_i is not None:
            legend_lines.append(f"Global Moran's I: {float(global_i):.4f}")
        if p_value is not None:
            legend_lines.append(f"p-value: {float(p_value):.4f}")
        if k_neighbors is not None:
            legend_lines.append(f"K-neighbors: {int(k_neighbors)}")

        # Category counts from metadata or statistics
        counts: Dict[str, int] = {}
        for cat in ("HH", "LL", "HL", "LH", "NS"):
            n = meta.get(f"n_{cat.lower()}")
            if n is None:
                n = len(category_points.get(cat, []))
            if n:
                counts[cat] = int(n)
        if counts:
            count_str = ", ".join(f"{k}={v}" for k, v in counts.items())
            legend_lines.append(f"Counts: {count_str}")

        if legend_lines:
            legend_text = "  |  ".join(legend_lines)
            self.ax.text(
                0.5,
                1.02,
                legend_text,
                transform=self.ax.transAxes,
                ha="center",
                va="bottom",
                fontsize=CHART_FONT_LEGEND,
                color=TEXT_SECONDARY,
            )

        # Grid on top of scatter but behind annotations
        self.ax.grid(True, color=CHART_GRID, linestyle="-", linewidth=0.5, alpha=0.5, zorder=0)

        self.ax.legend(
            loc="lower right",
            fontsize=CHART_FONT_LEGEND,
            title_fontsize=CHART_FONT_ANNOTATION,
        )

        self.canvas.draw()
        return True
