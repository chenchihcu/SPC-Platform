import pandas as pd

from app.analytics.radar_payload_helper import (
    build_radar_payload,
    extract_statistics_from_engine_outputs,
    build_radar_from_measurement_stats,
    build_radar_from_dataframe_groups,
)


class TestBuildRadarPayload:
    def test_valid_payload(self):
        stats_map = {
            "Center": {"Volume": 85.0, "Area": 78.0, "Height": 92.0},
            "Left": {"Volume": 72.0, "Area": 80.0, "Height": 88.0},
        }
        result = build_radar_payload(stats_map)
        assert result["metadata"]["is_valid"] is True
        assert result["payload_key"] == "radar"
        assert result["data"]["categories"] == ["Area", "Height", "Volume"]
        assert len(result["data"]["series"]) == 2
        assert result["data"]["series"][0]["name"] == "Center"
        assert result["data"]["series"][0]["values"] == [78.0, 92.0, 85.0]

    def test_empty_input(self):
        result = build_radar_payload({})
        assert result["metadata"]["is_valid"] is False
        assert result["data"]["categories"] == []
        assert result["data"]["series"] == []

    def test_single_series_single_category(self):
        stats_map = {"Only": {"FeatureX": 42.0}}
        result = build_radar_payload(stats_map)
        assert result["metadata"]["is_valid"] is True
        assert result["data"]["categories"] == ["FeatureX"]
        assert result["data"]["series"][0]["values"] == [42.0]

    def test_missing_values(self):
        stats_map = {
            "A": {"X": 10.0, "Y": 20.0},
            "B": {"X": 15.0},  # Missing "Y"
        }
        result = build_radar_payload(stats_map)
        assert result["metadata"]["is_valid"] is True
        assert result["data"]["categories"] == ["X", "Y"]
        assert result["data"]["series"][0]["values"] == [10.0, 20.0]
        assert result["data"]["series"][1]["values"] == [15.0, 0.0]


class TestExtractStatistics:
    def test_valid_extraction(self):
        outputs = {
            "Pos1": {
                "statistics": {"mean": 12.5, "std": 1.2},
                "metadata": {"is_valid": True},
            },
            "Pos2": {
                "statistics": {"mean": 10.3, "std": 0.8},
                "metadata": {"is_valid": True},
            },
        }
        result = extract_statistics_from_engine_outputs(outputs, stat_key="mean")
        assert result == {"Pos1": {"mean": 12.5}, "Pos2": {"mean": 10.3}}

    def test_invalid_outputs_skipped(self):
        outputs = {
            "Good": {
                "statistics": {"mean": 5.0},
                "metadata": {"is_valid": True},
            },
            "Bad": {
                "statistics": {"mean": 0.0},
                "metadata": {"is_valid": False},
            },
        }
        result = extract_statistics_from_engine_outputs(outputs)
        assert "Bad" not in result


class TestBuildRadarFromMeasurementStats:
    def test_convenience_wrapper(self):
        data = {
            "Center": {"Volume": 85.0, "Area": 78.0},
            "Edge": {"Volume": 70.0, "Area": 72.0},
        }
        result = build_radar_from_measurement_stats(data)
        assert result["metadata"]["is_valid"] is True
        assert len(result["data"]["series"]) == 2
        assert result["data"]["series"][0]["name"] == "Center"


class TestBuildRadarFromDataframeGroups:
    def test_groups_by_refdes_mean_by_default(self):
        df = pd.DataFrame({
            "RefDes": ["R1", "R1", "C1", "C1"],
            "Volume": [80.0, 90.0, 60.0, 70.0],
            "Area": [10.0, 20.0, 30.0, 40.0],
            "Height": [1.0, 2.0, 3.0, 4.0],
        })
        result = build_radar_from_dataframe_groups(df, ["Volume", "Area", "Height"])

        assert result["metadata"]["is_valid"] is True
        series_by_name = {s["name"]: s["values"] for s in result["data"]["series"]}
        assert set(series_by_name) == {"R1", "C1"}
        assert result["data"]["categories"] == ["Area", "Height", "Volume"]
        # R1 group mean: Volume=85.0, Area=15.0, Height=1.5
        r1_values = dict(zip(result["data"]["categories"], series_by_name["R1"]))
        assert r1_values == {"Area": 15.0, "Height": 1.5, "Volume": 85.0}

    def test_supports_custom_group_col_candidates_with_fallback(self):
        df = pd.DataFrame({
            "PartType": ["A", "A", "B"],
            "Volume": [1.0, 2.0, 3.0],
        })
        result = build_radar_from_dataframe_groups(
            df, ["Volume"], group_col_candidates=("PartType", "RefDes"),
        )
        assert result["metadata"]["is_valid"] is True
        assert {s["name"] for s in result["data"]["series"]} == {"A", "B"}

    def test_no_cap_by_default_keeps_every_group(self):
        df = pd.DataFrame({
            "RefDes": ["A", "A", "A", "B", "B", "C"],
            "Volume": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        })
        result = build_radar_from_dataframe_groups(df, ["Volume"])
        names = {s["name"] for s in result["data"]["series"]}
        assert names == {"A", "B", "C"}

    def test_caps_series_to_max_series_by_sample_count_when_given(self):
        df = pd.DataFrame({
            "RefDes": ["A", "A", "A", "B", "B", "C"],
            "Volume": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        })
        result = build_radar_from_dataframe_groups(df, ["Volume"], max_series=2)
        names = {s["name"] for s in result["data"]["series"]}
        assert names == {"A", "B"}

    def test_invalid_when_no_group_column_present(self):
        df = pd.DataFrame({"Volume": [1.0, 2.0], "Area": [3.0, 4.0]})
        result = build_radar_from_dataframe_groups(df, ["Volume", "Area"])
        assert result["metadata"]["is_valid"] is False

    def test_invalid_on_empty_dataframe(self):
        df = pd.DataFrame({"RefDes": [], "Volume": []})
        result = build_radar_from_dataframe_groups(df, ["Volume"])
        assert result["metadata"]["is_valid"] is False
