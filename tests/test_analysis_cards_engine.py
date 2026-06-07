from app.analytics.analysis_cards_engine import (
    compute_drift_detection,
    compute_ooc_analysis,
    compute_outlier_analysis,
    compute_shift_detection,
)


def test_ooc_analysis_reports_alarm_when_ratio_reaches_threshold() -> None:
    payload = {
        "spc": {
            "data": {"out_of_control_indices": [0, 1, 2]},
            "statistics": {"n": 20},
        }
    }
    result = compute_ooc_analysis(payload)
    assert result["metadata"]["is_valid"] is True
    assert result["data"]["severity"] == "Alarm"
    assert abs(float(result["statistics"]["ooc_ratio"]) - 0.15) < 1e-9


def test_shift_detection_reports_local_shift_for_small_nonzero_ratio() -> None:
    payload = {
        "cusum": {
            "statistics": {"n": 20, "ooc_count": 1},
            "data": {},
        }
    }
    result = compute_shift_detection(payload)
    assert result["metadata"]["is_valid"] is True
    assert result["data"]["shift_level"] == "Local Shift"


def test_drift_detection_returns_invalid_without_ewma_values() -> None:
    result = compute_drift_detection({"ewma": {"data": {}, "statistics": {}}})
    assert result["metadata"]["is_valid"] is False
    assert "缺少 EWMA 資料" in result["metadata"]["error"]
    # Bug B2 regression: contract requires data={} and statistics={} on failure.
    assert result["data"] == {}
    assert result["statistics"] == {}


def test_outlier_analysis_falls_back_to_spc_ooc_when_bivariate_missing() -> None:
    payload = {
        "spc": {
            "data": {"out_of_control_indices": [2, 4, 6]},
            "statistics": {"n": 20},
        },
        "bivariate_outlier": {"data": {}},
    }
    result = compute_outlier_analysis(payload)
    assert result["metadata"]["is_valid"] is True
    assert result["statistics"]["outlier_count"] == 3
    assert abs(float(result["statistics"]["outlier_ratio"]) - 0.15) < 1e-9
    assert result["data"]["level"] == "Alarm"
