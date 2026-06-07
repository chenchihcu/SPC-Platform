import pandas as pd

from app.analytics.chart_registry import get_feature_payload_slice
from app.data.session_store import filter_analysis_df
from app.utils.dataframe_utils import detect_order_col, sorted_unique_values


def test_detect_order_col_prefers_time_like_columns_before_board_id():
    df = pd.DataFrame(
        {
            "BoardNo": ["Board_10", "Board_2"],
            "Timestamp": ["2026-03-20T10:00:00", "2026-03-20T10:01:00"],
            "Volume": [100, 101],
        }
    )
    assert detect_order_col(df) == "Timestamp"


def test_sorted_unique_values_uses_natural_order_for_board_ids():
    series = pd.Series(["Board_10", "Board_2", "Board_1", "Board_2"])
    assert sorted_unique_values(series) == ["Board_1", "Board_2", "Board_10"]


def test_filter_analysis_df_first_last_board_use_natural_order():
    df = pd.DataFrame(
        {
            "BoardNo": ["Board_10", "Board_2", "Board_1"],
            "RefDes": ["R1", "R1", "R1"],
            "PartType": ["P", "P", "P"],
            "Volume": [10.0, 20.0, 30.0],
        }
    )
    first_df = filter_analysis_df(df, "首件", "全部 (All)", "全部 (All)")
    last_df = filter_analysis_df(df, "末件", "全部 (All)", "全部 (All)")

    assert first_df["BoardNo"].iloc[0] == "Board_1"
    assert last_df["BoardNo"].iloc[0] == "Board_10"


def test_get_feature_payload_slice_for_histogram_merges_capability_fields():
    payload = {
        "selected_features": ["Volume"],
        "parameters": {
            "Volume": {
                "dist": {
                    "metadata": {"is_valid": True},
                    "statistics": {"mean": 100.0},
                    "analysis_context": {"target_col": "Volume"},
                },
                "cap": {
                    "metadata": {"usl": 130.0, "lsl": 70.0, "target": 100.0},
                    "statistics": {"cpk": 1.2, "ppk": 1.1},
                },
            }
        },
    }
    result = get_feature_payload_slice(payload, "histogram_spec", "Volume")

    assert result["usl"] == 130.0
    assert result["lsl"] == 70.0
    assert result["target"] == 100.0
    assert result["statistics"]["cpk"] == 1.2
    assert result["statistics"]["ppk"] == 1.1
