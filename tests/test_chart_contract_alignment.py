from app.analytics.chart_registry import CHART_CATALOG, CHART_ORDER
from app.ui.pages.data_management_page import _build_chart_ref_rows


def test_chart_reference_rows_follow_chart_order():
    rows = _build_chart_ref_rows()
    assert [str(row["id"]) for row in rows] == CHART_ORDER


def test_chart_reference_id_set_matches_chart_order_set():
    rows = _build_chart_ref_rows()
    ref_ids = [str(row["id"]) for row in rows]
    chart_order_ids = [str(chart_id) for chart_id in CHART_ORDER]

    assert len(ref_ids) == len(set(ref_ids)), "chart reference rows contain duplicate ids"
    assert len(chart_order_ids) == len(set(chart_order_ids)), "CHART_ORDER contains duplicate ids"
    assert set(ref_ids) == set(chart_order_ids), "chart reference id set must match CHART_ORDER"


def test_chart_reference_badges_cover_required_count():
    rows = _build_chart_ref_rows()
    row_by_id = {str(row["id"]): row for row in rows}
    for entry in CHART_CATALOG:
        chart_id = str(entry["id"])
        row = row_by_id.get(chart_id)
        assert row is not None, f"{chart_id} missing in chart reference rows"
        badges = list(row["badges"])
        required = int(entry["required_feature_count"])
        if required == 1:
            assert "①" in badges, f"{chart_id} should include ①"
        elif required == 2:
            assert "②" in badges, f"{chart_id} should include ②"
        elif required == 3:
            assert "③" in badges, f"{chart_id} should include ③"
