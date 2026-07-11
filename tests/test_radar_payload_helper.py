from app.analytics.radar_payload_helper import (
    build_radar_payload,
    extract_statistics_from_engine_outputs,
    build_radar_from_measurement_stats,
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
