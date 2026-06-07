import numpy as np
import pandas as pd

from app.analytics.parallel_coord_engine import ParallelCoordEngine
from app.analytics.run_chart_engine import RunChartEngine
from tests.helpers.perf_timing import measure_wall_seconds


def test_run_chart_large_dataset_performance_baseline() -> None:
    n = 1_000_000
    data = pd.Series(np.linspace(0.0, 1.0, n))
    result, elapsed = measure_wall_seconds(lambda: RunChartEngine.compute_run_chart(data))
    assert result["metadata"]["is_valid"] is True
    assert result["statistics"]["n"] == n
    assert result["statistics"]["sampled_for_display"] is False
    # Conservative guardrail to catch pathological regressions.
    assert elapsed < 15.0


def test_parallel_coord_large_dataset_performance_baseline() -> None:
    n = 300_000
    df = pd.DataFrame(
        {
            "Volume": np.linspace(80.0, 120.0, n),
            "Area": np.linspace(75.0, 125.0, n),
            "Height": np.linspace(0.08, 0.12, n),
        }
    )
    result, elapsed = measure_wall_seconds(
        lambda: ParallelCoordEngine.compute_parallel_coord(df, cols=["Volume", "Area", "Height"], max_points=500)
    )
    assert result["metadata"]["is_valid"] is True
    assert result["statistics"]["sampled_for_display"] is False
    # Conservative guardrail to catch pathological regressions.
    assert elapsed < 15.0
