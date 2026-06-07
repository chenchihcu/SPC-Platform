"""
三特徵並列 CUSUM 管制圖（CUSUM 3F）

每個特徵各佔一列，共用 X 軸（樣本序）。顯示 C+ / C- 與決策界限 h，
方便比較三個特徵的漂移起始點與方向是否同步。
"""
import numpy as np
from app.charts.base_chart import BaseChart, _apply_mpl_dark_style, sparse_tick_positions_labels
from typing import Dict, Any
from app.ui.theme.tokens import (
    CHART_ANNOTATION,
    CHART_CONTROL_LIMITS,
    CHART_LINE_STYLE_SECONDARY,
    CHART_NEUTRAL_LINE,
    CHART_OOC,
    CHART_SERIES_SECONDARY,
    FEATURE_COLORS,
    FEATURE_COLOR_AREA,
    FEATURE_COLOR_HEIGHT,
    FEATURE_COLOR_VOLUME,
    CHART_FONT_LABEL,
    CHART_FONT_LEGEND,
    CHART_FONT_MICRO,
    CHART_FONT_TICK,
    CHART_FONT_TITLE)

_FEAT_COLOR = {
    "Height": FEATURE_COLOR_HEIGHT,
    "Area": FEATURE_COLOR_AREA,
    "Volume": FEATURE_COLOR_VOLUME,
}
_DEFAULT_COLORS = FEATURE_COLORS


def _color_for(feat: str, idx: int) -> str:
    return _FEAT_COLOR.get(feat, _DEFAULT_COLORS[idx % len(_DEFAULT_COLORS)])


def _zscore_pair(pos_vals: np.ndarray, neg_vals: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    """Normalize C+ and C- (negative side) with a single z-score policy."""
    if pos_vals.size == 0 and neg_vals.size == 0:
        return pos_vals, neg_vals, 0.0, 1.0, 0.0
    combined = np.concatenate([pos_vals, neg_vals])
    mean_val = float(np.mean(combined))
    std_val = float(np.std(combined, ddof=1)) if combined.size > 1 else 0.0
    if std_val <= 0:
        std_val = 1.0
    return (
        (pos_vals - mean_val) / std_val,
        (neg_vals - mean_val) / std_val,
        mean_val,
        std_val,
        (0.0 - mean_val) / std_val,
    )


class CUSUM3F(BaseChart):
    """三特徵並列 CUSUM 管制圖：3 列垂直堆疊，共用 X 軸。"""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="三特徵 CUSUM 管制圖並列 (CUSUM 3F)",
            xlabel="樣本序 (PCB Run Order)",
            ylabel="CUSUM",
            figsize=(8, 7),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        self._set_visual_contract_payload(engine_output or {})
        metadata = engine_output.get("metadata", {})
        if not metadata.get("is_valid", False):
            error_msg = metadata.get("error", "未知錯誤")
            self._show_placeholder(error_msg)
            return False

        features: list[str] = engine_output.get("_features", [])
        feature_data: dict[str, dict] = engine_output.get("_feature_data", {})
        normalized: bool = engine_output.get("_normalized", False)

        if not features or not feature_data:
            self._show_placeholder("無多特徵資料")
            return False

        n = len(features)
        self.figure.clear()
        axes = self.figure.subplots(n, 1, sharex=True)
        axes = [axes] if n == 1 else list(axes)

        for fig_ax in axes:
            _apply_mpl_dark_style(self.figure, fig_ax)

        for i, feat in enumerate(features):
            ax = axes[i]
            color = _color_for(feat, i)

            fd = feature_data.get(feat, {})
            feat_meta = fd.get("metadata", {})
            if not feat_meta.get("is_valid", False):
                ax.text(0.5, 0.5, f"{feat} 無資料", ha="center", va="center",
                        transform=ax.transAxes, fontsize=CHART_FONT_LABEL)
                ax.set_ylabel(feat, fontsize=CHART_FONT_LABEL)
                continue

            data = fd.get("data", {})
            stats = fd.get("statistics", {})
            h_sigma = stats.get("h_sigma", 0)

            # Prefer board_summary lollipop; fall back to detail line chart
            board_summary = data.get("board_summary", {})
            if board_summary and board_summary.get("board_labels"):
                self._draw_board_summary_panel(ax, board_summary, h_sigma, feat, color, normalized)
            else:
                self._draw_detail_panel(ax, data, h_sigma, feat, color, normalized)

            # mu0 annotation
            mu0 = stats.get("mu0", 0)
            mu0_src = stats.get("mu0_source", "data_mean")
            _src = {"spec_target": "規格", "spec_midpoint": "規格中心",
                    "data_mean": "資料均值"}.get(mu0_src, mu0_src)
            ax.annotate(f"mu0={mu0:.3g}（{_src}）",
                        xy=(0.01, 0.97), xycoords="axes fraction",
                        fontsize=CHART_FONT_MICRO, color=CHART_ANNOTATION, va="top")
            if stats.get("mu0_fallback_applied"):
                _dev = stats.get("mu0_fallback_deviation_sigma")
                _dev_txt = f"{float(_dev):.1f}σ" if _dev is not None else "N/A"
                ax.annotate(
                    f"mu0回退（偏差 {_dev_txt}）",
                    xy=(0.01, 0.90), xycoords="axes fraction",
                    fontsize=CHART_FONT_MICRO, color=CHART_OOC, va="top",
                )

            ax.set_ylabel(feat, fontsize=CHART_FONT_LABEL)
            ax.tick_params(labelsize=CHART_FONT_TICK)
            ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
            # Hide redundant X-axis labels for non-bottom rows
            ax.label_outer()

        axes[-1].set_xlabel("樣本序 (PCB Run Order) / 板號 (Board ID)", fontsize=CHART_FONT_LABEL)

        title = "三特徵 CUSUM 管制圖並列"
        if normalized:
            title += "（Z-score 軸；hσ 為原始參數）"
        axes[0].set_title(title, fontsize=CHART_FONT_TITLE)

        self.ax = axes[0]

        self._show_canvas()
        # layout handled by BaseChart
        self.canvas.draw()
        return True

    # ── Panel helpers ──────────────────────────────────────────────────

    def _draw_board_summary_panel(self, ax, summary: dict, h_sigma: float,
                                   feat: str, color: str, normalized: bool) -> None:
        labels = summary["board_labels"]
        max_cp = np.array(summary["max_cp"])
        max_cm = np.array(summary["max_cm"])
        n = len(labels)
        x = np.arange(n)

        cp_raw = max_cp.astype(float)
        cm_raw_neg = -max_cm.astype(float)
        if normalized:
            cp_plot, cm_neg, mean_val, std_val, zero_plot = _zscore_pair(cp_raw, cm_raw_neg)
            h_pos_plot = (float(h_sigma) - mean_val) / std_val
            h_neg_plot = (-float(h_sigma) - mean_val) / std_val
        else:
            cp_plot = cp_raw
            cm_neg = cm_raw_neg
            h_pos_plot = h_sigma
            h_neg_plot = -h_sigma
            zero_plot = 0.0

        ax.vlines(x, 0, cp_plot, color=color, linewidth=1.2, alpha=0.6)
        ax.scatter(x, cp_plot, color=color, s=12, zorder=5, label="C+ peak")
        ax.vlines(x, 0, cm_neg, color=CHART_SERIES_SECONDARY, linewidth=1.2, alpha=0.6)
        ax.scatter(x, cm_neg, color=CHART_SERIES_SECONDARY, s=12, zorder=5, label="C- peak")

        h_label = f"+hσ(raw): {h_sigma:.3g}" if normalized else f"+hσ: {h_sigma:.3g}"
        ax.axhline(h_pos_plot, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.2, label=h_label)
        ax.axhline(h_neg_plot, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.2)
        ax.axhline(zero_plot, color=CHART_NEUTRAL_LINE, linestyle="-", linewidth=0.5)

        ticks, tick_labels = sparse_tick_positions_labels(labels, max_ticks=20)
        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels, rotation=45, fontsize=CHART_FONT_MICRO, ha="right")

    def _draw_detail_panel(self, ax, data: dict, h_sigma: float,
                            feat: str, color: str, normalized: bool) -> None:
        indices = data.get("indices", [])
        cp = data.get("values", [])
        cm = data.get("values_cm", [])
        cm_neg = [-v for v in cm]

        cp_arr = np.array(cp, dtype=float)
        cm_arr = np.array(cm_neg, dtype=float)
        if normalized:
            cp_plot_arr, cm_plot_arr, mean_val, std_val, zero_plot = _zscore_pair(cp_arr, cm_arr)
            cp_plot = cp_plot_arr.tolist()
            cm_plot = cm_plot_arr.tolist()
            h_pos_plot = (float(h_sigma) - mean_val) / std_val
            h_neg_plot = (-float(h_sigma) - mean_val) / std_val
        else:
            cp_plot = cp
            cm_plot = cm_neg
            h_pos_plot = h_sigma
            h_neg_plot = -h_sigma
            zero_plot = 0.0

        ax.plot(indices, cp_plot, color=color, linestyle="-", linewidth=1, label="C+")
        ax.plot(indices, cm_plot, color=CHART_SERIES_SECONDARY, linestyle="-", linewidth=1, label="C-")
        h_label = f"+hσ(raw): {h_sigma:.3g}" if normalized else f"+hσ: {h_sigma:.3g}"
        ax.axhline(h_pos_plot, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.2, label=h_label)
        ax.axhline(h_neg_plot, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.2)
        ax.axhline(zero_plot, color=CHART_NEUTRAL_LINE, linestyle="-", linewidth=0.5)
