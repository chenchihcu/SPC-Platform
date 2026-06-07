from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from app.charts.mpl_font_config import setup_mpl_cjk_font
setup_mpl_cjk_font()
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from app.charts.base_chart import _apply_mpl_dark_style
from app.analytics.chart_registry import format_chart_description, format_chart_description_compact
from app.ui.theme.tokens import (
    ACCENT_PRIMARY,
    ACCENT_SUCCESS,
    ACCENT_ERROR,
    TEXT_PRIMARY,
    FEATURE_COLOR_HEIGHT,
    FEATURE_COLOR_AREA,
    FEATURE_COLOR_VOLUME,
    FEATURE_COLORS,
    CHART_FONT_TITLE,
    CHART_FONT_LABEL,
    CHART_FONT_ANNOTATION,
)

# Per-feature colour cycle (matches BoxplotChart palette)
_FEAT_COLORS = {
    "Height": FEATURE_COLOR_HEIGHT,
    "Area": FEATURE_COLOR_AREA,
    "Volume": FEATURE_COLOR_VOLUME,
}
_DEFAULT_COLORS = FEATURE_COLORS


def _color_for(feat: str, idx: int) -> str:
    return _FEAT_COLORS.get(feat, _DEFAULT_COLORS[idx % len(_DEFAULT_COLORS)])


class NormalityTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.lbl_desc = QLabel(format_chart_description_compact("normality"))
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setProperty("class", "chartDescCompact")

        self.lbl_desc.setToolTip(format_chart_description("normality"))
        self.lbl_desc.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self.lbl_desc)

        self.lbl_stats = QLabel("載入中... (Waiting for Data)")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stats.setProperty("class", "statsResult")
        layout.addWidget(self.lbl_stats)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, 1)

        # ax is (re-)created in update_data; initialise with a single subplot
        self.ax = self.figure.add_subplot(111)
        _apply_mpl_dark_style(self.figure, self.ax)

        self._last_payload: dict = {}

    @staticmethod
    def _format_sampling_note(stats: dict) -> str:
        total_n = stats.get("total_n")
        tested_n = stats.get("tested_n")
        if total_n is None or tested_n is None:
            return ""
        if stats.get("sampled_for_test"):
            return f"  |  檢定樣本: {tested_n}/{total_n}（抽樣）"
        return f"  |  檢定樣本: {tested_n}/{total_n}"

    # ── update_data ───────────────────────────────────────────────────

    def update_data(self, data: dict) -> None:
        """Dispatch to multi-feature or single-feature rendering."""
        self._last_payload = data or {}
        self.figure.clear()

        if self._last_payload.get("_multi_feature"):
            self._draw_multi_feature(self._last_payload)
        else:
            # Recreate single axes and draw
            self.ax = self.figure.add_subplot(111)
            _apply_mpl_dark_style(self.figure, self.ax)

            ctx = data.get("analysis_context", {})
            desc_ctx = {"target_col": ctx.get("target_col")}
            self.lbl_desc.setText(format_chart_description_compact("normality", desc_ctx))
            self.lbl_desc.setToolTip(format_chart_description("normality", desc_ctx))

            self._draw_normality_chart(data)

    # ── Single-feature (original logic, refactored to use self.ax) ────

    def _draw_normality_chart(self, data: dict) -> None:
        """Draw Q-Q normality chart on the current self.ax."""
        self.ax.clear()
        _apply_mpl_dark_style(self.figure, self.ax)

        meta = data.get("metadata", {})
        ctx = data.get("analysis_context", {})
        if not meta.get("is_valid", False):
            self.ax.set_title("常態機率圖 (Normal Probability Plot Q-Q)")
            self.ax.set_xlabel("理論分位數 (Theoretical Quantiles)")
            self.ax.set_ylabel("實際資料值 (Ordered Values)")
            self.lbl_stats.setText(f"無法進行常態分析：{meta.get('error', '未知錯誤')}")
            self.canvas.draw()
            return

        chart_data = data.get("data", {})
        stats = data.get("statistics", {})

        th_q = chart_data.get("theoretical_q", [])
        ac_q = chart_data.get("actual_q", [])
        line_x = chart_data.get("line_x", [])
        line_y = chart_data.get("line_y", [])

        self.ax.scatter(th_q, ac_q, color=ACCENT_PRIMARY, edgecolors=TEXT_PRIMARY,
                        alpha=0.6, label="資料點 (Data)")
        self.ax.plot(line_x, line_y, color=ACCENT_ERROR, linestyle="--",
                     linewidth=2, label="常態擬合線 (Normal Fit)")

        self.ax.set_title("常態機率圖 (Normal Probability Plot Q-Q)")
        self.ax.set_xlabel("理論分位數 (Theoretical Quantiles)")
        ylabel = "實際資料值 (Ordered Values)"
        if ctx.get("target_col"):
            ylabel = f"實際資料值 ({ctx['target_col']})"
        self.ax.set_ylabel(ylabel)
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.legend()
        sampling_note = self._format_sampling_note(stats)
        if sampling_note:
            self.ax.annotate(
                sampling_note.replace("  |  ", ""),
                xy=(0.01, 0.97),
                xycoords="axes fraction",
                fontsize=CHART_FONT_ANNOTATION,
                color=TEXT_PRIMARY,
                va="top",
            )

        p_val = stats.get("p_value", 0)
        is_normal = stats.get("is_normal", False)
        test_name = stats.get("test_name", "Test")
        r_sq = stats.get("r_squared", 0)
        result_text = "符合常態分配 (Normal)" if is_normal else "不符合常態分配 (Non-Normal)"
        self.lbl_stats.setProperty("class", "status-ok" if is_normal else "status-error")
        self.lbl_stats.setText(
            f"檢定方法: {test_name}  |  P-Value: {p_val:.5f}  |  R²: {r_sq:.4f}  |  "
            f"結論: {result_text}"
            f"{sampling_note}"
        )
        self.lbl_stats.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_stats.style().unpolish(self.lbl_stats)
        self.lbl_stats.style().polish(self.lbl_stats)

        self.figure.tight_layout()
        self.canvas.draw()

    # ── Multi-feature: side-by-side Q-Q subplots ─────────────────────

    def _draw_multi_feature(self, data: dict) -> None:
        """Draw one Q-Q subplot per feature, arranged in a single row."""
        features: list[str] = data.get("_features", [])
        feature_data: dict[str, dict] = data.get("_feature_data", {})
        n = len(features)

        if n == 0:
            self.ax = self.figure.add_subplot(111)
            _apply_mpl_dark_style(self.figure, self.ax)
            self.ax.text(0.5, 0.5, "無多特徵資料", ha="center", va="center",
                         transform=self.ax.transAxes)
            self.canvas.draw()
            return

        # Update description label
        desc_ctx = {"selected_features": features}
        self.lbl_desc.setText(format_chart_description_compact("normality", desc_ctx))
        self.lbl_desc.setToolTip(format_chart_description("normality", desc_ctx))

        # Widen figure for multiple subplots
        self.figure.set_size_inches(max(8, 4 * n), 5)

        stats_parts: list[str] = []
        for i, feat in enumerate(features):
            ax = self.figure.add_subplot(1, n, i + 1)
            _apply_mpl_dark_style(self.figure, ax)
            color = _color_for(feat, i)

            fd = feature_data.get(feat, {})
            meta = fd.get("metadata", {})
            chart_data = fd.get("data", {})
            stats = fd.get("statistics", {})

            ax.set_title(feat, fontsize=CHART_FONT_TITLE)
            ax.set_xlabel("理論分位數", fontsize=CHART_FONT_LABEL)
            ax.set_ylabel(f"實際值 ({feat})", fontsize=CHART_FONT_LABEL)
            ax.tick_params(labelsize=CHART_FONT_ANNOTATION)

            if not meta.get("is_valid", False):
                ax.text(0.5, 0.5, f"無法分析\n{meta.get('error', '')}",
                        ha="center", va="center", transform=ax.transAxes, fontsize=CHART_FONT_LABEL)
                stats_parts.append(f"{feat}: 無法分析")
                continue

            th_q = chart_data.get("theoretical_q", [])
            ac_q = chart_data.get("actual_q", [])
            line_x = chart_data.get("line_x", [])
            line_y = chart_data.get("line_y", [])

            ax.scatter(th_q, ac_q, color=color, edgecolors=TEXT_PRIMARY, alpha=0.6, s=18)
            ax.plot(line_x, line_y, color=ACCENT_ERROR, linestyle="--", linewidth=1.8)
            ax.grid(True, linestyle="--", alpha=0.4)

            p_val = stats.get("p_value", 0)
            is_normal = stats.get("is_normal", False)
            test_name = stats.get("test_name", "Test")
            result = "常態 (OK)" if is_normal else "非常態 (NG)"
            result_col = ACCENT_SUCCESS if is_normal else ACCENT_ERROR
            ax.set_title(
                f"{feat}  [{test_name}  p={p_val:.4f}]",
                fontsize=CHART_FONT_LABEL,
                color=result_col,
            )
            sample_note = self._format_sampling_note(stats).replace("  |  ", "")
            if sample_note:
                ax.annotate(
                    sample_note,
                    xy=(0.01, 0.96),
                    xycoords="axes fraction",
                    fontsize=CHART_FONT_ANNOTATION,
                    color=TEXT_PRIMARY,
                    va="top",
                )
            stats_parts.append(f"{feat}: p={p_val:.4f} [{result}]" + (f" | {sample_note}" if sample_note else ""))

        self.lbl_stats.setText("　｜　".join(stats_parts))
        self.lbl_stats.setTextFormat(Qt.TextFormat.PlainText)

        # Empty valid set means "not analyzable", never "all normal".
        valid_results = [
            fd for fd in feature_data.values()
            if fd.get("metadata", {}).get("is_valid")
        ]
        all_normal = bool(valid_results) and all(
            fd.get("statistics", {}).get("is_normal", False)
            for fd in valid_results
        )
        status_cls = "statsResultNormal" if all_normal else "statsResultAbnormal"
        self.lbl_stats.setProperty("class", status_cls)

        self.lbl_stats.style().unpolish(self.lbl_stats)
        self.lbl_stats.style().polish(self.lbl_stats)

        if self.figure.axes:
            self.ax = self.figure.axes[0]

        self.figure.tight_layout()
        self.canvas.draw()
