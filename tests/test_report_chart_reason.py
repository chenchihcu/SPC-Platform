from app.services.report_chart_reason import get_no_chart_reason


def test_get_no_chart_reason_prefers_payload_error_for_string_payload_key() -> None:
    reason = get_no_chart_reason(
        "spatial_heatmap",
        {"spatial": {"metadata": {"error": "缺乏有效座標映射資料"}}},
        catalog_by_id_fn=lambda: {"spatial_heatmap": {"payload_key": "spatial"}},
    )
    assert reason == "缺乏有效座標映射資料"


def test_get_no_chart_reason_checks_multiple_payload_keys_in_order() -> None:
    reason = get_no_chart_reason(
        "multi",
        {
            "a": {"metadata": {}},
            "b": {"metadata": {"error": "第二組資料不足"}},
        },
        catalog_by_id_fn=lambda: {"multi": {"payload_key": ("a", "b")}},
    )
    assert reason == "第二組資料不足"


def test_get_no_chart_reason_falls_back_to_default_message() -> None:
    reason = get_no_chart_reason(
        "unknown_chart",
        {},
        catalog_by_id_fn=dict,
    )
    assert reason == "此條件下資料不足或格式不符，無法產出圖表"
