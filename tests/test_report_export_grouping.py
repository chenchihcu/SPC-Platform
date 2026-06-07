import pandas as pd

from app.analytics.chart_registry import CHART_ORDER
from app.data.session_store import SessionStore
from app.ui.pages.report_export_page import (
    REPORT_CHART_GROUP_ORDER,
    _has_valid_report_coordinates,
    _resolve_report_features,
    get_grouped_chart_ids,
    get_report_chart_group,
)


def test_grouping_covers_all_chart_order_ids_once() -> None:
    grouped = get_grouped_chart_ids(CHART_ORDER)
    ordered_grouped_ids = [
        chart_id
        for group in REPORT_CHART_GROUP_ORDER
        for chart_id in grouped[group]
    ]
    assert set(ordered_grouped_ids) == set(CHART_ORDER)
    assert len(ordered_grouped_ids) == len(CHART_ORDER)


def test_grouping_keeps_chart_order_inside_each_group() -> None:
    grouped = get_grouped_chart_ids(CHART_ORDER)
    for group in REPORT_CHART_GROUP_ORDER:
        group_ids = grouped[group]
        expected = [chart_id for chart_id in CHART_ORDER if get_report_chart_group(chart_id) == group]
        assert group_ids == expected


def test_unknown_chart_defaults_to_comparison_group() -> None:
    assert get_report_chart_group("unknown_chart") == "比較分析"


def test_resolve_report_features_expands_for_single_feature_with_parameters() -> None:
    selected = ["Volume"]
    payload = {
        "parameters": {
            "Volume": {},
            "Area": {},
            "Height": {},
        }
    }
    resolved = _resolve_report_features(selected, payload)
    assert resolved == ["Volume", "Area", "Height"]


def test_resolve_report_features_keeps_selected_when_no_parameters() -> None:
    selected = ["Volume", "Area"]
    resolved = _resolve_report_features(selected, {})
    assert resolved == selected


def test_has_valid_report_coordinates_requires_xy_columns() -> None:
    store = SessionStore()
    store.clear()
    store.meas_df = pd.DataFrame({"Volume": [100.0], "Area": [120.0]})
    assert _has_valid_report_coordinates(store) is False

    store.meas_df = pd.DataFrame({"X": [1.0], "Y": [2.0], "Volume": [100.0]})
    assert _has_valid_report_coordinates(store) is True
