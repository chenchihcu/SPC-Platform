"""Tests for shared dashboard_layers formatting (UI / PPTX alignment)."""

from app.analytics.dashboard_layers_display import (
    _layer_dict,
    build_process_stat_report_sections,
    extract_dashboard_layers,
    fmt_dashboard_value,
    get_tone_and_status,
    oos_state_ui,
    pptx_alarm_health_lines,
    pptx_kpi_capability_lines,
    pptx_layer8_diagnosis_lines,
    yield_state_ui,
)


def test_extract_dashboard_layers_empty() -> None:
    assert extract_dashboard_layers(None) == {}
    assert extract_dashboard_layers({}) == {}
    assert extract_dashboard_layers({"process": {}}) == {}


def test_layer_dict_helper() -> None:
    assert _layer_dict({"a": {"x": 1}}, "a") == {"x": 1}
    assert _layer_dict({"a": None}, "a") == {}


def test_get_tone_and_status_alarm() -> None:
    tone, zh = get_tone_and_status({"ooc_rate_state": "Alarm"})
    assert tone == "critical"
    assert "嚴重" in zh


def test_pptx_alarm_health_lines_includes_ooc() -> None:
    layers = {
        "layer_1_alarm": {"ooc_rate": 0.01, "ooc_rate_state": "Warning", "anomaly_cluster_count": 3},
        "layer_3_info": {"driver_feature": "Height"},
        "layer_5_spec_analysis": {"oos_rate": 0.0008, "mean_shift_pct": 5.0},
        "layer_8_diagnosis": {"issue_type_display_zh": "局部"},
    }
    lines = pptx_alarm_health_lines(layers)
    text = "\n".join(lines)
    assert "OOC" in text
    assert "高度" in text or "Height" in text


def test_pptx_kpi_and_layer8() -> None:
    layers = {
        "layer_2_kpi": {"yield_pct": 99.0, "dpmo": 100.0, "sigma_level": 3.0},
        "layer_5_spec_analysis": {"cpk": 1.5},
        "layer_8_diagnosis": {
            "priority": "low",
            "issue_type_display_zh": "局部",
            "root_cause_zh": "群集",
            "recommended_action_zh": "檢查鋼網",
        },
    }
    assert "Cpk" in "\n".join(pptx_kpi_capability_lines(layers))
    l8 = "\n".join(pptx_layer8_diagnosis_lines(layers))
    assert "檢查鋼網" in l8


def test_fmt_dashboard_yield() -> None:
    assert "%" in fmt_dashboard_value(99.5, "yield_pct")


def test_process_stat_report_sections_keep_reading_order_and_severity() -> None:
    layers = {
        "layer_1_alarm": {"ooc_rate": 0.12, "ooc_rate_state": "Alarm"},
        "layer_2_kpi": {"yield_pct": 96.0, "dpmo": 5000.0},
        "layer_3_info": {"sample_size": 120, "range": 10.0, "driver_feature": "Height"},
        "layer_5_spec_analysis": {"cpk": 1.42, "cp": 1.9, "oos_rate": 0.002},
        "layer_8_diagnosis": {"priority": "medium", "issue_type_display_zh": "局部"},
    }
    sections = build_process_stat_report_sections(layers)

    assert [section["key"] for section in sections] == [
        "status",
        "capability",
        "stability",
        "diagnosis",
        "context",
    ]
    status_rows = {row["key"]: row for row in sections[0]["rows"]}
    capability_rows = {row["key"]: row for row in sections[1]["rows"]}
    stability_rows = {row["key"]: row for row in sections[2]["rows"]}

    assert status_rows["oos_rate"]["state"] == "bad"
    assert capability_rows["cpk"]["state"] == "warning"
    assert stability_rows["yield"]["state"] == "warning"
    assert status_rows["ooc_rate"]["source"] == "layer_1_alarm"
    assert "layer_5_spec_analysis" in capability_rows["cpk"]["source"]


def test_dashboard_severity_helpers_match_report_rules() -> None:
    assert oos_state_ui(0.0) == "good"
    assert oos_state_ui(0.0001) == "bad"
    assert yield_state_ui(99.0) == "good"
    assert yield_state_ui(96.0) == "warning"
    assert yield_state_ui(90.0) == "bad"
