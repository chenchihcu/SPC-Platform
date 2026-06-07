"""
三特徵並列 EWMA 管制圖（EWMA 3F）

每個特徵各佔一列，共用 X 軸（樣本序）。標準化模式時顯示各特徵的
EWMA 相對偏移（以均值正規化），方便跨特徵比較漂移速度與方向。
"""
import numpy as np
from app.charts.base_chart import BaseChart, _apply_mpl_dark_style
from typing import Dict, Any
from app.ui.theme.tokens import (
    CHART_CENTERLINE,
    CHART_CONTROL_LIMITS,
    CHART_LINE_STYLE_SECONDARY,
    CHART_OOC,
    FEATURE_COLORS,
    FEATURE_COLOR_AREA,
    FEATURE_COLOR_HEIGHT,
    FEATURE_COLOR_VOLUME,
    CHART_FONT_LABEL,
    CHART_FONT_LEGEND,
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


def _zscore_with_limits(values: list[float], cl: float, ucl: float, lcl: float) -> tuple[list[float], float, float, float]:
    """Apply one normalization policy (z-score) to values and control limits."""
    arr = np.array(values, dtype=float)
    if arr.size == 0:
        return values, cl, ucl, lcl
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    if std_val <= 0:
        std_val = 1.0
    values_plot = ((arr - mean_val) / std_val).tolist()
    return (
        values_plot,
        (float(cl) - mean_val) / std_val,
        (float(ucl) - mean_val) / std_val,
        (float(lcl) - mean_val) / std_val,
    )


class EWMA3F(BaseChart):
    """三特徵並列 EWMA 管制圖：3 列垂直堆疊，共用 X 軸。"""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="三特徵 EWMA 管制圖並列 (EWMA 3F)",
            xlabel="樣本序 (PCB Run Order)",
            ylabel="EWMA 值",
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
            values = data.get("values", [])
            indices = data.get("indices", list(range(len(values))))
            ooc = data.get("out_of_control_indices", [])
            cl = stats.get("cl", float(np.mean(values)) if values else 0)
            ucl = stats.get("ucl", 0)
            lcl = stats.get("lcl", 0)

            if normalized and values:
                values_plot, cl_plot, ucl_plot, lcl_plot = _zscore_with_limits(values, cl, ucl, lcl)
                ylabel = "Z-score"
            else:
                values_plot = values
                cl_plot, ucl_plot, lcl_plot = cl, ucl, lcl
                ylabel = feat

            ax.plot(indices, values_plot, color=color, linestyle="-",
                    linewidth=1.5, label=f"EWMA ({feat})")

            if ooc:
                idx_map = {idx: k for k, idx in enumerate(indices)}
                ooc_vals = [values_plot[idx_map[idx]] for idx in ooc if idx in idx_map]
                ooc_idx = [idx for idx in ooc if idx in idx_map]
                if ooc_idx and ooc_vals:
                    ax.scatter(ooc_idx, ooc_vals, color=CHART_OOC, zorder=5, s=25, label="OOC")

            ax.axhline(cl_plot,  color=CHART_CENTERLINE, linestyle="-",  linewidth=1.2,
                       label=f"CL: {cl:.3g}")
            ax.axhline(ucl_plot, color=CHART_CONTROL_LIMITS,   linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.2,
                       label=f"UCL: {ucl:.3g}")
            ax.axhline(lcl_plot, color=CHART_CONTROL_LIMITS,   linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.2,
                       label=f"LCL: {lcl:.3g}")

            ax.set_ylabel(ylabel, fontsize=CHART_FONT_LABEL)
            ax.tick_params(labelsize=CHART_FONT_TICK)
            ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
            # Hide redundant X-axis labels for non-bottom rows
            ax.label_outer()

        axes[-1].set_xlabel("樣本序 (PCB Run Order)", fontsize=CHART_FONT_LABEL)

        title = "三特徵 EWMA 管制圖並列"
        if normalized:
            title += "（Z-score 標準化）"
        axes[0].set_title(title, fontsize=CHART_FONT_TITLE)

        self.ax = axes[0]

        self._show_canvas()
        # layout handled by BaseChart
        self.canvas.draw()
        return True
