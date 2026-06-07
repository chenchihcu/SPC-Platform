import numpy as np
import pandas as pd

from app.analytics import spatial_engine as spatial_module
from app.analytics.spatial_engine import SpatialEngine


def _spatial_df(n: int) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    return pd.DataFrame(
        {
            "X": rng.uniform(0.0, 100.0, n),
            "Y": rng.uniform(0.0, 100.0, n),
            "RefDes": [f"R{i}" for i in range(n)],
            "Volume": rng.normal(100.0, 5.0, n),
        }
    )


def test_spatial_engine_grid_mode_exposes_sampling_metadata() -> None:
    df = _spatial_df(7000)
    original_threshold = spatial_module.SPATIAL_GRID_THRESHOLD
    try:
        spatial_module.SPATIAL_GRID_THRESHOLD = 100
        result = SpatialEngine.compute_heatmap(df, "Volume", mode=SpatialEngine.MODE_VALUE)
    finally:
        spatial_module.SPATIAL_GRID_THRESHOLD = original_threshold

    assert result["metadata"]["is_valid"] is True
    stats = result["statistics"]
    assert stats["n"] == 7000
    assert stats["displayed_n"] < stats["n"]
    assert stats["sampled_for_display"] is True
    assert stats["sampling_method"] == "grid_aggregation"
    assert np.isfinite(stats["max"])
    assert np.isfinite(stats["min"])
    assert all(np.isfinite(v) for v in result["data"]["values"])
    assert result["metadata"]["sampled_for_display"] is True


def test_spatial_engine_full_mode_reports_no_sampling() -> None:
    df = _spatial_df(200)
    result = SpatialEngine.compute_heatmap(df, "Volume", mode=SpatialEngine.MODE_VALUE)
    assert result["metadata"]["is_valid"] is True
    stats = result["statistics"]
    assert stats["n"] == 200
    assert stats["displayed_n"] == 200
    assert stats["sampled_for_display"] is False
    assert stats["sampling_method"] == "full_data"
    assert result["metadata"]["sampled_for_display"] is False
