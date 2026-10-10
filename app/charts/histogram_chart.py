from app.charts.base_chart import BaseChart, _apply_mpl_app_style, draw_reference_line, get_feature_color
from app.ui.theme.tokens import (
    CHART_FILL_EDGE,
    CHART_NORMAL_CURVE,
    CHART_FONT_LABEL,
    CHART_FONT_TICK,
    CHART_FONT_LEGEND,
    CHART_FONT_MICRO,
    CHART_WARNING_MARK,
)
from typing import Dict, Any


# When measurement data and spec limits sit on incompatible scales (e.g. mm data
# vs a percent spec), drawing both on one linear axis crushes the histogram to an
# invisible sliver. Detect that and suppress the spec lines so the distribution
# stays readable, showing an explicit caveat instead.
_SPEC_VISIBILITY_MIN_FRACTION = 0.05
_SCALE_MISMATCH_CAVEAT = "【尺度異常】USL/LSL 與資料尺度差距過大，規格線已隱藏以保留分布可讀性"


def _spec_would_crush_data(bin_edges, *spec_values) -> bool:
    """True when spec limits sit so far outside the data that plotting them would
    collapse the histogram to an invisible sliver (< 5% of the axis span)."""
    specs = [float(v) for v in spec_values if v is not None]
    if not bin_edges or not specs:
        return False
    data_lo = float(bin_edges[0])
    data_hi = float(bin_edges[-1])
    data_span = data_hi - data_lo
    if data_span <= 0:
        return False
    axis_lo = min(data_lo, *specs)
    axis_hi = max(data_hi, *specs)
    axis_span = axis_hi - axis_lo
    if axis_span <= 0:
        return False
    return (data_span / axis_span) < _SPEC_VISIBILITY_MIN_FRACTION


def _fill_for(feat: str, idx: int) -> str:
    """Return consistent semantic fill color (Pass 24)."""
    fill, _ = get_feature_color(feat, idx)
    return fill


class HistogramChart(BaseChart):
    """
    Renders a Distribution Histogram overlaid with a Normal Curve.

    Supports two modes:
    - Single-feature : original behaviour (histogram + normal curve + spec lines)
    - Multi-feature  : 1×N subplots, one per feature, same elements per subplot
    """
    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="分佈與常態曲線 (Distribution & Normal Curve)",
            xlabel="量測值 (Measurement)",
            ylabel="測量次數 (Frequency)",
        )

    # ── Public entry ──────────────────────────────────────────────────

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        self._set_visual_contract_payload(engine_output or {})
        if engine_output.get("_multi_feature"):
            self._draw_multi_feature(engine_output)
            # Return draw success, not canvas.isVisible(): a chart rendered
            # into a hidden tab is still a successful draw.
            return True

        # Single-feature: reset to single axes before drawing
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        _apply_mpl_app_style(self.figure, self.ax)

        metadata = engine_output.get("metadata", {})
        if not metadata.get("is_valid", False):
            error_msg = metadata.get("error", "未知錯誤 / Unknown Error")
            self._show_placeholder(error_msg, self._placeholder_class_for(metadata, error_msg))
            return False

        self._show_canvas()
        self._draw_single(self.ax, engine_output)
        # layout handled by BaseChart
        self.canvas.draw()
        return True

    # ── Single-feature drawing (reused per subplot in multi-feature) ──

    def _draw_single(self, ax, engine_output: Dict[str, Any], feat_label: str = "") -> None:
        ctx = engine_output.get("analysis_context", {})
        col = feat_label or ctx.get("target_col", "")
        color = _fill_for(col, 0)

        data = engine_output.get("data", {})
        stats = engine_output.get("statistics", {})

        bin_edges = data.get("bin_edges", [])
        counts = data.get("counts", [])
        norm_x = data.get("normal_curve_x", [])
        norm_y = data.get("normal_curve_y", [])
        mean_val = stats.get("mean", 0)

        if not bin_edges or not counts:
            ax.text(0.5, 0.5, "無法取得直方圖區間", ha="center", va="center",
                    transform=ax.transAxes, fontsize=CHART_FONT_LABEL)
            return

        bin_widths = [bin_edges[i + 1] - bin_edges[i] for i in range(len(counts))]
        ax.bar(bin_edges[:-1], counts, width=bin_widths, align="edge",
               color=color, edgecolor=CHART_FILL_EDGE, alpha=0.72, label="頻率 (Frequency)")

        if norm_x and norm_y:
            ax.plot(norm_x, norm_y, color=CHART_NORMAL_CURVE, linewidth=2,
                    label="常態曲線 (Normal Curve)")

        draw_reference_line(ax, mean_val, f"Mean: {mean_val:.2f}", orientation="v", semantic="mean")

        usl = engine_output.get("usl")
        lsl = engine_output.get("lsl")
        if _spec_would_crush_data(bin_edges, usl, lsl):
            # Data and spec on incompatible scales: keep the distribution visible.
            ax.set_xlim(bin_edges[0], bin_edges[-1])
            ax.text(0.5, 0.98, _SCALE_MISMATCH_CAVEAT, transform=ax.transAxes,
                    ha="center", va="top", fontsize=CHART_FONT_MICRO, color=CHART_WARNING_MARK)
        else:
            if usl is not None:
                draw_reference_line(ax, usl, f"USL: {usl:.2f}", orientation="v", semantic="spec_limit")
            if lsl is not None:
                draw_reference_line(ax, lsl, f"LSL: {lsl:.2f}", orientation="v", semantic="spec_limit")

        # Cpk annotation in title when available
        cpk = stats.get("cpk")
        title = col
        if cpk is not None:
            title += f"  Cpk={cpk:.3f}"
        ax.set_title(title, fontsize=CHART_FONT_LABEL)
        ax.set_xlabel(f"量測值 ({col})" if col else "量測值", fontsize=CHART_FONT_LABEL)
        ax.set_ylabel("頻率", fontsize=CHART_FONT_LABEL)
        ax.tick_params(labelsize=CHART_FONT_TICK)
        ax.legend(loc="lower right", fontsize=CHART_FONT_LEGEND)

    # ── Multi-feature: 1×N subplots ───────────────────────────────────

    def _draw_multi_feature(self, engine_output: Dict[str, Any]) -> None:
        import numpy as np

        features = engine_output.get("_features", [])
        feature_data = engine_output.get("_feature_data", {})
        normalized = engine_output.get("_normalized", False)
        n = len(features)

        if n == 0:
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            _apply_mpl_app_style(self.figure, self.ax)
            self.ax.text(0.5, 0.5, "無多特徵資料", ha="center", va="center",
                         transform=self.ax.transAxes)
            self._show_canvas()
            self.canvas.draw()
            return

        self.figure.clear()
        self.figure.set_size_inches(max(8, 4 * n), 4)

        for i, feat in enumerate(features):
            ax = self.figure.add_subplot(1, n, i + 1)
            _apply_mpl_app_style(self.figure, ax)

            fd = feature_data.get(feat, {})
            meta = fd.get("metadata", {})

            if not meta.get("is_valid", False):
                ax.text(0.5, 0.5, f"{feat}\n無法分析\n{meta.get('error', '')}",
                        ha="center", va="center", transform=ax.transAxes, fontsize=CHART_FONT_LABEL)
                continue

            self._draw_single_enhanced(ax, fd, feat_label=feat, normalized=normalized, np=np)

        # figure.clear() 後須保留有效的 self.ax，供 BaseChart.clear() 等路徑使用
        if self.figure.axes:
            self.ax = self.figure.axes[0]

        self._show_canvas()
        # layout handled by BaseChart
        self.canvas.draw()

    def _draw_single_enhanced(self, ax, engine_output: Dict[str, Any],
                               feat_label: str = "", normalized: bool = False, np=None) -> None:
        """Enhanced single-subplot renderer: adds Z-score mode, median, target, Cpk+Ppk."""
        if np is None:
            import numpy as _np
            np = _np

        col = feat_label or engine_output.get("analysis_context", {}).get("target_col", "")
        color = _fill_for(col, 0)

        data = engine_output.get("data", {})
        stats = engine_output.get("statistics", {})

        bin_edges = data.get("bin_edges", [])
        counts = data.get("counts", [])
        norm_x = data.get("normal_curve_x", [])
        norm_y = data.get("normal_curve_y", [])
        mean_val = stats.get("mean", 0)
        std_val = stats.get("std", 1)
        if not std_val:  # None, 0, or 0.0 — avoid divide-by-zero
            std_val = 1

        if not bin_edges or not counts:
            ax.text(0.5, 0.5, "無法取得直方圖區間", ha="center", va="center",
                    transform=ax.transAxes, fontsize=CHART_FONT_LABEL)
            return

        # Estimate median from cumulative histogram
        counts_arr = np.array(counts, dtype=float)
        cum = np.cumsum(counts_arr)
        half = cum[-1] / 2.0
        med_idx = int(np.searchsorted(cum, half))
        med_idx = min(med_idx, len(bin_edges) - 2)
        median_val = (bin_edges[med_idx] + bin_edges[med_idx + 1]) / 2.0

        usl = engine_output.get("usl")
        lsl = engine_output.get("lsl")
        target = engine_output.get("target")

        if normalized:
            # Z-score transform: (x - mean) / std
            def _z(v):
                return (v - mean_val) / std_val

            bin_edges_plot = [_z(e) for e in bin_edges]
            norm_x_plot = [_z(x) for x in norm_x] if norm_x else []
            mean_plot = _z(mean_val)
            median_plot = _z(median_val)
            usl_plot = _z(usl) if usl is not None else None
            lsl_plot = _z(lsl) if lsl is not None else None
            target_plot = _z(target) if target is not None else None
            xlabel = f"Z-score ({col})" if col else "Z-score"
        else:
            bin_edges_plot = list(bin_edges)
            norm_x_plot = list(norm_x) if norm_x else []
            mean_plot = mean_val
            median_plot = median_val
            usl_plot = usl
            lsl_plot = lsl
            target_plot = target if target is not None else None
            xlabel = f"量測值 ({col})" if col else "量測值"

        bin_widths = [bin_edges_plot[k + 1] - bin_edges_plot[k] for k in range(len(counts))]
        ax.bar(bin_edges_plot[:-1], counts, width=bin_widths, align="edge",
               color=color, edgecolor=CHART_FILL_EDGE, alpha=0.72)

        if norm_x_plot and norm_y:
            ax.plot(norm_x_plot, norm_y, color=CHART_NORMAL_CURVE, linewidth=2,
                    label="常態曲線")

        draw_reference_line(ax, mean_plot, f"Mean: {mean_val:.3g}", orientation="v", semantic="mean")
        draw_reference_line(ax, median_plot, f"Median: {median_val:.3g}", orientation="v", semantic="median")

        if not normalized and _spec_would_crush_data(bin_edges_plot, usl_plot, lsl_plot, target_plot):
            # Data and spec on incompatible scales (raw mode): keep distribution visible.
            ax.set_xlim(bin_edges_plot[0], bin_edges_plot[-1])
            ax.text(0.5, 0.98, _SCALE_MISMATCH_CAVEAT, transform=ax.transAxes,
                    ha="center", va="top", fontsize=CHART_FONT_MICRO, color=CHART_WARNING_MARK)
        else:
            if target_plot is not None:
                draw_reference_line(ax, target_plot, f"Target: {target:.3g}", orientation="v", semantic="target")
            if usl_plot is not None:
                draw_reference_line(ax, usl_plot, f"USL: {usl:.3g}", orientation="v", semantic="spec_limit")
            if lsl_plot is not None:
                draw_reference_line(ax, lsl_plot, f"LSL: {lsl:.3g}", orientation="v", semantic="spec_limit")

        # Title: feature name + Cpk + Ppk
        cpk = stats.get("cpk")
        ppk = stats.get("ppk")
        title = col
        cap_parts = []
        if cpk is not None:
            cap_parts.append(f"Cpk={cpk:.2f}")
        if ppk is not None:
            cap_parts.append(f"Ppk={ppk:.2f}")
        if cap_parts:
            title += "  " + "  ".join(cap_parts)

        ax.set_title(title, fontsize=CHART_FONT_LABEL)
        ax.set_xlabel(xlabel, fontsize=CHART_FONT_LABEL)
        ax.set_ylabel("頻率", fontsize=CHART_FONT_LABEL)
        ax.tick_params(labelsize=CHART_FONT_TICK)
        ax.legend(loc="lower right", fontsize=CHART_FONT_MICRO)
