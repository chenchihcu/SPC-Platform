from app.bootstrap.runtime_env import ensure_home_env

ensure_home_env()

import matplotlib
matplotlib.use('QtAgg')
from app.charts.mpl_font_config import setup_mpl_cjk_font
setup_mpl_cjk_font()
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from typing import Dict, Any, Iterable, Mapping, Sequence

from app.ui.theme.tokens import (
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    CHART_GRID,
    CHART_GRID_MINOR,
    CHART_FIGURE_BG,
    CHART_AXES_BG,
    CHART_SERIES,
    CHART_SERIES_SECONDARY,
    CHART_CENTERLINE,
    CHART_CONTROL_LIMITS,
    CHART_SPEC_LIMITS,
    CHART_OOC,
    CHART_OOC_MARKER_SIZE,
    CHART_WARNING_MARK,
    CHART_ANNOTATION,
    CHART_LINE_STYLE_SECONDARY,
    ERROR_NO_DATA,
    CHART_PALETTE_VOLUME_FILL, CHART_PALETTE_VOLUME_EDGE,
    CHART_PALETTE_AREA_FILL, CHART_PALETTE_AREA_EDGE,
    CHART_PALETTE_HEIGHT_FILL, CHART_PALETTE_HEIGHT_EDGE,
    CHART_PALETTE_OFFSET_X_FILL, CHART_PALETTE_OFFSET_X_EDGE,
    CHART_PALETTE_OFFSET_Y_FILL, CHART_PALETTE_OFFSET_Y_EDGE,
    CHART_PALETTE_OFFSET_R_FILL, CHART_PALETTE_OFFSET_R_EDGE,
    CHART_PALETTE_SOLDER_FILL, CHART_PALETTE_SOLDER_EDGE,
    CHART_FONT_LABEL,
    CHART_FONT_LEGEND,
    CHART_FONT_ANNOTATION,
    CHART_FONT_MICRO,
)
from app.utils.constants import MSG_NOT_SYSTEM_ERROR


def _apply_mpl_app_style(fig, ax):
    """Apply unified light Slate chart style for figure and axes."""
    fig.patch.set_facecolor(CHART_FIGURE_BG)
    fig.patch.set_edgecolor("none")           # 移除 figure 外框，圖邊更乾淨
    ax.set_facecolor(CHART_AXES_BG)

    # Tick 樣式：文字色稍淡，避免搶奪資料焦點
    ax.tick_params(
        colors=TEXT_SECONDARY,
        grid_color=CHART_GRID,
        labelsize=CHART_FONT_LABEL,
        length=3,          # 縮短刻度線
        width=0.7,         # 刻度線更細
        pad=4,             # 刻度文字與軸的間距
    )
    ax.xaxis.label.set_color(TEXT_SECONDARY)   # 軸標籤用次要色，不與資料搶顯
    ax.yaxis.label.set_color(TEXT_SECONDARY)
    ax.title.set_color(TEXT_PRIMARY)

    # 網格：僅主格，線條更輕薄
    ax.grid(True, which="major", color=CHART_GRID, linestyle="-", linewidth=0.6, alpha=0.65)
    ax.minorticks_on()
    ax.grid(True, which="minor", color=CHART_GRID_MINOR, linestyle="-", linewidth=0.4, alpha=0.35)
    ax.set_axisbelow(True)

    # Spine（軸框）：只保留左下兩條，移除上右，Linear 風格更乾淨
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(CHART_GRID)
    ax.spines["left"].set_linewidth(0.7)
    ax.spines["bottom"].set_color(CHART_GRID)
    ax.spines["bottom"].set_linewidth(0.7)


_apply_mpl_dark_style = _apply_mpl_app_style


def resolve_target_col(engine_output: Dict[str, Any]) -> str:
    """Resolve display target column from metadata first, then analysis_context."""
    output = engine_output or {}
    for key in ("metadata", "analysis_context"):
        section = output.get(key, {}) or {}
        if isinstance(section, dict):
            target = section.get("target_col")
            if target:
                return str(target)
    return ""


_FEATURE_PALETTE = {
    "Volume":     (CHART_PALETTE_VOLUME_FILL,   CHART_PALETTE_VOLUME_EDGE),
    "Area":       (CHART_PALETTE_AREA_FILL,     CHART_PALETTE_AREA_EDGE),
    "Height":     (CHART_PALETTE_HEIGHT_FILL,   CHART_PALETTE_HEIGHT_EDGE),
    "Offset_X":   (CHART_PALETTE_OFFSET_X_FILL, CHART_PALETTE_OFFSET_X_EDGE),
    "Offset_Y":   (CHART_PALETTE_OFFSET_Y_FILL, CHART_PALETTE_OFFSET_Y_EDGE),
    "Offset_R":   (CHART_PALETTE_OFFSET_R_FILL, CHART_PALETTE_OFFSET_R_EDGE),
    "Solder_Vol": (CHART_PALETTE_SOLDER_FILL,   CHART_PALETTE_SOLDER_EDGE),
}

_GENERIC_PALETTE = [
    (CHART_PALETTE_VOLUME_FILL,   CHART_PALETTE_VOLUME_EDGE),
    (CHART_PALETTE_AREA_FILL,     CHART_PALETTE_AREA_EDGE),
    (CHART_PALETTE_HEIGHT_FILL,   CHART_PALETTE_HEIGHT_EDGE),
    (CHART_PALETTE_OFFSET_X_FILL, CHART_PALETTE_OFFSET_X_EDGE),
]

def get_feature_color(feature_name: str, fallback_idx: int = 0) -> tuple[str, str]:
    """Return consistent semantic color tuple (fill, edge) for a measurement feature (Pass 24)."""
    if feature_name in _FEATURE_PALETTE:
        return _FEATURE_PALETTE[feature_name]
    return _GENERIC_PALETTE[fallback_idx % len(_GENERIC_PALETTE)]


def build_sparse_tick_labels(labels: list[str], threshold: int = 30, step_small: int = 5, step_large: int = 10) -> list[str]:
    """Return sparse labels while guaranteeing first/last visibility."""
    n = len(labels)
    if n <= threshold:
        return labels
    step = step_small if n <= 50 else step_large
    display = [labels[i] if i % step == 0 else "" for i in range(n)]
    if n > 0:
        display[0] = labels[0]
        display[-1] = labels[-1]
    return display


def sparse_tick_positions_labels(labels: list[str], max_ticks: int = 20) -> tuple[list[int], list[str]]:
    """Return sampled tick positions/labels while guaranteeing first/last visibility."""
    n = len(labels)
    if n == 0:
        return [], []
    if n <= max_ticks:
        pos = list(range(n))
        return pos, labels
    step = max(1, n // max_ticks)
    pos = list(range(0, n, step))
    if pos[-1] != n - 1:
        pos.append(n - 1)
    tick_labels = [labels[i] for i in pos]
    tick_labels[0] = labels[0]
    tick_labels[-1] = labels[-1]
    return pos, tick_labels


def chart_line_style(primary: bool = True) -> dict[str, float | str]:
    """Return shared line-style defaults for primary vs reference chart lines."""
    if primary:
        return {"linestyle": "-", "linewidth": 1.5}
    return {"linestyle": CHART_LINE_STYLE_SECONDARY, "linewidth": 1.0}


_REFERENCE_SEMANTICS: dict[str, dict[str, float | str]] = {
    "series": {"color": CHART_SERIES, "linestyle": "-", "linewidth": 1.6},
    "series_secondary": {"color": CHART_SERIES_SECONDARY, "linestyle": "-", "linewidth": 1.3},
    "centerline": {"color": CHART_CENTERLINE, "linestyle": "-", "linewidth": 1.4},
    "control_limit": {"color": CHART_CONTROL_LIMITS, "linestyle": CHART_LINE_STYLE_SECONDARY, "linewidth": 1.3},
    "spec_limit": {"color": CHART_SPEC_LIMITS, "linestyle": ":", "linewidth": 1.5},
    "target": {"color": CHART_CENTERLINE, "linestyle": "-.", "linewidth": 1.2},
    "mean": {"color": CHART_CENTERLINE, "linestyle": "--", "linewidth": 1.2},
    "median": {"color": CHART_WARNING_MARK, "linestyle": ":", "linewidth": 1.2},
    "neutral": {"color": CHART_ANNOTATION, "linestyle": "-", "linewidth": 0.8},
}


def semantic_line_style(kind: str, **overrides: float | str) -> dict[str, float | str]:
    """Return the shared visual style for a statistical line semantic."""
    style = dict(_REFERENCE_SEMANTICS.get(kind, _REFERENCE_SEMANTICS["neutral"]))
    style.update(overrides)
    return style


def draw_reference_line(
    ax,
    value: float,
    label: str,
    *,
    orientation: str = "h",
    semantic: str = "neutral",
    annotate_edge: bool = True,
) -> Any:
    """Draw a horizontal or vertical statistical reference line with direct labeling."""
    style = semantic_line_style(semantic)
    if orientation == "v":
        artist = ax.axvline(value, label=label, **style)
    else:
        artist = ax.axhline(value, label=label, **style)
    if annotate_edge:
        annotate_limit_edge(ax, value, label, orientation=orientation, color=str(style["color"]))
    return artist


def annotate_limit_edge(
    ax,
    value: float,
    label: str,
    *,
    orientation: str = "h",
    color: str = CHART_ANNOTATION,
) -> None:
    """Place a compact label at the visible edge of a limit/reference line."""
    if orientation == "v":
        ax.annotate(
            label,
            xy=(value, 0.98),
            xycoords=("data", "axes fraction"),
            xytext=(0, -4),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=CHART_FONT_MICRO,
            color=color,
        )
        return
    x0, x1 = ax.get_xlim()
    x_edge = x1 if x1 >= x0 else x0
    ax.annotate(
        label,
        xy=(x_edge, value),
        xytext=(6, 0),
        textcoords="offset points",
        ha="left",
        va="center",
        fontsize=CHART_FONT_MICRO,
        color=color,
    )


def annotate_latest_point(
    ax,
    x_values: Sequence[Any],
    y_values: Sequence[Any],
    *,
    label: str = "Latest",
    color: str = CHART_SERIES,
) -> None:
    """Label the last plottable point in a measured series."""
    if not x_values or not y_values:
        return
    count = min(len(x_values), len(y_values))
    for idx in range(count - 1, -1, -1):
        x_val = x_values[idx]
        y_val = y_values[idx]
        try:
            y_num = float(y_val)
        except (TypeError, ValueError):
            continue
        if not y_num == y_num:
            continue
        ax.annotate(
            label,
            xy=(x_val, y_val),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=CHART_FONT_ANNOTATION,
            color=color,
            ha="left",
            va="bottom",
            bbox={"boxstyle": "round,pad=0.3", "fc": CHART_AXES_BG, "ec": color, "alpha": 0.85},
        )
        return


def scatter_state_points(
    ax,
    x_values: Sequence[Any],
    y_values: Sequence[Any],
    *,
    state: str = "ooc",
    label: str | None = None,
    size: float | None = None,
) -> Any:
    """Render special state points while keeping OOC and OOS visually distinct."""
    color = CHART_OOC if state == "ooc" else CHART_SPEC_LIMITS
    marker = "o" if state == "ooc" else "D"
    point_size = size if size is not None else (CHART_OOC_MARKER_SIZE ** 2)
    return ax.scatter(
        x_values,
        y_values,
        color=color,
        marker=marker,
        s=point_size,
        zorder=6,
        label=label or state.upper(),
        edgecolors=CHART_AXES_BG,
        linewidths=0.8,
    )


def _first_present(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


def format_sample_disclosure(engine_output: Mapping[str, Any]) -> str:
    """Build a compact traceability line for sample, aggregation, and normalization basis."""
    stats = engine_output.get("statistics", {})
    meta = engine_output.get("metadata", {})
    data = engine_output.get("data", {})
    if not isinstance(stats, Mapping):
        stats = {}
    if not isinstance(meta, Mapping):
        meta = {}
    if not isinstance(data, Mapping):
        data = {}

    parts: list[str] = []
    n = _first_present(stats, ("n", "total_n", "sample_count")) or _first_present(meta, ("n", "total_n", "sample_count"))
    if n is None:
        n = _first_present(data, ("n", "total_n", "sample_count"))
    if n is not None:
        parts.append(f"N={n}")

    displayed = _first_present(stats, ("displayed_n", "shown_n"))
    total = _first_present(stats, ("total_n", "n", "n_refdes_with_violations"))
    if displayed is not None and total is not None and str(displayed) != str(total):
        parts.append(f"shown={displayed}/{total}")

    tested = _first_present(stats, ("tested_n",))
    tested_total = _first_present(stats, ("total_n", "n"))
    if tested is not None and tested_total is not None:
        parts.append(f"tested={tested}/{tested_total}")

    aggregation_bins = _first_present(stats, ("aggregation_bins",))
    if aggregation_bins is not None:
        parts.append(f"grid={aggregation_bins}x{aggregation_bins}")

    top_n = _first_present(stats, ("top_n",))
    if top_n is not None:
        parts.append(f"top_n={top_n}")

    if bool(engine_output.get("_normalized")) or bool(stats.get("normalized")):
        parts.append("normalized")

    basis = _first_present(stats, ("normalization_basis", "sampling_method"))
    if basis is not None:
        parts.append(str(basis))

    return " | ".join(parts)


def add_sample_disclosure(ax, engine_output: Mapping[str, Any]) -> str:
    """Add a bottom-left chart disclosure once and return the rendered text."""
    text = format_sample_disclosure(engine_output)
    if not text or getattr(ax, "_spc_sample_disclosure", False):
        return text
    ax.text(
        0.01,
        0.01,
        text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=CHART_FONT_MICRO,
        color=CHART_ANNOTATION,
        bbox={"boxstyle": "round,pad=0.35", "fc": CHART_AXES_BG, "ec": CHART_GRID, "alpha": 0.86},
    )
    setattr(ax, "_spc_sample_disclosure", True)
    return text


def apply_legend_style(ax) -> None:
    """Apply a consistent compact legend style and move it above the axes to prevent overlap."""
    legend = ax.get_legend()
    if legend is None:
        return

    legend.set_bbox_to_anchor((1.0, 1.02), transform=ax.transAxes)
    legend.set_title(None)

    # 現代簡約：圖例背景極淡，邊框更細緻
    frame = legend.get_frame()
    frame.set_facecolor(CHART_AXES_BG)
    frame.set_edgecolor(CHART_GRID)
    frame.set_linewidth(0.6)
    frame.set_alpha(0.95)

    for text in legend.get_texts():
        text.set_fontsize(CHART_FONT_LEGEND)
        text.set_color(TEXT_SECONDARY)   # 圖例文字用次要色，降低視覺雜訊


class BaseChart(QWidget):
    """
    Base widget for all Matplotlib charts.
    Handles canvas creation, layout embedding, and rendering context.
    Uses app theme tokens for figure/axes to match UI and report output.
    """
    def __init__(self, parent=None, title: str = "", xlabel: str = "", ylabel: str = "", figsize=(6, 4)):
        super().__init__(parent)
        # Use 'constrained' layout engine by default for better handling of legends and subplots.
        self.figure = Figure(figsize=figsize, dpi=100, layout='constrained')
        self.figure.patch.set_facecolor(CHART_FIGURE_BG)
        self.canvas = FigureCanvas(self.figure)
        self._last_engine_output: Dict[str, Any] = {}
        self._visual_contract_finalizing = False
        original_draw = self.canvas.draw

        def _draw_with_visual_contract(*args: Any, **kwargs: Any) -> Any:
            self._finalize_visual_contract_before_draw()
            return original_draw(*args, **kwargs)

        setattr(self.canvas, "draw", _draw_with_visual_contract)

        # Tighter default pads for dense industrial UI (Pass 25 layout audit).
        layout_engine: Any = (
            self.figure.get_layout_engine()
            if hasattr(self.figure, "get_layout_engine")
            else None
        )
        if layout_engine is not None:
            layout_engine.set(
                w_pad=0.05, h_pad=0.05, wspace=0.08, hspace=0.08
            )

        self.ax = self.figure.add_subplot(111)
        _apply_mpl_app_style(self.figure, self.ax)
        self.title_str = title
        self.xlabel_str = xlabel
        self.ylabel_str = ylabel

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.placeholder = QLabel(ERROR_NO_DATA)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setProperty("class", "chartPlaceholder")

        self._layout.addWidget(self.placeholder)
        self._layout.addWidget(self.canvas, 1)
        self.canvas.hide()

    def clear(self) -> None:
        """Clears the axes and restores placeholder if needed."""
        self.ax.clear()
        _apply_mpl_app_style(self.figure, self.ax)
        self.ax.set_title(self.title_str)
        self.ax.set_xlabel(self.xlabel_str)
        self.ax.set_ylabel(self.ylabel_str)

    def draw_chart(self, engine_output: Dict[str, Any]) -> bool:
        """
        Base method to be overridden.
        Takes the standardized JSON-like output from analytics engines.
        """
        self._set_visual_contract_payload(engine_output)
        self.clear()

        metadata = engine_output.get("metadata", {})
        if not metadata.get("is_valid", False):
            error_msg = metadata.get("error", "未知錯誤 / Unknown Error")
            if metadata.get("incompatible"):
                error_msg = f"{error_msg} {MSG_NOT_SYSTEM_ERROR}"
            placeholder_class = self._placeholder_class_for(metadata, error_msg)
            self._show_placeholder(error_msg, placeholder_class)
            return False

        self._show_canvas()
        return True

    def _set_visual_contract_payload(self, engine_output: Dict[str, Any]) -> None:
        """Store the payload used by the draw wrapper for report/screen parity."""
        self._last_engine_output = engine_output or {}

    def _finalize_visual_contract_before_draw(self) -> None:
        """Apply shared presentation finishing to every BaseChart render path."""
        if self._visual_contract_finalizing:
            return
        self._visual_contract_finalizing = True
        try:
            axes = list(getattr(self.figure, "axes", []))
            for axis in axes:
                apply_legend_style(axis)
            if axes and self._last_engine_output:
                add_sample_disclosure(axes[0], self._last_engine_output)
        finally:
            self._visual_contract_finalizing = False
        
    def _placeholder_class_for(self, metadata: dict, error_msg: str) -> str:
        """Return chartPlaceholder-incompatible | chartPlaceholder-error | chartPlaceholder-empty.

        Semantics: incompatible = feature count / condition mismatch; error = compute or load failure;
        empty = no data or not yet computed. App QSS applies distinct styles per class.
        """
        if metadata.get("incompatible"):
            return "chartPlaceholder-incompatible"
        if metadata.get("error") and any(
            kw in (error_msg or "") for kw in ("失敗", "錯誤", "Error", "error")
        ):
            return "chartPlaceholder-error"
        return "chartPlaceholder-empty"

    def _show_placeholder(self, text: str, placeholder_class: str = "chartPlaceholder") -> None:
        self.canvas.hide()
        self.placeholder.setProperty("class", placeholder_class)
        self.placeholder.setText(text)
        self.placeholder.show()
        self.placeholder.style().unpolish(self.placeholder)
        self.placeholder.style().polish(self.placeholder)
        self.canvas.draw()
        
    def _show_canvas(self) -> None:
        self.placeholder.hide()
        self.canvas.show()
