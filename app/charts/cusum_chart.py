import numpy as np
from app.charts.base_chart import BaseChart, resolve_target_col, sparse_tick_positions_labels
from app.ui.theme.tokens import (
    CHART_ANNOTATION,
    CHART_CONTROL_LIMITS,
    CHART_LINE_STYLE_SECONDARY,
    CHART_NEUTRAL_LINE,
    CHART_OOC,
    CHART_SERIES,
    CHART_SERIES_SECONDARY,
    CHART_FONT_ANNOTATION,
    CHART_FONT_LEGEND)
from typing import Dict, Any


class CUSUMChart(BaseChart):
    """Renders CUSUM chart (C+ and C- with decision limit)."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="CUSUM 管制圖",
            xlabel="樣本序 (PCB Run Order)",
            ylabel="CUSUM",
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False
        target_col = resolve_target_col(engine_output)
        data = engine_output.get("data", {})
        stats = engine_output.get("statistics", {})
        h_sigma = stats.get("h_sigma", 0)

        board_summary = data.get("board_summary", {})
        if board_summary and board_summary.get("board_labels"):
            self._draw_board_summary(board_summary, h_sigma, target_col)
        else:
            self._draw_detail(data, h_sigma, target_col)

        # Show mu0 source annotation
        mu0 = stats.get("mu0", 0)
        mu0_src = stats.get("mu0_source", "data_mean")
        _src_label = {"spec_target": "鋼板規格", "spec_midpoint": "規格中心",
                      "data_mean": "資料平均"}.get(mu0_src, mu0_src)
        self.ax.annotate(
            f"mu0={mu0:.4f}（{_src_label}）",
            xy=(0.01, 0.97), xycoords="axes fraction",
            fontsize=CHART_FONT_ANNOTATION, color=CHART_ANNOTATION, va="top",
        )
        if stats.get("mu0_fallback_applied"):
            _dev = stats.get("mu0_fallback_deviation_sigma")
            _dev_txt = f"{float(_dev):.1f}σ" if _dev is not None else "N/A"
            self.ax.annotate(
                f"mu0回退：目標與資料均值偏差過大（{_dev_txt}）",
                xy=(0.01, 0.91), xycoords="axes fraction",
                fontsize=CHART_FONT_ANNOTATION, color=CHART_OOC, va="top",
            )

        self.ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
        # layout handled by BaseChart
        self.canvas.draw()
        return True

    # ── Board-level summary (全批) ─────────────────────────────────

    def _draw_board_summary(self, summary: dict, h_sigma: float, target_col: str):
        """Lollipop chart: one point per board showing peak C+ / C-."""
        labels = summary["board_labels"]
        max_cp = np.array(summary["max_cp"])
        max_cm = np.array(summary["max_cm"])
        ooc = summary.get("ooc_flags", [])
        n = len(labels)
        x = np.arange(n)

        # C+ (above 0) — lollipop
        self.ax.vlines(x, 0, max_cp, color=CHART_SERIES, linewidth=1.2, alpha=0.6)
        self.ax.scatter(x, max_cp, color=CHART_SERIES, s=14, zorder=5, label="C+ peak")

        # C- (below 0, negated) — lollipop
        cm_neg = -max_cm
        self.ax.vlines(x, 0, cm_neg, color=CHART_SERIES_SECONDARY, linewidth=1.2, alpha=0.6)
        self.ax.scatter(x, cm_neg, color=CHART_SERIES_SECONDARY, s=14, zorder=5, label="C- peak")

        # OOC boards — red highlight
        if ooc:
            ooc_arr = np.array(ooc, dtype=bool)
            if np.any(ooc_arr):
                ooc_x = x[ooc_arr]
                ooc_y_cp = max_cp[ooc_arr]
                ooc_y_cm = cm_neg[ooc_arr]
                # Mark whichever side exceeded h
                exceed_cp = ooc_y_cp > h_sigma
                exceed_cm = ooc_y_cm < -h_sigma
                if np.any(exceed_cp):
                    self.ax.scatter(ooc_x[exceed_cp], ooc_y_cp[exceed_cp],
                                    color=CHART_OOC, s=28, zorder=6, marker="x",
                                    linewidths=1.5, label="OOC")
                if np.any(exceed_cm):
                    self.ax.scatter(ooc_x[exceed_cm], ooc_y_cm[exceed_cm],
                                    color=CHART_OOC, s=28, zorder=6, marker="x",
                                    linewidths=1.5)

        # Decision limits
        self.ax.axhline( h_sigma, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.5,
                          label=f"+hσ: {h_sigma:.2f}")
        self.ax.axhline(-h_sigma, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.5,
                          label=f"-hσ: {-h_sigma:.2f}")
        self.ax.axhline(0, color=CHART_NEUTRAL_LINE, linestyle="-", linewidth=0.5)

        # Axis labels
        self.ax.set_title("CUSUM 板級摘要")
        self.ax.set_xlabel("板號 (Board ID)")
        self.ax.set_ylabel("累積偏移量 (CUSUM Peak)")

        # X-tick labels (sample when too many; keep first/last visible)
        ticks, tick_labels = sparse_tick_positions_labels(labels, max_ticks=20)
        self.ax.set_xticks(ticks)
        self.ax.set_xticklabels(tick_labels, rotation=45, fontsize=CHART_FONT_ANNOTATION, ha="right")

    # ── Pad-level detail (single board) ────────────────────────────

    def _draw_detail(self, data: dict, h_sigma: float, target_col: str):
        """Line chart for single-board or no-board-info CUSUM."""
        indices = data.get("indices", [])
        cp = data.get("values", [])
        cm = data.get("values_cm", [])
        cm_neg = [-v for v in cm]

        self.ax.plot(indices, cp,     color=CHART_SERIES, linestyle="-", linewidth=1, label="C+")
        self.ax.plot(indices, cm_neg, color=CHART_SERIES_SECONDARY, linestyle="-", linewidth=1, label="C-")
        self.ax.axhline( h_sigma, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.5,
                          label=f"+hσ: {h_sigma:.2f}")
        self.ax.axhline(-h_sigma, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.5,
                          label=f"-hσ: {-h_sigma:.2f}")
        self.ax.axhline(0, color=CHART_NEUTRAL_LINE, linestyle="-", linewidth=0.5)

        self.ax.set_title("CUSUM 管制圖")
        self.ax.set_xlabel("樣本序 (PCB Run Order)")
        if target_col:
            self.ax.set_ylabel(f"CUSUM ({target_col})")
