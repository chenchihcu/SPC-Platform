import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.charts.anomaly_3f_chart import Anomaly3FChart
from app.charts.base_chart import BaseChart
from app.charts.bivariate_outlier_chart import BivariateOutlierChart
from app.charts.boxplot_chart import BoxplotChart
from app.charts.consistency_3f_chart import Consistency3FChart
from app.charts.control_chart import ControlChart
from app.charts.cusum_3f_chart import CUSUM3F
from app.charts.cusum_chart import CUSUMChart
from app.charts.density_chart import DensityChart
from app.charts.ewma_3f_chart import EWMA3F
from app.charts.ewma_chart import EWMAChart
from app.charts.heatmap_chart import HeatmapChart
from app.charts.histogram_chart import HistogramChart
from app.charts.imr_3f_chart import IMR3F
from app.charts.parallel_coord_chart import ParallelCoordChart
from app.charts.pareto_chart import ParetoChart
from app.charts.pass_fail_chart import PassFailChart
from app.charts.quadrant_chart import QuadrantChart
from app.charts.repeated_offender_chart import RepeatedOffenderChart
from app.charts.run_chart import RunChart
from app.charts.run_chart_3f_chart import RunChart3F
from app.charts.scatter_spec_chart import ScatterSpecChart
from app.charts.subgroup_chart import SubgroupChart


def test_base_chart_invalid_payload_draws_placeholder_canvas() -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    chart = BaseChart()
    calls: list[bool] = []
    original_draw = chart.canvas.draw

    def _counted_draw(*args, **kwargs):
        calls.append(True)
        return original_draw(*args, **kwargs)

    chart.canvas.draw = _counted_draw  # type: ignore[method-assign]
    try:
        assert chart.draw_chart({"metadata": {"is_valid": False, "error": "No data"}}) is False
        assert calls
        assert not chart.placeholder.isHidden()
    finally:
        chart.deleteLater()


def test_chart_draw_chart_return_type_contract_is_bool() -> None:
    classes = [
        BaseChart,
        Anomaly3FChart,
        BivariateOutlierChart,
        BoxplotChart,
        Consistency3FChart,
        ControlChart,
        CUSUM3F,
        CUSUMChart,
        DensityChart,
        EWMA3F,
        EWMAChart,
        HeatmapChart,
        HistogramChart,
        IMR3F,
        ParallelCoordChart,
        ParetoChart,
        PassFailChart,
        QuadrantChart,
        RepeatedOffenderChart,
        RunChart3F,
        RunChart,
        ScatterSpecChart,
        SubgroupChart,
    ]
    for chart_cls in classes:
        signature = inspect.signature(chart_cls.draw_chart)
        assert signature.return_annotation is bool, chart_cls.__name__
