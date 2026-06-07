"""Matplotlib PNG baseline regression (fixed Agg + dpi); see tests/baseline_images/README.md."""

from __future__ import annotations

import os
import platform
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest
from matplotlib.testing.compare import compare_images

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.charts.density_chart import DensityChart


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _density_payload() -> dict:
    return {
        "metadata": {"is_valid": True},
        "data": {
            "x": [98.0, 100.0, 101.0, 103.0, 105.0],
            "y": [108.0, 110.0, 111.0, 109.0, 107.0],
            "col_x": "Area",
            "col_y": "Height",
        },
        "statistics": {"gridsize": 12},
    }


def test_density_chart_matches_baseline_png(qapp, tmp_path: Path) -> None:
    # Isolate baseline PNG settings: do not mutate global rcParams (would force
    # DejaVu for all later tests and flood the suite with CJK glyph warnings).
    # Baseline raster is pinned to DejaVu; chart labels include CJK — expect
    # missing-glyph noise only inside this block.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Glyph .* missing from font\(s\) DejaVu Sans",
            category=UserWarning,
        )
        with plt.rc_context(
            rc={
                "figure.dpi": 100,
                "savefig.dpi": 100,
                "font.family": "DejaVu Sans",
            }
        ):
            repo = Path(__file__).resolve().parents[1]
            expected = repo / "tests" / "baseline_images" / "density_chart_default.png"
            assert expected.is_file(), f"missing baseline: {expected}"

            chart = DensityChart()
            chart.draw_chart(_density_payload())
            assert chart.ax.get_xlabel() == "Area"
            assert chart.ax.get_ylabel() == "Height"
            assert len(chart.figure.axes) == 2
            assert chart.figure.axes[1].get_ylabel() == "計數"
            actual = tmp_path / "actual.png"
            chart.figure.savefig(
                actual, dpi=100, format="png", facecolor=chart.figure.get_facecolor()
            )

            # Keep Ubuntu/CI strict against the canonical baseline. Windows has
            # larger constrained-layout and FreeType shifts even when chart
            # semantics match, so pair a wider raster tolerance with explicit
            # semantic assertions above.
            raster_tol = 45 if platform.system() == "Windows" else 12
            msg = compare_images(str(expected), str(actual), tol=raster_tol)
            assert msg is None, msg
