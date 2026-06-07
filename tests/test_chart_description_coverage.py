from app.analytics.chart_registry import CHART_ORDER, get_chart_description_sections


def test_chart_order_all_have_required_description_sections() -> None:
    required = (
        "definition_text",
        "formula_text",
        "data_source_text",
        "smt_interpretation_text",
    )
    for chart_id in CHART_ORDER:
        sections = get_chart_description_sections(chart_id)
        for key in required:
            assert key in sections, f"{chart_id} missing key: {key}"
            assert str(sections[key]).strip(), f"{chart_id} empty section: {key}"
