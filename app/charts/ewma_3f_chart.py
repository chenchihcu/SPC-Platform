"""
三特徵並列 EWMA 管制圖（EWMA 3F）

每個特徵各佔一列，共用 X 軸（樣本序）。標準化模式時顯示各特徵的
EWMA 相對偏移（以均值正規化），方便跨特徵比較漂移速度與方向。
"""
import numpy as np
from app.charts.base_chart import BaseChart, feature_line_color, draw_reference_line
from app.charts.run_order_axis import aligned_axis, feature_label_lists, marker_points, shared_label_positions
from app.charts.multi_feature_panels import (
    zscore_array,
    zscore_scale,
    zscore_value,
)
from typing import Dict, Any
from app.ui.theme.tokens import (
    CHART_OOC,
    CHART_FONT_LABEL,
    CHART_FONT_LEGEND,
    CHART_FONT_TICK,
    CHART_FONT_TITLE)


def _zscore_with_limits(values: list[float], cl: float, ucl: float, lcl: float) -> tuple[list[float], float, float, float]:
    """Apply one normalization policy (z-score) to values and control limits."""
    if len(values) == 0:
        return values, cl, ucl, lcl
    mean_val, std_val = zscore_scale(values)
    return (
        zscore_array(values, mean_val, std_val).tolist(),
        zscore_value(cl, mean_val, std_val),
        zscore_value(ucl, mean_val, std_val),
        zscore_value(lcl, mean_val, std_val),
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
            # X = 1-based position in analysis order; labels only locate OOC points.
            indices, label_pos = aligned_axis(data.get("indices"), len(values), shared)
            ooc = data.get("out_of_control_indices", [])
            cl = stats["cl"] if "cl" in stats else (float(np.mean(values)) if values else 0)
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
                ooc_idx, ooc_vals = marker_points(ooc, label_pos, values_plot)
                if ooc_idx and ooc_vals:
                    ax.scatter(ooc_idx, ooc_vals, color=CHART_OOC, zorder=5, s=25, label="OOC")

            # Labels always carry raw values; only the y position is z-scored.
            draw_reference_line(ax, cl_plot, f"CL: {cl:.3g}", semantic="centerline")
            draw_reference_line(ax, ucl_plot, f"UCL: {ucl:.3g}", semantic="control_limit")
            draw_reference_line(ax, lcl_plot, f"LCL: {lcl:.3g}", semantic="control_limit")

            ax.set_ylabel(ylabel, fontsize=CHART_FONT_LABEL)
            ax.tick_params(labelsize=CHART_FONT_TICK)
            ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)
            # Hide redundant X-axis labels for non-bottom rows
            ax.label_outer()

        title = "三特徵 EWMA 管制圖並列"
        if normalized:
            title += "（Z-score 標準化）"
        # layout handled by BaseChart
        axes[-1].set_xlabel("樣本序 (PCB Run Order)", fontsize=CHART_FONT_LABEL)
        axes[0].set_title(title, fontsize=CHART_FONT_TITLE)
        self._finish_multi_feature_axes(axes)
        return True
