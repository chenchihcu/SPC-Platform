from app.analytics.chart_registry import (
    CHART_UI_GROUPS_ORDER,
    build_chart_interpretation_sections,
    format_chart_description_compact,
    get_charts_by_root_cause_flow,
    get_charts_by_ui_group,
    get_feature_payload_slice,
    get_incompatible_reason,
    get_incompatible_short_reason,
    get_multi_feature_payload_slice,
    get_payload_slice,
    resolve_chart_payload,
)
from app.services.report_intent_presets import INTENT_PRESETS
from app.utils.constants import MSG_INCOMPATIBLE_AT_LEAST_ONE


def test_get_payload_slice_returns_incompatible_placeholder_when_missing_chart_data():
    payload = {
        "selected_features": ["Volume", "Area"],  # dual selection -> imr incompatible
    }
    result = get_payload_slice(payload, "imr")

    assert result.get("metadata", {}).get("is_valid") is False
    assert result.get("metadata", {}).get("incompatible") is True
    assert "特徵" in result.get("metadata", {}).get("error", "")


def test_histogram_slice_merges_dist_and_capability_limits():
    payload = {
        "dist": {
            "data": {"bins": [1, 2], "counts": [3, 4]},
            "analysis_context": {"target_col": "Volume"},
        },
        "cap": {
            "metadata": {"usl": 130.0, "lsl": 70.0},
            "analysis_context": {"target_col": "Volume"},
        },
    }
    result = get_payload_slice(payload, "histogram_spec")

    assert result["usl"] == 130.0
    assert result["lsl"] == 70.0
    assert result.get("analysis_context", {}).get("target_col") == "Volume"


def test_boxplot_slice_injects_parameters_for_feature_switching():
    payload = {
        "box": {"metadata": {"is_valid": True}, "data": {"labels": ["A"], "arrays": [[1.0]]}},
        "parameters": {"Volume": {"box": {"metadata": {"is_valid": True}}}},
    }
    result = get_payload_slice(payload, "boxplot")

    assert "parameters" in result
    assert "Volume" in result["parameters"]


def test_multi_feature_payload_slice_merges_feature_data_for_run_chart():
    payload = {
        "selected_features": ["Volume"],
        "parameters": {
            "Volume": {"run_chart": {"metadata": {"is_valid": True}, "data": {"values": [1.0]}}},
            "Area": {"run_chart": {"metadata": {"is_valid": True}, "data": {"values": [2.0]}}},
        },
    }
    result = get_multi_feature_payload_slice(payload, "run_chart", ["Volume", "Area"], normalized=True)
    assert result["_multi_feature"] is True
    assert result["_normalized"] is True
    assert set(result["_features"]) == {"Volume", "Area"}


def test_feature_slice_fallback_exposes_reason_metadata():
    payload = {"selected_features": ["Volume"], "run_chart": {"metadata": {"is_valid": True}}}
    result = get_feature_payload_slice(payload, "run_chart", "Area")
    meta = result.get("metadata", {})
    assert meta.get("fallback_used") is True
    assert meta.get("requested_feature") == "Area"


def test_resolve_chart_payload_supports_3f_parallel_from_parameters():
    payload = {
        "selected_features": ["Volume"],
        "parameters": {
            "Volume": {"run_chart": {"metadata": {"is_valid": True}, "data": {"values": [1.0]}}},
            "Area": {"run_chart": {"metadata": {"is_valid": True}, "data": {"values": [2.0]}}},
            "Height": {"run_chart": {"metadata": {"is_valid": True}, "data": {"values": [3.0]}}},
        },
    }
    result = resolve_chart_payload(payload, "run_chart_3f", features=["Volume", "Area", "Height"], normalized=True, context="report")
    assert result.get("_multi_feature") is True
    assert result.get("_normalized") is True
    assert set(result.get("_features", [])) == {"Volume", "Area", "Height"}


def test_dist_charts_require_at_least_one_feature_message():
    assert get_incompatible_reason("histogram_spec", []) == MSG_INCOMPATIBLE_AT_LEAST_ONE
    assert get_incompatible_short_reason("histogram_spec", []) == "至少 1 特徵"
    assert get_incompatible_reason("normality", []) == MSG_INCOMPATIBLE_AT_LEAST_ONE
    assert get_incompatible_short_reason("boxplot", []) == "至少 1 特徵"


def test_ui_group_marks_incompatible_for_wrong_feature_count():
    grouped = get_charts_by_ui_group(["Volume", "Area"])  # dual
    charts = [item for items in grouped.values() for item in items]
    imr = next(item for item in charts if item["id"] == "imr")
    scatter = next(item for item in charts if item["id"] == "scatter_spec")

    assert imr["available"] is False
    assert imr["incompatible_reason"]
    assert scatter["available"] is True


def test_compact_description_incompatible_has_explicit_hint():
    text = format_chart_description_compact(
        "imr",
        {"is_incompatible": True, "selected_features": ["Volume", "Area"]},
    )
    assert "不相容" in text
    assert "單選/雙選/三選" in text


def test_root_cause_flow_order_matches_five_decision_categories():
    flow = get_charts_by_root_cause_flow(["Volume"])
    stage_ids = [stage["stage_id"] for stage in flow]
    assert stage_ids == [
        "process_monitoring",
        "process_capability",
        "anomaly_root_cause",
        "variable_relationship",
        "comparison_analysis",
    ]


def test_ui_group_exposes_root_cause_metadata_for_ewma():
    grouped = get_charts_by_ui_group(["Volume"])
    charts = [item for items in grouped.values() for item in items]
    ewma = next(item for item in charts if item["id"] == "ewma")
    assert ewma["root_cause_stage"] == "process_monitoring"
    assert ewma["next_chart_ids"][:2] == ["drift_detection", "cusum"]


def test_ui_group_is_refactored_to_five_decision_categories():
    assert CHART_UI_GROUPS_ORDER == ["製程監控", "製程能力", "異常根源", "變數關係", "比較分析"]
    grouped = get_charts_by_ui_group(["Volume", "Area", "Height"])
    assert set(grouped.keys()) == set(CHART_UI_GROUPS_ORDER)


def test_intent_presets_match_five_category_packages():
    assert [preset["label"] for preset in INTENT_PRESETS] == CHART_UI_GROUPS_ORDER


def test_chart_interpretation_sections_include_formula_and_status_context():
    sections = build_chart_interpretation_sections(
        "imr",
        context={
            "selected_features": ["Volume", "Area"],
            "is_incompatible": True,
        },
        render_status={"status": "Incompatible", "reason": "目前為雙特徵，I-MR 需單特徵。"},
    )
    expected_titles = [
        "圖表用途",
        "計算函數/公式說明",
        "資料抓取/來源",
        "SMT判讀與下一步",
    ]
    for expected, actual in zip(expected_titles, [s["title"] for s in sections]):
        assert actual.endswith(expected)
    assert "公式" in sections[1]["title"]
    assert "不相容" in sections[2]["body"]
    assert "圖卡狀態：Incompatible" in sections[2]["body"]
