from app.charts.base_chart import BaseChart, build_sparse_tick_labels, draw_reference_line, get_feature_color
from typing import Dict, Any
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from app.ui.theme.tokens import (
    CHART_FILL_EDGE,
    CHART_OOC,
    CHART_WARNING_MARK,
    CHART_FONT_LEGEND,
    CHART_FONT_LABEL,
    CHART_FONT_TITLE)


def _color_for(feat: str, idx: int) -> tuple[str, str]:
    """Return consistent semantic color tuple (Pass 24)."""
    return get_feature_color(feat, idx)


class BoxplotChart(BaseChart):
    """
    Renders boxplots displaying Median, Quartiles, and Outliers across groupings.

    Supports two modes:
    - Single-feature  : original behaviour (one Y-axis, groups = RefDes / PartType)
    - Multi-feature   : side-by-side boxes per group, one colour per feature;
                        optional normalisation to % of each feature's median.
    """
    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="元件群組比較 (Component Boxplot Comparison)",
            xlabel="元件或群組 (Component / Subgroup)",
            ylabel="量測值 (Measurement)",
        )

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


    # ── Public entry ──────────────────────────────────────────────────

    @staticmethod
    def _draw_feature_boxplot(
        ax,
        arrays: list,
        labels: list[str],
        *,
        fill_face,
        edge_color,
        flier_face,
        width: float,
        marker_size: int = 5,
    ) -> None:
        """Render one feature's boxplot with consistent style tokens."""
        ax.boxplot(
            arrays,
            tick_labels=labels,
            widths=width,
            patch_artist=True,
            boxprops=dict(facecolor=fill_face, edgecolor=edge_color, linewidth=1.5),
            medianprops=dict(color=CHART_OOC, linewidth=2),
            flierprops=dict(
                marker="o",
                markerfacecolor=flier_face,
                markersize=marker_size,
                linestyle="none",
                markeredgecolor=CHART_FILL_EDGE,
            ),
            whiskerprops=dict(color=edge_color, linewidth=1.2),
            capprops=dict(color=edge_color, linewidth=1.2),
        )

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """Render the chart with the given payload data."""
        if not super().draw_chart(engine_output):
            return False

        if engine_output.get("_overview_3f"):
            self._draw_overview_3f(engine_output)
        elif engine_output.get("_multi_feature"):
            self._draw_multi_feature(engine_output)
        else:
            self._draw_single_feature(engine_output)
        return self.canvas.isVisible()

    # ── Single-feature (original logic) ──────────────────────────────

    def _draw_single_feature(self, engine_output: Dict[str, Any]) -> None:
        data = engine_output.get("data", {})
        labels = data.get("labels", [])
        arrays = data.get("arrays", [])

        if not labels or not arrays:
            metadata = engine_output.get("metadata", {})
            self._show_placeholder(
                "無有效的群組資料能分析 (Missing Subgroups)",
                self._placeholder_class_for(metadata, "無資料")
            )
            return

        n = len(labels)
        total_n = n

        if n <= 15:
            self.figure.set_size_inches(6, 4)
        else:
            w = min(6 + 0.3 * n, 24)
            self.figure.set_size_inches(w, 4)

        ctx = engine_output.get("analysis_context", {})
        if ctx.get("target_col"):
            self.ax.set_ylabel(f"量測值 ({ctx['target_col']})")

        _grouping_mode = engine_output.get("_grouping_mode", "")
        _group_col = engine_output.get("_group_col", "")
        _xlabel_map: Dict[str, str] = {
            "board":     "板號 (Board No)",
            "footprint": "足印 / 元件 (Footprint / RefDes)",
            "refdes":    "元件或群組 (Component / Subgroup)",
        }
        _xlabel = _xlabel_map.get(_grouping_mode)
        if _xlabel is None and _group_col:
            _xlabel = _group_col
        if _xlabel:
            self.ax.set_xlabel(_xlabel, fontsize=CHART_FONT_LABEL)

        if total_n > self._SPARSE_LABEL_THRESHOLD:
            self.ax.set_title(self.title_str + f" （共 {total_n} 組）")

        target_col = ctx.get("target_col", "Height")
        fill_color, edge_color = _color_for(target_col, 0)

        boxprops = dict(facecolor=fill_color, color=edge_color, linewidth=1.5)
        medianprops = dict(color=CHART_OOC, linewidth=2)
        flierprops = dict(marker="o", markerfacecolor=CHART_WARNING_MARK, markersize=5,
                          linestyle="none", markeredgecolor=CHART_FILL_EDGE)
        self.ax.boxplot(arrays, tick_labels=labels, patch_artist=True,
                        boxprops=boxprops, medianprops=medianprops, flierprops=flierprops)

        display_labels = build_sparse_tick_labels(
            labels,
            self._SPARSE_LABEL_THRESHOLD,
            self._SPARSE_STEP_SMALL,
            self._SPARSE_STEP_LARGE,
        )
        rot, fs = (60, 7) if n > 12 else (15, 9)
        self.ax.set_xticklabels(display_labels,
                                rotation=rot, ha="right", fontsize=fs)

        legend_handles = [
            mpatches.Patch(facecolor=fill_color, edgecolor=edge_color, label="箱體 (Q1–Q3)"),
            Line2D([0], [0], color=CHART_OOC, linewidth=2, label="中位數 (Median)"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=CHART_WARNING_MARK,
                   markeredgecolor=CHART_FILL_EDGE, markersize=6, linestyle="none", label="離群值 (Outliers)"),
        ]
        self.ax.legend(handles=legend_handles, loc="lower right", fontsize=CHART_FONT_LABEL)
        # layout handled by BaseChart
        self.canvas.draw()

    # ── Overview 3F: one box per feature (no grouping) ────────────────

    def _draw_overview_3f(self, engine_output: Dict[str, Any]) -> None:
        """
        Draw a simple side-by-side boxplot overview: one box per feature.
        Useful for comparing overall distribution of Height / Area / Volume
        without per-component grouping.  Supports normalisation (% of median).
        """
        import numpy as np

        features: list[str] = engine_output.get("_features", [])
        feature_data: dict[str, dict] = engine_output.get("_feature_data", {})
        normalized: bool = engine_output.get("_normalized", False)

        if not features or not feature_data:
            self._show_placeholder("無多特徵資料可顯示")
            return

        arrays: list[list] = []
        valid_features: list[str] = []
        feat_medians: dict[str, float] = {}

        for feat in features:
            fd = feature_data.get(feat, {})
            # box engine returns data.arrays (list of per-group arrays);
            # flatten all into one overall array
            raw_arrays = fd.get("data", {}).get("arrays", [])
            if raw_arrays:
                all_vals = [v for grp in raw_arrays for v in grp]
            else:
                # fallback: values key if present
                all_vals = list(fd.get("data", {}).get("values", []))
            if not all_vals:
                continue
            med = float(np.median(all_vals))
            feat_medians[feat] = med if med != 0 else 1.0
            arrays.append(all_vals)
            valid_features.append(feat)

        if not valid_features:
            self._show_placeholder("無有效資料")
            return

        if normalized:
            arrays = [
                list(np.array(a, dtype=float) / feat_medians[f] * 100)
                for a, f in zip(arrays, valid_features)
            ]

        n = len(valid_features)
        self.figure.clear()
        # Horizontal one-row layout for better side-by-side comparison.
        self.figure.set_size_inches(max(8, 3.8 * n), 4.8)
        axes = self.figure.subplots(1, n, sharex=False, sharey=False)
        axes = [axes] if n == 1 else list(axes)

        for i, (arr, feat, ax) in enumerate(zip(arrays, valid_features, axes)):
            fc, ec = _color_for(feat, i)
            r, g, b, _ = mcolors.to_rgba(fc)
            fill_rgba = (r, g, b, 0.72)
            self._draw_feature_boxplot(
                ax,
                [arr],
                [feat],
                fill_face=fill_rgba,
                edge_color=ec,
                flier_face=fc,
                width=0.5,
                marker_size=5,
            )
            usl = feature_data[feat].get("usl")
            lsl = feature_data[feat].get("lsl")
            if usl is not None and not normalized:
                draw_reference_line(ax, usl, f"USL {usl:.3g}", semantic="spec_limit")
            if lsl is not None and not normalized:
                draw_reference_line(ax, lsl, f"LSL {lsl:.3g}", semantic="spec_limit")
            ax.set_ylabel("標準化值" if normalized else "量測值")
            ax.set_title(f"{feat} 概覽", fontsize=CHART_FONT_LABEL)

        self.ax = axes[0]

        if normalized:
            self.figure.suptitle("三特徵整體分布概覽 — 標準化 (Three-Feature Overview, Normalized)", fontsize=CHART_FONT_TITLE)
        else:
            self.figure.suptitle("三特徵整體分布概覽 (Three-Feature Distribution Overview)", fontsize=CHART_FONT_TITLE)
        # layout handled by BaseChart
        self.canvas.draw()

    # ── Multi-feature (new: side-by-side per group) ───────────────────

    def _draw_multi_feature(self, engine_output: Dict[str, Any]) -> None:
        """
        Draw one cluster of boxes per RefDes group; each feature gets its own
        colour-coded box within the cluster.  When normalised=True every
        feature's values are divided by their own median × 100 so that
        different physical units (mm / mm² / mm³) can be compared visually.
        """
        import numpy as np

        features: list[str] = engine_output.get("_features", [])
        feature_data: dict[str, dict] = engine_output.get("_feature_data", {})
        normalized: bool = engine_output.get("_normalized", False)

        if not features or not feature_data:
            self._show_placeholder("無多特徵資料可顯示")
            return

        # Reference group labels from first valid feature
        first = features[0]
        labels: list[str] = feature_data[first].get("data", {}).get("labels", [])
        n_groups = len(labels)
        n_feats = len(features)

        if n_groups == 0:
            self._show_placeholder("無有效的群組資料 (Missing Subgroups)")
            return

        total_n = n_groups

        # Compute per-feature medians for normalisation
        feat_medians: dict[str, float] = {}
        if normalized:
            for feat in features:
                all_vals: list[float] = []
                for arr in feature_data[feat].get("data", {}).get("arrays", []):
                    all_vals.extend(arr)
                feat_medians[feat] = float(np.median(all_vals)) if all_vals else 1.0

        # Draw one subplot per feature, horizontally aligned for side-by-side comparison.
        self.figure.clear()
        fig_w = min(26, max(10, 3.4 * n_feats + 0.12 * n_groups))
        self.figure.set_size_inches(fig_w, 5.4)
        axes = self.figure.subplots(1, n_feats, sharex=False, sharey=False)
        axes = [axes] if n_feats == 1 else list(axes)

        for fi, feat in enumerate(features):
            ax = axes[fi]
            fill_hex, edge_hex = _color_for(feat, fi)
            # Semi-transparent fill
            r, g_c, b, _ = mcolors.to_rgba(fill_hex)
            fill_rgba = (r, g_c, b, 0.72)

            raw_arrays = list(feature_data[feat].get("data", {}).get("arrays", []))

            if not raw_arrays:
                continue

            arrays = raw_arrays
            if normalized and feat in feat_medians and feat_medians[feat] != 0:
                median = feat_medians[feat]
                arrays = [np.array(a, dtype=float) / median * 100 for a in raw_arrays]

            self._draw_feature_boxplot(
                ax,
                arrays,
                labels[:len(arrays)],
                fill_face=fill_rgba,
                edge_color=edge_hex,
                flier_face=fill_hex,
                width=0.6,
                marker_size=4,
            )
            rot, fs = (90, 7) if n_groups > 15 else (45, 9)
            display_labels = build_sparse_tick_labels(
                labels[:len(arrays)],
                self._SPARSE_LABEL_THRESHOLD,
                self._SPARSE_STEP_SMALL,
                self._SPARSE_STEP_LARGE,
            )
            ax.set_xticklabels(display_labels, rotation=rot, ha="right" if rot < 70 else "center", fontsize=fs)
            ax.set_ylabel("標準化值" if normalized else "量測值", fontsize=CHART_FONT_LABEL)
            ax.set_xlabel("元件或群組", fontsize=CHART_FONT_LABEL)
            ax.set_title(f"{feat} 箱型圖", fontsize=CHART_FONT_LABEL)
            ax.legend(
                handles=[
                    mpatches.Patch(facecolor=fill_rgba, edgecolor=edge_hex, label=feat),
                    Line2D([0], [0], color=CHART_OOC, linewidth=2, label="中位數 (Median)"),
                ],
                loc="lower right",
                fontsize=CHART_FONT_LEGEND,
            )

        # Labels / title
        if normalized:
            title = "元件群組比較 — 多特徵標準化 (Multi-Feature Normalized)"
        else:
            title = "元件群組比較 — 多特徵並列 (Multi-Feature Comparison)"
        if total_n > self._SPARSE_LABEL_THRESHOLD:
            title += f"（共 {total_n} 組）"
        self.figure.suptitle(title, fontsize=CHART_FONT_TITLE)

        self.ax = axes[0]

        # layout handled by BaseChart
        self.canvas.draw()
