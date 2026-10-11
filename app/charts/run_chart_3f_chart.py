"""
三特徵並列趨勢圖（Run Chart 3F）

三條特徵的趨勢圖以垂直並排方式顯示，共用 X 軸（板序 / 樣本序），
支援標準化模式（Z-score）以消除不同量綱的影響。
"""
import numpy as np
from app.charts.base_chart import BaseChart, feature_line_color, add_sample_disclosure, draw_reference_line
from app.charts.run_order_axis import aligned_axis, feature_label_lists, shared_label_positions
from app.charts.multi_feature_panels import (
    zscore_array,
    zscore_scale,
)
from typing import Dict, Any
from app.ui.theme.tokens import (
    CHART_FONT_LABEL,
    CHART_FONT_TICK,
    CHART_FONT_LEGEND,
    CHART_FONT_TITLE,
)


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
        prepared = self._prepare_multi_feature_axes(engine_output)
        if prepared is None:
            return False
        features, feature_data, normalized, axes = prepared
        shared = shared_label_positions(feature_label_lists(features, feature_data))

        for i, feat in enumerate(features):
            ax = axes[i]
            fd = feature_data.get(feat, {})
            if not fd.get("metadata", {}).get("is_valid", False):
                self._draw_invalid_feature_panel([ax], feat)
                continue
            color = feature_line_color(feat, i)
            data = fd.get("data", {})
            stats = fd.get("statistics", {})
            values = data.get("values", [])
            # X = position on the label union shared by all features (sharex axes).
            indices, _ = aligned_axis(data.get("indices"), len(values), shared)
            center = stats["center_line"] if "center_line" in stats else (float(np.mean(values)) if values else 0)

            if normalized and values:
                # Engine-provided normalization basis wins over the displayed sample.
                mean_val, std_val = zscore_scale(
                    values, mean=stats.get("normalize_mean"), std=stats.get("normalize_std")
                )
                values_plot = zscore_array(values, mean_val, std_val).tolist()
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
            draw_reference_line(ax, center_plot, f"中心: {center:.3g}", semantic="centerline")
            # Per-panel sampling disclosure: the top-level 3F payload carries no
            # per-feature displayed_n, so the shared footer would not show it.
            if stats.get("sampled_for_display"):
                add_sample_disclosure(ax, fd)

            ax.set_ylabel(ylabel, fontsize=CHART_FONT_LABEL)
            ax.tick_params(labelsize=CHART_FONT_TICK)
            ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
            # Hide redundant X-axis labels for non-bottom rows
            ax.label_outer()

        title = "三特徵趨勢圖並列"
        if normalized:
            title += "（Z-score 標準化）"
        # layout handled by BaseChart
        axes[-1].set_xlabel("樣本序 (PCB Run Order)", fontsize=CHART_FONT_LABEL)
        axes[0].set_title(title, fontsize=CHART_FONT_TITLE)
        self._finish_multi_feature_axes(axes)
        return True
