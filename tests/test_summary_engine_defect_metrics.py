import math

import pandas as pd

import app.analytics.summary_engine as summary_engine
from app.analytics.summary_engine import compute_summary


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "BoardNo": ["B1", "B1", "B2", "B2", "B3", "B3"],
            "Volume": [95.0, 101.0, 130.0, 99.0, 70.0, 102.0],
            "Area": [96.0, 100.0, 125.0, 98.0, 75.0, 103.0],
            "Height": [97.0, 100.0, 121.0, 97.0, 78.0, 101.0],
        }
    )


def _full_spec() -> dict:
    return {
        "volume": {"usl": "120", "lsl": "80", "target": "100"},
        "area": {"usl": "120", "lsl": "80", "target": "100"},
        "height": {"usl": "120", "lsl": "80", "target": "100"},
    }


def test_compute_summary_emits_feature_and_combined_defect_metrics():
    summary = compute_summary(_sample_df(), _full_spec())
    per_measure = summary["per_measure"]
    process = summary["process"]

    for col in ("Volume", "Area", "Height"):
        defect = per_measure[col]["defect"]
        assert defect["ppm_below_lsl"] is not None
        assert defect["ppm_above_usl"] is not None
        assert defect["ppm_total"] is not None
        assert defect["dpmo_feature"] is not None
        assert defect["zbench_st"] is not None
        assert defect["zbench_lt"] is not None
        assert defect["cpk_ci"] == "N/A"
        assert defect["cpk_ci_method"] == "N/A"
        assert math.isclose(
            defect["ppm_total"],
            defect["ppm_below_lsl"] + defect["ppm_above_usl"],
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
        assert math.isclose(
            defect["dpmo_feature"],
            defect["ppm_total"],
            rel_tol=1e-9,
            abs_tol=1e-9,
        )

    combined = process["defect_combined"]
    assert combined["dpmo_combined_event"] is not None
    assert combined["dpmo_combined_board"] is not None
    assert combined["board_n"] == 3
    assert combined["opportunity_per_board"] == 3
    assert combined["opportunity_count_feature"] == 6
    assert combined["opportunity_count_combined_event"] == 18
    assert combined["opportunity_count_combined_board"] == 3
    assert 0 <= combined["combined_defect_board_count"] <= combined["combined_defect_event_count"] <= combined["board_n"] * 3
    assert combined["dpmo_combined_event"] < combined["dpmo_combined_board"]


def test_combined_defect_metrics_match_row_loop_reference() -> None:
    df = _sample_df()
    spec = _full_spec()
    summary = compute_summary(df, spec)
    combined = summary["process"]["defect_combined"]

    cols = ["Volume", "Area", "Height"]
    event_count = 0
    board_count = 0
    for _, row in df[cols].iterrows():
        row_events = 0
        for col in cols:
            if row[col] < 80 or row[col] > 120:
                row_events += 1
        if row_events:
            event_count += row_events
            board_count += 1

    assert combined["combined_defect_event_count"] == event_count
    assert combined["combined_defect_board_count"] == board_count


def test_compute_summary_defect_metrics_none_when_spec_missing():
    spec_missing = {
        "volume": {"usl": "120", "lsl": "80", "target": "100"},
    }
    summary = compute_summary(_sample_df(), spec_missing)

    volume_defect = summary["per_measure"]["Volume"]["defect"]
    assert volume_defect["ppm_total"] is not None
    assert volume_defect["dpmo_feature"] is not None

    area_defect = summary["per_measure"]["Area"]["defect"]
    assert area_defect["ppm_total"] is None
    assert area_defect["dpmo_feature"] is None
    assert area_defect["zbench_st"] is None
    assert area_defect["zbench_lt"] is None
    assert area_defect["cpk_ci"] == "N/A"
    assert area_defect["cpk_ci_method"] == "N/A"


def test_compute_summary_uses_inf_safe_denominator_for_yield_ppm_and_n():
    df = pd.DataFrame(
        {
            "BoardNo": ["B1", "B1", "B2", "B2", "B3", "B3"],
            "Volume": [100.0, 130.0, float("inf"), 90.0, 70.0, float("-inf")],
            "Area": [95.0, 100.0, 98.0, 102.0, 97.0, 103.0],
            "Height": [96.0, 99.0, 101.0, 103.0, 98.0, 100.0],
        }
    )
    summary = compute_summary(df, _full_spec())
    volume = summary["per_measure"]["Volume"]
    defect = volume["defect"]

    # Valid values after inf filtering: [100, 130, 90, 70] => 2 defects / 4
    assert volume["n"] == 4
    assert math.isclose(volume["yield_pct"], 50.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(defect["ppm_total"], 500000.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(defect["dpmo_feature"], 500000.0, rel_tol=1e-9, abs_tol=1e-9)


def test_compute_summary_emits_cpk_ci_when_capability_is_valid():
    n = 12
    df = pd.DataFrame(
        {
            "BoardNo": [f"B{i}" for i in range(n)],
            "Volume": [100.0, 101.0, 99.0, 103.0, 97.0, 104.0, 96.0, 102.0, 98.0, 105.0, 95.0, 100.0],
            "Area": [100.0, 100.5, 99.5, 101.5, 98.5, 102.0, 97.5, 101.0, 99.0, 102.5, 98.0, 100.0],
            "Height": [100.0, 101.0, 99.0, 100.5, 98.5, 102.0, 97.5, 101.5, 99.5, 102.5, 98.0, 100.5],
        }
    )
    summary = compute_summary(df, _full_spec())
    defect = summary["per_measure"]["Volume"]["defect"]
    ci_text = defect["cpk_ci"]
    assert str(ci_text).startswith("[")
    assert str(ci_text).endswith("]")
    assert "Bissell" in str(defect["cpk_ci_method"])


def test_compute_summary_dashboard_layer_contracts_use_alarm_driver() -> None:
    summary = compute_summary(_sample_df(), _full_spec())
    process = summary["process"]
    layers = process["dashboard_layers"]
    per_feature_alarm = layers["per_feature_alarm"]

    ooc_candidates = [
        float(row["ooc_rate"])
        for row in per_feature_alarm.values()
        if row.get("ooc_rate") is not None
    ]
    expected_ooc = max(ooc_candidates) if ooc_candidates else None
    assert layers["layer_1_alarm"]["ooc_rate"] == expected_ooc

    cpk_below = sum(
        1
        for row in per_feature_alarm.values()
        if row.get("cpk") is not None and float(row["cpk"]) < 1.33
    )
    assert layers["layer_1_alarm"]["cpk_below_133_count"] == cpk_below

    driver_feature = layers["layer_3_info"]["driver_feature"]
    expected_driver = process["min_cpk_measure"]
    if not expected_driver:
        expected_driver = next((m for m in ("Volume", "Area", "Height") if m in summary["per_measure"]), None)
    assert driver_feature == expected_driver
    if driver_feature:
        assert layers["layer_3_info"]["sample_size"] == summary["per_measure"][driver_feature]["n"]


def test_compute_summary_dashboard_cluster_uses_max_contiguous_segments(monkeypatch) -> None:
    df = pd.DataFrame(
        {
            "BoardNo": ["B1", "B1", "B2", "B2", "B3", "B3"],
            "Volume": [100.0, 101.0, 102.0, 99.0, 98.0, 100.0],
            "Area": [100.0, 101.0, 102.0, 99.0, 98.0, 100.0],
        }
    )
    spec = {
        "volume": {"usl": "120", "lsl": "80", "target": "100"},
        "area": {"usl": "120", "lsl": "80", "target": "100"},
    }

    def _fake_spc(_series, target_col):
        ooc = [1, 2, 5] if target_col == "Volume" else [0, 4, 5]  # 2 clusters each
        return {
            "data": {"out_of_control_indices": ooc, "values": [1, 2, 3, 4, 5, 6]},
            "statistics": {"n": 6},
            "metadata": {"is_valid": True},
        }

    def _fake_cusum(_series, _target_col, target=None, usl=None, lsl=None):  # noqa: ARG001
        return {
            "data": {"values": [0.1, 0.2], "values_cm": [0.0, 0.1]},
            "statistics": {"h_sigma": 0.5},
            "metadata": {"is_valid": True},
        }

    monkeypatch.setattr(summary_engine.SPCEngine, "compute_imr", staticmethod(_fake_spc))
    monkeypatch.setattr(summary_engine.CUSUMEngine, "compute_cusum", staticmethod(_fake_cusum))

    summary = compute_summary(df, spec)
    layer1 = summary["process"]["dashboard_layers"]["layer_1_alarm"]
    assert layer1["anomaly_cluster_count"] == 2
