"""
Headless chart rendering for report export: given chart_id and payload slice,
creates the chart widget, draws, and returns PNG bytes. Used by ReportService.
"""
import logging
from io import BytesIO
from typing import Dict, Any, Optional, List
import numpy as np

logger = logging.getLogger(__name__)

from app.analytics.chart_registry import resolve_chart_payload

_QT_APP_REF: Any | None = None


def _ensure_qapplication() -> None:
    """Ensure report chart rendering never constructs widgets before QApplication."""
    global _QT_APP_REF
    from app.bootstrap.runtime_env import ensure_home_env
    from app.bootstrap.font_runtime import register_qt_bundled_fonts, preferred_qt_font_family
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    ensure_home_env()
    app_instance = QApplication.instance()
    if not isinstance(app_instance, QApplication):
        app = QApplication([])
        _QT_APP_REF = app
    else:
        app = app_instance
    register_qt_bundled_fonts()
    app.setFont(QFont(preferred_qt_font_family()))


def _png_has_visual_content(png_bytes: bytes, *, min_non_white_ratio: float = 0.01) -> bool:
    """Detect near-blank exported PNGs (mostly white background with no real plot ink)."""
    if not png_bytes:
        return False
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        # If Pillow is unavailable, keep previous behavior and trust renderer output.
        return True
    try:
        with Image.open(BytesIO(png_bytes)) as image:
            rgb = image.convert("RGB")
            w, h = rgb.size
            if w <= 0 or h <= 0:
                return False
            total = w * h
            pixels = np.asarray(rgb, dtype=np.uint8)
            # Count pixels where any RGB channel is not near-white.
            non_white = int(np.count_nonzero(np.any(pixels <= 245, axis=2)))
            return (non_white / total) >= min_non_white_ratio
    except (OSError, TypeError, ValueError, RuntimeError):
        # Corrupted/unreadable PNG should not be considered valid visual output.
        return False


def _canvas_has_drawn_content(widget: Any) -> bool:
    """Best-effort check: return False when widget is in placeholder/hidden-canvas state."""
    try:
        canvas = getattr(widget, "canvas", None)
        if canvas is not None and hasattr(canvas, "isHidden"):
            return not bool(canvas.isHidden())
    except (AttributeError, RuntimeError, TypeError):
        logger.debug("canvas visibility check failed", exc_info=True)

    try:
        chart_view = getattr(widget, "chart_view", None)
        cv_canvas = getattr(chart_view, "canvas", None) if chart_view is not None else None
        if cv_canvas is not None and hasattr(cv_canvas, "isHidden"):
            return not bool(cv_canvas.isHidden())
    except (AttributeError, RuntimeError, TypeError):
        logger.debug("chart_view canvas visibility check failed", exc_info=True)

    # Unknown widget model: preserve previous behavior.
    return True


def _render_imr(slice_data: dict) -> Optional[bytes]:
    _ensure_qapplication()
    from app.charts.control_chart import ControlChart
    w = ControlChart(parent=None)
    w.draw_chart(slice_data or {})
    if not (slice_data.get("metadata") or {}).get("is_valid", False):
        return None
    if not _canvas_has_drawn_content(w):
        return None
    buf = BytesIO()
    w.figure.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    png_bytes = buf.getvalue()
    if not _png_has_visual_content(png_bytes):
        return None
    return png_bytes


def _render_tab_widget(tab_class, slice_data: dict, *, self_figure: bool = False) -> Optional[bytes]:
    """Generic renderer for tab-based chart widgets.

    Args:
        tab_class: The tab widget class to instantiate.
        slice_data: Engine output dict for this chart.
        self_figure: True when the tab exposes `self.figure` directly (e.g. NormalityTab).
                     False (default) when the figure is accessed via `self.chart_view.figure`.
    """
    _ensure_qapplication()
    w = tab_class(parent=None)
    w.update_data(slice_data or {})
    if not (slice_data.get("metadata") or {}).get("is_valid", False):
        return None
    if not _canvas_has_drawn_content(w):
        return None
    fig = w.figure if self_figure else w.chart_view.figure
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    png_bytes = buf.getvalue()
    if not _png_has_visual_content(png_bytes):
        return None
    return png_bytes


def _render_histogram_cap(slice_data: dict) -> Optional[bytes]:
    from app.ui.tabs.distribution_capability_tab import DistributionCapabilityTab
    return _render_tab_widget(DistributionCapabilityTab, slice_data)


def _render_boxplot(slice_data: dict) -> Optional[bytes]:
    from app.ui.tabs.comparison_tab import ComparisonTab
    return _render_tab_widget(ComparisonTab, slice_data)


def _render_normality(slice_data: dict) -> Optional[bytes]:
    from app.ui.tabs.normality_tab import NormalityTab
    return _render_tab_widget(NormalityTab, slice_data, self_figure=True)


def _render_spatial(slice_data: dict) -> Optional[bytes]:
    from app.ui.tabs.spatial_tab import SpatialTab
    return _render_tab_widget(SpatialTab, slice_data)


def _render_pareto(slice_data: dict) -> Optional[bytes]:
    from app.ui.tabs.pareto_tab import ParetoTab
    return _render_tab_widget(ParetoTab, slice_data)


def _render_single_chart(chart_class, slice_data: dict) -> Optional[bytes]:
    _ensure_qapplication()
    w = chart_class(parent=None)
    w.draw_chart(slice_data or {})
    if not (slice_data.get("metadata") or {}).get("is_valid", False):
        return None
    if not _canvas_has_drawn_content(w):
        return None
    buf = BytesIO()
    w.figure.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    png_bytes = buf.getvalue()
    if not _png_has_visual_content(png_bytes):
        return None
    return png_bytes


_RENDERERS = {
    "imr": _render_imr,
    "histogram_spec": _render_histogram_cap,
    "capability": _render_histogram_cap,
    "boxplot": _render_boxplot,
    "normality": _render_normality,
    "spatial_heatmap": _render_spatial,
    "pareto": _render_pareto,
}


def _register_single(chart_id: str, chart_class: Any) -> None:
    def _renderer(slice_data: dict) -> Optional[bytes]:
        return _render_single_chart(chart_class, slice_data)

    _RENDERERS[chart_id] = _renderer


def _init_renderers():
    from app.charts.scatter_spec_chart import ScatterSpecChart
    from app.charts.xbar_r_chart import XbarRChart
    from app.charts.quadrant_chart import QuadrantChart
    from app.charts.bivariate_outlier_chart import BivariateOutlierChart
    from app.charts.correlation_matrix_chart import CorrelationMatrixChart
    from app.charts.correlation_heatmap_chart import CorrelationHeatmapChart
    from app.charts.anova_parttype_chart import AnovaPartTypeChart
    from app.charts.summary_card_chart import SummaryCardChart
    from app.charts.pattern_recognition_chart import PatternRecognitionChart
    from app.charts.anomaly_3f_chart import Anomaly3FChart
    from app.charts.consistency_3f_chart import Consistency3FChart
    from app.charts.ewma_chart import EWMAChart
    from app.charts.cusum_chart import CUSUMChart
    from app.charts.run_chart import RunChart
    from app.charts.subgroup_chart import SubgroupChart
    from app.charts.repeated_offender_chart import RepeatedOffenderChart
    from app.charts.density_chart import DensityChart
    from app.charts.parallel_coord_chart import ParallelCoordChart
    from app.charts.pass_fail_chart import PassFailChart
    from app.charts.imr_3f_chart import IMR3F
    from app.charts.run_chart_3f_chart import RunChart3F
    from app.charts.ewma_3f_chart import EWMA3F
    from app.charts.cusum_3f_chart import CUSUM3F
    from app.charts.boxplot_chart import BoxplotChart
    _register_single("xbar_r", XbarRChart)
    _register_single("scatter_spec", ScatterSpecChart)
    _register_single("correlation_matrix", CorrelationMatrixChart)
    _register_single("correlation_heatmap", CorrelationHeatmapChart)
    _register_single("anova_parttype", AnovaPartTypeChart)
    _register_single("quadrant", QuadrantChart)
    _register_single("bivariate_outlier", BivariateOutlierChart)
    _register_single("pattern_recognition", PatternRecognitionChart)
    _register_single("ooc_analysis", SummaryCardChart)
    _register_single("shift_detection", SummaryCardChart)
    _register_single("drift_detection", SummaryCardChart)
    _register_single("outlier_analysis", SummaryCardChart)
    _register_single("anomaly_3f", Anomaly3FChart)
    _register_single("consistency_3f", Consistency3FChart)
    _register_single("ewma", EWMAChart)
    _register_single("cusum", CUSUMChart)
    _register_single("run_chart", RunChart)
    _register_single("subgroup", SubgroupChart)
    _register_single("repeated_offender", RepeatedOffenderChart)
    _register_single("density", DensityChart)
    _register_single("parallel_coord", ParallelCoordChart)
    _register_single("pass_fail_matrix", PassFailChart)
    _register_single("imr_3f", IMR3F)
    _register_single("run_chart_3f", RunChart3F)
    _register_single("ewma_3f", EWMA3F)
    _register_single("cusum_3f", CUSUM3F)
    _register_single("boxplot_3f", BoxplotChart)


_init_renderers()


def render_chart_to_png_bytes(
    chart_id: str,
    payload: Dict[str, Any],
    *,
    features: Optional[List[str]] = None,
    normalized: bool = False,
    context: str = "report",
) -> Optional[bytes]:
    """
    Render the given chart_id with data from payload to PNG bytes.
    Returns None if chart_id unknown or slice invalid/empty.
    """
    slice_data = resolve_chart_payload(
        payload,
        chart_id,
        features=features,
        normalized=normalized,
        context=context,
    )
    if not slice_data:
        return None
    renderer = _RENDERERS.get(chart_id)
    if not renderer:
        return None
    try:
        return renderer(slice_data)
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError, OSError):
        logger.exception("圖表渲染失敗: chart_id=%s", chart_id)
        raise  # Surface renderer failures to caller (e.g. report export) instead of returning None
