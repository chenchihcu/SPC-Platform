import contextlib
import logging

from app.charts.base_chart import BaseChart, build_sparse_tick_labels
from PySide6.QtCore import Signal
from typing import Dict, Any, List
from app.ui.theme.tokens import (
    CHART_FILL,
    CHART_FILL_EDGE,
    CHART_BAR_FAIL,
    CHART_SERIES,
    CHART_FONT_LABEL,
)

logger = logging.getLogger(__name__)

class ParetoChart(BaseChart):
    """
    Renders a Pareto Chart for SPI defect categorizations or component ranking.
    When data has mode "component", clicking a bar emits component_selected(component_id).
    """
    component_selected = Signal(str)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent, title="柏拉圖分析 (Pareto Chart)", xlabel="不良分類 (Defect Type)", ylabel="數量 (Count)")
        self._component_ids: List[str] = []
        self._ax2: Any = None

    def clear(self) -> None:
        """Clear chart canvas and reset to empty state."""
        if self._ax2 is not None:
            with contextlib.suppress(AttributeError, RuntimeError, ValueError):
                # Twin axis might already be detached during repeated clear/draw cycles.
                self._ax2.remove()
            self._ax2 = None
        super().clear()

    _SPARSE_LABEL_THRESHOLD = 30
    _SPARSE_STEP_SMALL = 5
    _SPARSE_STEP_LARGE = 10

    @staticmethod
    def _build_sparse_labels(
        labels: list[str],
        threshold: int = 30,
        step_small: int = 5,
        step_large: int = 10,
    ) -> list[str]:
        # Backward-compatible wrapper for unit tests and legacy chart code.
        return build_sparse_tick_labels(
            labels, threshold=threshold, step_small=step_small, step_large=step_large
        )


    def _on_pick(self, event: Any) -> None:
        if not event.artist or not self._component_ids:
            return
        try:
            ind = event.ind[0]
            if 0 <= ind < len(self._component_ids):
                self.component_selected.emit(self._component_ids[ind])
        except (IndexError, KeyError, TypeError):
            logger.debug("Ignore invalid pareto pick event", exc_info=True)

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False

        data = engine_output.get("data", {})
        categories = data.get("categories", [])
        counts = data.get("counts", [])
        cum_pct = data.get("cumulative_pct", [])
        mode = data.get("mode") or engine_output.get("metadata", {}).get("mode")
        self._component_ids = data.get("component_ids", []) if mode == "component" else []

        if not categories or not counts:
            self._show_placeholder("無任何不良種類資料能分析 (No Defect Data)")
            return False
        # 方案 10: 無不良時顯示 placeholder
        if categories == ["None"] and counts == [0]:
            self._show_placeholder("無不良，製程良好 (No Defects)")
            return False

        n = len(categories)
        total_n = n

        # 方案 4: n 低於門檻時還原 figsize
        if n <= 12:
            self.figure.set_size_inches(6, 4)
        else:
            w = min(6 + 0.4 * n, 24)
            self.figure.set_size_inches(w, 4)
        
        if total_n > self._SPARSE_LABEL_THRESHOLD:
            self.ax.set_title(self.title_str + f" （共 {total_n} 類）")
             
        # Bar Chart for frequencies
        indices = range(len(categories))
        bars = self.ax.bar(indices, counts, color=CHART_FILL, edgecolor=CHART_FILL_EDGE, zorder=2, picker=True)
        if self._component_ids and len(self._component_ids) == len(bars):
            if not hasattr(self, "_pick_cid"):
                self._pick_cid = None
            if self._pick_cid is not None:
                self.canvas.mpl_disconnect(self._pick_cid)
            self._pick_cid = self.canvas.mpl_connect("pick_event", self._on_pick)
        
        # 方案 1: 稀疏 X 軸標籤
        display_labels = build_sparse_tick_labels(
            categories,
            self._SPARSE_LABEL_THRESHOLD,
            self._SPARSE_STEP_SMALL,
            self._SPARSE_STEP_LARGE,
        )
        rot, fs = (60, 7) if n > 12 else (15, 9)
        self.ax.set_xticks(indices)
        self.ax.set_xticklabels(display_labels, rotation=rot, ha="right", fontsize=fs)
        if mode == "component":
            self.ax.set_xlabel("元件類別 (Part Type / RefDes)")
            self.ax.set_ylabel("異常次數 (Abnormal Count)", color=CHART_BAR_FAIL)
        else:
            self.ax.set_ylabel("數量 (Count)", color=CHART_BAR_FAIL)
        
        # Line Chart for Cumulative Percentage
        ax2 = self.ax.twinx()
        self._ax2 = ax2
        ax2.plot(indices, cum_pct, color=CHART_SERIES, marker='o', linestyle='-', linewidth=2, zorder=3)
        ax2.set_ylabel("累積比例 (Cumulative %)", color=CHART_SERIES)
        ax2.set_ylim(0, 110)

        # 80% Pareto reference line (vital-few threshold)
        ax2.axhline(
            80,
            color=CHART_BAR_FAIL,
            linestyle="--",
            linewidth=1.2,
            zorder=2,
            label="80% 基準 (Vital Few)",
        )
        ax2.text(
            len(indices) - 0.5, 81,
            "80%",
            color=CHART_BAR_FAIL,
            fontsize=CHART_FONT_LABEL,
            ha="right",
            va="bottom",
        )

        # Add labels for percentage
        annotation_labels = build_sparse_tick_labels(
            categories,
            self._SPARSE_LABEL_THRESHOLD,
            self._SPARSE_STEP_SMALL,
            self._SPARSE_STEP_LARGE,
        )
        for i, pct in enumerate(cum_pct):
            if annotation_labels[i] == "":
                continue
            ax2.text(i, pct + 2, f"{pct:.1f}%", ha='center', va='bottom', fontsize=CHART_FONT_LABEL, color=CHART_SERIES)
            
        # Prevent twinx tight layout clipping
        # layout handled by BaseChart
        self.canvas.draw()
        return True

