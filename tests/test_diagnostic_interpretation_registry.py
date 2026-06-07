from app.analytics.diagnostic_interpretation_registry import (
    build_diagnostic_interpretation_sections,
    get_diagnostic_interpretation_registry,
)


def test_diagnostic_interpretation_registry_covers_layer_1_to_layer_7() -> None:
    registry = get_diagnostic_interpretation_registry()
    keys = [item["layer_key"] for item in registry]
    assert keys == [
        "layer_1_alarm",
        "layer_2_kpi",
        "layer_3_info",
        "layer_4_defect_structure",
        "layer_5_spec_analysis",
        "layer_6_product_context",
        "layer_7_engineering_info",
    ]
    for item in registry:
        assert item["purpose"].strip()
        assert item["how_to_read"].strip()
        assert item["threshold_meaning"].strip()
        assert item["suggested_action"].strip()


def test_diagnostic_interpretation_sections_keep_nodata_framework() -> None:
    sections = build_diagnostic_interpretation_sections({})
    assert len(sections) == 7
    for sec in sections:
        assert "用途：" in sec["body"]
        assert "如何解讀：" in sec["body"]
        assert "門檻含意：" in sec["body"]
        assert "建議動作：" in sec["body"]
        assert "NoData" in sec["body"]
