"""
三特徵並列趨勢圖（Run Chart 3F）

三條特徵的趨勢圖以垂直並排方式顯示，共用 X 軸（板序 / 樣本序），
支援標準化模式（Z-score）以消除不同量綱的影響。
"""
import numpy as np
from app.charts.base_chart import BaseChart, _apply_mpl_dark_style
from typing import Dict, Any
from app.ui.theme.tokens import (
    CHART_ANNOTATION,
    CHART_CENTERLINE,
    CHART_LINE_STYLE_SECONDARY,
    FEATURE_COLORS,
    FEATURE_COLOR_AREA,
    FEATURE_COLOR_HEIGHT,
    FEATURE_COLOR_VOLUME,
    CHART_FONT_LABEL,
    CHART_FONT_TICK,
    CHART_FONT_LEGEND,
    CHART_FONT_TITLE,
    CHART_FONT_MICRO,
)

_FEAT_COLOR = {
    "Height": FEATURE_COLOR_HEIGHT,
    "Area": FEATURE_COLOR_AREA,
    "Volume": FEATURE_COLOR_VOLUME,
}
_DEFAULT_COLORS = FEATURE_COLORS


def _color_for(feat: str, idx: int) -> str:
    return _FEAT_COLOR.get(feat, _DEFAULT_COLORS[idx % len(_DEFAULT_COLORS)])


class RunChart3F(BaseChart):
    """三特徵並列趨勢圖：每個特徵獨立一列，共用 X 軸。"""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="三特徵趨勢圖並列 (Run Chart 3F)",
            xlabel="樣本序 (PCB Run Order)",
            ylabel="量測值",
            figsize=(8, 7),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """
        engine_output 格式：
          _multi_feature: True
          _features: ["Height", "Area", "Volume"]
          _normalized: bool
          _feature_data: { feat: run_chart_engine_output, ... }
        """
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
            center = stats.get("center_line", float(np.mean(values)) if values else 0)

            color = _color_for(feat, i)

            if normalized and values:
                mean_val = float(stats.get("normalize_mean", np.mean(values)))
                std_val = float(stats.get("normalize_std", np.std(values, ddof=1)))
                if not np.isfinite(std_val) or std_val == 0.0:
                    std_val = 1.0
                values_plot = [(v - mean_val) / std_val for v in values]
                center_plot = 0.0
                ylabel = "Z-score"
            else:
                values_plot = values
                center_plot = center
                ylabel = feat

            _marker = "o" if len(values) <= 300 else None
            _msize = 3 if _marker else 0
            ax.plot(indices, values_plot, color=color, linestyle="-",
                    linewidth=1, marker=_marker, markersize=_msize, label=feat)
            ax.axhline(center_plot, color=CHART_CENTERLINE, linestyle=CHART_LINE_STYLE_SECONDARY,
                       linewidth=1.2, label=f"中心: {center:.3g}")
            if stats.get("sampled_for_display"):
                shown = stats.get("displayed_n", len(values))
                total = stats.get("n", len(values))
                step = stats.get("downsample_step", 1)
                ax.annotate(
                    f"抽樣 {shown}/{total} step={step}",
                    xy=(0.01, 0.96),
                    xycoords="axes fraction",
                    fontsize=CHART_FONT_MICRO,
                    color=CHART_ANNOTATION,
                    va="top",
                )

            ax.set_ylabel(ylabel, fontsize=CHART_FONT_LABEL)
            ax.tick_params(labelsize=CHART_FONT_TICK)
            ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
            # Hide redundant X-axis labels for non-bottom rows
            ax.label_outer()

        axes[-1].set_xlabel("樣本序 (PCB Run Order)", fontsize=CHART_FONT_LABEL)

        title = "三特徵趨勢圖並列"
        if normalized:
            title += "（Z-score 標準化）"
        axes[0].set_title(title, fontsize=CHART_FONT_TITLE)

        self.ax = axes[0]

        self._show_canvas()
        # layout handled by BaseChart
        self.canvas.draw()
        return True
