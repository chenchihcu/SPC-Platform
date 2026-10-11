"""
三特徵並列 I-MR 管制圖（IMR 3F）

每個特徵各佔一列，每列包含左（Individual 圖）+ 右（MR 圖）兩個子圖，
共 3 列 × 2 欄 = 6 個子圖。共用同一 X 軸，以便跨特徵比對失控位置。
"""
import numpy as np
from app.charts.base_chart import feature_line_color as _color_for, BaseChart
from app.charts.run_order_axis import (
    aligned_axis,
    feature_label_lists,
    marker_points,
    mr_positions,
    shared_label_positions,
)
from app.ui.theme.tokens import (
    CHART_CENTERLINE,
    CHART_CONTROL_LIMITS,
    CHART_LINE_STYLE_SECONDARY,
    CHART_OOC,
    CHART_OOC_MARKER_SIZE,
    CHART_SERIES_MARKER_SIZE,
    CHART_FONT_ANNOTATION,
    CHART_FONT_LABEL,
    CHART_FONT_MICRO,
    CHART_FONT_TICK)
from typing import Dict, Any

_MR_D4 = 3.267  # D4 constant for n=2


class IMR3F(BaseChart):
    """三特徵並列 I-MR 管制圖：3 列 × 2 欄（左 = I 圖，右 = MR 圖）。"""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="三特徵 I-MR 管制圖並列 (I-MR 3F)",
            xlabel="樣本序 (PCB Run Order)",
            ylabel="量測值",
            figsize=(10, 8),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        prepared = self._prepare_multi_feature_axes(engine_output, columns=2)
        if prepared is None:
            return False
        features, feature_data, _normalized, axes = prepared
        n = len(features)
        shared = shared_label_positions(feature_label_lists(features, feature_data))

        for i, feat in enumerate(features):
            ax_i = axes[i][0]  # Individual chart
            ax_mr = axes[i][1]  # MR chart
            color = _color_for(feat, i)

            fd = feature_data.get(feat, {})
            feat_meta = fd.get("metadata", {})
            if not feat_meta.get("is_valid", False):
                ax_i.text(0.5, 0.5, f"{feat} 無資料", ha="center", va="center",
                          transform=ax_i.transAxes, fontsize=CHART_FONT_LABEL)
                ax_mr.text(0.5, 0.5, "—", ha="center", va="center",
                           transform=ax_mr.transAxes, fontsize=CHART_FONT_LABEL)
                ax_i.set_ylabel(feat, fontsize=CHART_FONT_LABEL)
                continue

            data = fd.get("data", {})
            stats = fd.get("statistics", {})

            y_values = data.get("values", [])
            # X = 1-based position in analysis order; labels only locate OOC / MR points.
            indices, label_pos = aligned_axis(data.get("indices"), len(y_values), shared)
            ooc = data.get("out_of_control_indices", [])
            cl = stats["cl"] if "cl" in stats else (float(np.mean(y_values)) if y_values else 0)
            ucl = stats.get("ucl", 0)
            lcl = stats.get("lcl", 0)

            _n = len(y_values)
            _marker = "o" if _n <= 300 else None
            _msize = CHART_SERIES_MARKER_SIZE if _marker else 0

            # ── I chart ────────────────────────────────────────────────
            ax_i.plot(indices, y_values, marker=_marker, color=color,
                      linestyle="-", markersize=_msize, label=feat)

            if ooc:
                ooc_idx, ooc_vals = marker_points(ooc, label_pos, y_values, indices)
                if ooc_idx and ooc_vals:
                    _s = CHART_OOC_MARKER_SIZE ** 2 if _n <= 300 else max(3, CHART_OOC_MARKER_SIZE - 4) ** 2
                    ax_i.scatter(ooc_idx, ooc_vals, color=CHART_OOC, s=_s, zorder=5)

            ax_i.axhline(cl,  color=CHART_CENTERLINE,     linestyle="-",  linewidth=1.2)
            ax_i.axhline(ucl, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.2)
            ax_i.axhline(lcl, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.2)

            # Annotate limits at right edge
            x_max = max(indices) if indices else 0
            for val, name in [(ucl, "UCL"), (lcl, "LCL"), (cl, "CL")]:
                c = CHART_CENTERLINE if name == "CL" else CHART_CONTROL_LIMITS
                ax_i.annotate(f"{name} {val:.3g}", xy=(x_max, val),
                              xytext=(4, 0), textcoords="offset points",
                              fontsize=CHART_FONT_MICRO, color=c, va="center")

            ooc_count = len(ooc)
            ax_i.text(0.99, 0.99, f"OOC={ooc_count}", transform=ax_i.transAxes,
                      ha="right", va="top", fontsize=CHART_FONT_ANNOTATION,
                      color=CHART_OOC if ooc_count > 0 else CHART_CENTERLINE)
            ax_i.set_ylabel(feat, fontsize=CHART_FONT_LABEL)
            ax_i.set_title(f"{feat} — I 圖", fontsize=CHART_FONT_LABEL)
            ax_i.tick_params(labelsize=CHART_FONT_TICK)

            # ── MR chart ───────────────────────────────────────────────
            mr_values = data.get("mr_values", [])
            mr_bar = stats.get("mr_bar", 0)
            if mr_values:
                mr_indices = mr_positions(data.get("mr_indices"), label_pos, len(mr_values))
                mr_ucl = mr_bar * _MR_D4
                _mr_marker = "o" if len(mr_values) <= 300 else None
                _mr_msize = CHART_SERIES_MARKER_SIZE if _mr_marker else 0
                ax_mr.plot(mr_indices, mr_values, marker=_mr_marker, color=color,
                           linestyle="-", markersize=_mr_msize, label="MR")
                ax_mr.axhline(mr_bar, color=CHART_CENTERLINE,     linestyle="-",  linewidth=1.2)
                ax_mr.axhline(mr_ucl, color=CHART_CONTROL_LIMITS, linestyle=CHART_LINE_STYLE_SECONDARY, linewidth=1.2)
                x_max_mr = max(mr_indices) if mr_indices else 0
                ax_mr.annotate(f"UCL {mr_ucl:.3g}", xy=(x_max_mr, mr_ucl),
                               xytext=(4, 0), textcoords="offset points",
                               fontsize=CHART_FONT_MICRO, color=CHART_CONTROL_LIMITS, va="center")
                ax_mr.annotate(f"CL {mr_bar:.3g}", xy=(x_max_mr, mr_bar),
                               xytext=(4, 0), textcoords="offset points",
                               fontsize=CHART_FONT_MICRO, color=CHART_CENTERLINE, va="center")
            ax_mr.set_ylabel("MR", fontsize=CHART_FONT_LABEL)
            ax_mr.set_title(f"{feat} — MR 圖", fontsize=CHART_FONT_LABEL)
            ax_mr.tick_params(labelsize=CHART_FONT_TICK)
            
            # Hide redundant X-axis labels for non-bottom rows (Pass 25 audit)
            if i < n - 1:
                ax_i.tick_params(labelbottom=False)
                ax_mr.tick_params(labelbottom=False)
                ax_i.set_xlabel("")
                ax_mr.set_xlabel("")

        # X-axis labels on bottom row only
        axes[-1][0].set_xlabel("樣本序 (PCB Run Order)", fontsize=CHART_FONT_LABEL)
        axes[-1][1].set_xlabel("樣本序 (PCB Run Order)", fontsize=CHART_FONT_LABEL)

        self._finish_multi_feature_axes(axes, columns=2)
        return True
