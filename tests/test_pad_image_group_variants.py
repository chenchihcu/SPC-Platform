import pandas as pd

from app.viewmodels.chart_analysis_viewmodel import (
    _compute_boxplot_for_df,
    _pareto_with_parttype_fallback,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "RefDes": ["U1_1", "U1_2", "U2_1", "U2_2"],
            "PartType": ["U", "U", "U", "U"],
            "Pad": ["1", "1", "2", "2"],
            "ImageID": [1, 2, 1, 2],
            "BoardNo": ["B1", "B1", "B2", "B2"],
            "Volume": [80.0, 120.0, 75.0, 125.0],
        }
    )


def test_boxplot_precomputes_pad_and_image_variants() -> None:
    result = _compute_boxplot_for_df(_sample_df(), "Volume")

    assert set(result["_group_variants"]) == {"pad", "image"}
    assert result["_group_variants"]["pad"]["_group_col"] == "Pad"
    assert result["_group_variants"]["image"]["_group_col"] == "ImageID"


def test_pareto_precomputes_non_drilldown_pad_and_image_variants() -> None:
    result = _pareto_with_parttype_fallback(
        _sample_df(), "Volume", ucl=110.0, lcl=90.0, usl=130.0, lsl=70.0
    )

    assert set(result["_group_variants"]) == {"pad", "image"}
    assert result["_group_variants"]["pad"]["data"]["component_ids"] == []
    assert result["_group_variants"]["image"]["data"]["component_ids"] == []
