"""Chart interpretation texts and renderers must match what engines actually compute."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
from PySide6.QtWidgets import QApplication

from app.analytics.chart_registry import get_chart_description_sections
from app.analytics.density_engine import DensityEngine
from app.analytics.quadrant_engine import QuadrantEngine
from app.charts.density_chart import DensityChart
from app.charts.quadrant_chart import QuadrantChart
from app.services.analysis_orchestrator import AnalysisOrchestrator


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def _text(chart_id: str) -> str:
    return " ".join(get_chart_description_sections(chart_id).values())


def test_descriptions_state_actual_engine_semantics() -> None:
    assert "1.128" in _text("imr") and "1.128" in _text("imr_3f")
    assert "μ0 + kσ" in _text("cusum") and "μ0 + kσ" in _text("cusum_3f")
    assert "USL 與 LSL" in _text("cusum")
    assert "PartType" in _text("subgroup") and "BoardNo" not in get_chart_description_sections("subgroup")["data_source_text"]
    assert "管制界線" not in get_chart_description_sections("repeated_offender")["definition_text"]
    assert "D'Agostino" in _text("normality")
    assert "PartType" in _text("pareto") and "UCL/LCL" in _text("pareto")
    assert "λ = 0.2" in _text("ewma")
    assert "0.0027" in _text("bivariate_outlier")
    assert "中位數" in _text("quadrant")
    assert "抽樣" in _text("parallel_coord") and "不抽樣" in _text("parallel_coord")
    assert "100% Pass" in _text("pass_fail_matrix")
    for cid in ("imr_3f", "run_chart_3f", "ewma_3f", "cusum_3f", "boxplot_3f"):
        assert "Volume / Area / Height" in get_chart_description_sections(cid)["definition_text"], cid


def test_density_three_feature_draws_one_kde_per_feature() -> None:
    _app()
    rng = np.random.default_rng(0)
    feats = ["Volume", "Area", "Height"]
    feature_data = {f: DensityEngine.compute_univariate_density(pd.Series(rng.normal(100, 5, 200)), f) for f in feats}
    payload = dict(feature_data["Volume"])
    payload.update({"_multi_feature": True, "_features": feats, "_feature_data": feature_data})
    chart = DensityChart()
    assert chart.draw_chart(payload) is True
    assert len(chart.figure.axes) == 3
    assert all(ax.lines for ax in chart.figure.axes)
    # Returning to single-feature mode must drop the extra subplots.
    assert chart.draw_chart(feature_data["Area"]) is True
    assert len(chart.figure.axes) == 1


def test_quadrant_points_coloured_per_quadrant() -> None:
    _app()
    df = pd.DataFrame({"Volume": [90.0, 110.0, 90.0, 110.0, 105.0], "Area": [90.0, 90.0, 110.0, 110.0, 95.0]})
    payload = QuadrantEngine.compute_quadrant(df, "Volume", "Area", spec_x={"target": 100}, spec_y={"target": 100})
    chart = QuadrantChart()
    assert chart.draw_chart(payload) is True
    assert len(chart.ax.collections) == 4
    labels = [t.get_text() for t in chart.ax.get_legend().get_texts()]
    assert any(label.startswith("Q4") and "(2)" in label for label in labels)


def test_one_sided_spec_keeps_missing_limit_none() -> None:
    limits, err = AnalysisOrchestrator._resolve_primary_limits({"volume": {"usl": "150"}}, "Volume")
    assert err is None
    assert limits == (150.0, None, None)
    limits, err = AnalysisOrchestrator._resolve_primary_limits({"volume": {"usl": "120", "lsl": "80"}}, "Volume")
    assert limits == (120.0, 80.0, 100.0)
    limits, _ = AnalysisOrchestrator._resolve_primary_limits({"volume": {"usl": "10", "lsl": "-10", "target": "0"}}, "Volume")
    assert limits == (10.0, -10.0, 0.0)
