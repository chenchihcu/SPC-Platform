"""Visual-contract regressions: shared reference lines, sample disclosure, empty states."""
import re
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QApplication

from app.charts.base_chart import BaseChart, format_sample_disclosure
from app.charts.cusum_3f_chart import CUSUM3F
from app.charts.heatmap_chart import HeatmapChart
from app.charts.ewma_3f_chart import EWMA3F
from app.charts.imr_3f_chart import IMR3F
from app.charts.multi_feature_panels import zscore_scale
from app.charts.run_chart import RunChart
from app.charts.run_chart_3f_chart import RunChart3F

_FEATS = ["Height", "Area", "Volume"]


def _ensure_app() -> None:
    if QApplication.instance() is None:
        QApplication([])


def _imr_fd(values: list[float]) -> dict:
    mr = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    m = float(np.mean(values))
    return {
        "metadata": {"is_valid": True},
        "data": {"values": values, "indices": list(range(len(values))), "mr_values": mr},
        "statistics": {"cl": m, "ucl": m + 3, "lcl": m - 3, "mr_bar": float(np.mean(mr))},
    }


def _wrap(fds: list[dict], normalized: bool = False) -> dict:
    return {
        "metadata": {"is_valid": True},
        "_multi_feature": True,
        "_features": _FEATS,
        "_normalized": normalized,
        "_feature_data": dict(zip(_FEATS, fds)),
    }


def _texts(ax) -> list[str]:
    return [t.get_text() for t in ax.texts]


def test_zscore_scale_matches_legacy_variants() -> None:
    values = [1.0, 2.0, 4.0, 7.0]
    assert zscore_scale(values) == (float(np.mean(values)), float(np.std(values, ddof=1)))
    assert zscore_scale([3.0]) == (3.0, 1.0)  # single point -> std fallback
    assert zscore_scale([]) == (0.0, 1.0)
    assert zscore_scale(values, mean=10.0, std=0.0) == (10.0, 1.0)
    assert zscore_scale(values, mean=10.0, std=float("nan")) == (10.0, 1.0)


def test_imr_3f_reference_lines_use_shared_edge_labels() -> None:
    _ensure_app()
    chart = IMR3F()
    assert chart.draw_chart(_wrap([_imr_fd([10.0, 11.0, 9.0, 10.5]) for _ in _FEATS])) is True
    ax_i, ax_mr = chart.figure.axes[0], chart.figure.axes[1]
    assert {"CL", "UCL", "LCL"} <= {t.split()[0] for t in _texts(ax_i) if " " in t}
    assert {"CL", "UCL"} <= {t.split()[0] for t in _texts(ax_mr) if " " in t}
    # Edge labels are anchored in axes-fraction X so a shared X axis cannot move them inward.
    edge = [a for a in ax_i.texts if a.get_text().startswith("UCL")][0]
    assert edge.xy[0] == 1.0


def test_ewma_and_cusum_3f_label_raw_values_on_zscore_axis() -> None:
    _ensure_app()
    ewma = EWMA3F()
    assert ewma.draw_chart(_wrap([_imr_fd([10.0, 11.0, 9.0, 10.5]) for _ in _FEATS], normalized=True))
    assert "UCL: 13.1" in _texts(ewma.figure.axes[0])  # raw 13.125, not the z-score

    cusum_fd = {
        "metadata": {"is_valid": True},
        "data": {"indices": [0, 1, 2], "values": [0.0, 1.0, 2.0], "values_cm": [0.5, 0.0, 1.0]},
        "statistics": {"h_sigma": 5.0},
    }
    cusum = CUSUM3F()
    assert cusum.draw_chart(_wrap([cusum_fd] * 3, normalized=True))
    ax = cusum.figure.axes[0]
    assert "+hσ(raw): 5" in _texts(ax) and "-hσ(raw): -5" in _texts(ax)
    legend_labels = [t.get_text() for t in ax.get_legend().get_texts()]
    assert legend_labels.count("+hσ(raw): 5") == 1
    assert not any(label.startswith("-hσ") for label in legend_labels)


def test_run_chart_sampling_uses_shared_disclosure_only() -> None:
    _ensure_app()
    stats = {"center_line": 1.0, "sampled_for_display": True, "displayed_n": 3, "n": 30, "downsample_step": 10}
    payload = {"metadata": {"is_valid": True}, "data": {"values": [1.0, 2.0, 0.5], "indices": [0, 1, 2]},
               "statistics": stats}
    assert "step=10" in format_sample_disclosure(payload)

    chart = RunChart()
    chart.draw_chart(payload)
    texts = _texts(chart.ax)
    assert not any("顯示抽樣" in t for t in texts)
    assert sum("shown=3/30" in t for t in texts) == 1

    chart3f = RunChart3F()
    chart3f.draw_chart(_wrap([payload, payload, payload]))
    for ax in chart3f.figure.axes:
        panel_texts = _texts(ax)
        assert not any(t.startswith("抽樣 ") for t in panel_texts)
        assert sum("shown=3/30" in t and "step=10" in t for t in panel_texts) == 1


def test_show_placeholder_routes_through_placeholder_class_for() -> None:
    _ensure_app()
    chart = BaseChart()
    chart._show_placeholder("無資料")
    assert chart.placeholder.property("class") == "chartPlaceholder-empty"
    chart._show_placeholder("x", metadata={"incompatible": True})
    assert chart.placeholder.property("class") == "chartPlaceholder-incompatible"

    chart3f = IMR3F()
    assert chart3f.draw_chart({"metadata": {"is_valid": False, "error": "載入失敗"}}) is False
    assert chart3f.placeholder.property("class") == "chartPlaceholder-error"
    assert chart3f.draw_chart({"metadata": {"is_valid": True}, "_features": []}) is False
    assert chart3f.placeholder.property("class") == "chartPlaceholder-empty"


def test_chart_placeholder_literals_follow_wording_convention() -> None:
    chart_dir = Path(__file__).resolve().parents[1] / "app" / "charts"
    literal = re.compile(r'_show_placeholder\(\s*"([^"]*)"')
    offenders: list[str] = []
    for path in chart_dir.glob("*.py"):
        for text in literal.findall(path.read_text(encoding="utf-8")):
            if text.endswith("。") or re.search(r"\([A-Za-z][A-Za-z ]+\)$", text):
                offenders.append(f"{path.name}: {text}")
    assert offenders == []


def test_sample_disclosure_survives_repeated_renders_after_axis_clear() -> None:
    _ensure_app()
    chart = HeatmapChart()
    payload = {
        "metadata": {"is_valid": True, "mode": "value"},
        "data": {"x": [0.0, 1.0, 2.0], "y": [0.0, 1.0, 2.0], "values": [1.0, 2.0, 3.0]},
        "statistics": {"sampled_for_display": True, "displayed_n": 3200, "n": 120000, "aggregation_bins": 80},
    }
    for _ in range(3):  # each draw_chart() runs BaseChart.clear() -> ax.clear()
        chart.draw_chart(payload)
        texts = _texts(chart.ax)
        assert sum("shown=3200/120000" in t and "grid=80x80" in t for t in texts) == 1
