import pandas as pd

from app.analytics.chart_registry import CHART_ORDER
from app.data.session_store import SessionStore
from app.services.report_context import build_chart_evidence_coverage, build_pptx_report_context


def _fresh_store() -> SessionStore:
    store = SessionStore()
    store.clear()
    return store


def test_build_pptx_report_context_infers_filters_time_and_risk() -> None:
    store = _fresh_store()
    store.relation_meta = {"match_rate": 99.1}
    store.workorder_master = {"product_name": ""}
    filtered_df = pd.DataFrame(
        {
            "BoardNo": ["B1", "B1"],
            "Line": ["L1", "L1"],
            "Time": ["2026-03-01 08:00:00", "2026-03-01 09:00:00"],
            "Volume": [100.0, 101.0],
        }
    )

    context = build_pptx_report_context(
        store=store,
        filtered_df=filtered_df,
        summary_data={"process": {"verdict": "可接受"}},
        diagnostics=[{"severity": "warning"}],
        selected_features=["Volume"],
        batch="B1",
        refdes_filter="全部 (All)",
        part_type="全部 (All)",
        product="P100",
        time_start="2026-03-01 00:00:00",
        time_end="2026-03-02 00:00:00",
        line="L1",
    )

    assert context["filter_context"]["batch"] == "B1"
    assert context["risk_assessment"]["level"] == "MEDIUM"
    assert context["risk_assessment"]["warning_count"] == 1
    assert context["inferred_context"]["line_name"] == "L1"
    assert context["inferred_context"]["time_start"] == "2026-03-01 08:00:00"
    assert context["inferred_context"]["time_end"] == "2026-03-01 09:00:00"
    wc0 = context["workorder_context"]
    assert wc0["product_name"] == ""
    assert wc0["work_order_no"] == ""
    assert wc0["supplier_work_order_no"] == ""
    assert wc0["outsource_work_order_no"] == ""
    assert wc0["batch_no"] == ""
    assert wc0["batch_qty"] == ""
    assert wc0["product_part_no"] == ""
    assert wc0["supplier"] == ""
    assert wc0["line_name"] == ""
    assert wc0["production_date"] == ""


def test_build_pptx_report_context_includes_workorder_batch_fields() -> None:
    store = _fresh_store()
    store.workorder_master = {
        "product_name": "PN",
        "work_order_no": "OUT-WO-9",
        "supplier_work_order_no": "SUP-WO-7",
        "outsource_work_order_no": "OUT-WO-9",
        "product_part_no": "P-01",
        "supplier": "ACME",
        "batch_no": "OUT-WO-9",
        "batch_qty": "24",
        "line_name": "Line 3",
        "production_date": "26/04/09",
    }
    filtered_df = pd.DataFrame({"Volume": [100.0]})

    context = build_pptx_report_context(
        store=store,
        filtered_df=filtered_df,
        summary_data={"process": {"verdict": "可接受"}},
        diagnostics=[],
        selected_features=["Volume"],
        batch="全部 (All)",
        refdes_filter="全部 (All)",
        part_type="全部 (All)",
        product=None,
        time_start=None,
        time_end=None,
        line=None,
    )

    wc = context["workorder_context"]
    assert wc["product_name"] == "PN"
    assert wc["work_order_no"] == "OUT-WO-9"
    assert wc["supplier_work_order_no"] == "SUP-WO-7"
    assert wc["outsource_work_order_no"] == "OUT-WO-9"
    assert wc["product_part_no"] == "P-01"
    assert wc["supplier"] == "ACME"
    assert wc["batch_no"] == "OUT-WO-9"
    assert wc["batch_qty"] == "24"
    assert wc["line_name"] == "Line 3"
    assert wc["production_date"] == "26/04/09"


def test_build_pptx_report_context_includes_height_spec_stats() -> None:
    store = _fresh_store()
    store.workorder_master = {"product_name": ""}
    store.height_spec_by_refdes = {
        "R1": {"target": 0.15},
        "R2": {"target": 0.16},
        "R3": {"target": 0.15},
    }
    filtered_df = pd.DataFrame({"Volume": [100.0, 101.0, 99.0]})

    context = build_pptx_report_context(
        store=store,
        filtered_df=filtered_df,
        summary_data={"process": {"verdict": "可接受"}},
        diagnostics=[],
        selected_features=["Volume"],
        batch="全部 (All)",
        refdes_filter="全部 (All)",
        part_type="全部 (All)",
        product=None,
        time_start=None,
        time_end=None,
        line=None,
    )

    assert context["height_spec_stats"]["assigned_refdes"] == 3
    assert context["height_spec_stats"]["distinct_height_targets"] == 2


def test_build_pptx_report_context_marks_spatial_excluded_without_xy() -> None:
    store = _fresh_store()
    filtered_df = pd.DataFrame(
        {
            "BoardNo": ["B1", "B1", "B1"],
            "RefDes": ["R1", "R2", "R3"],
            "Volume": [100.0, 101.0, 99.5],
            "Area": [120.0, 121.0, 119.0],
            "Height": [0.15, 0.151, 0.149],
        }
    )

    context = build_pptx_report_context(
        store=store,
        filtered_df=filtered_df,
        summary_data={"process": {"verdict": "可接受"}},
        diagnostics=[],
        selected_features=["Volume", "Area", "Height"],
        batch="全部 (All)",
        refdes_filter="全部 (All)",
        part_type="全部 (All)",
        product=None,
        time_start=None,
        time_end=None,
        line=None,
    )

    data_scope = context["data_scope"]
    assert data_scope["sample_n"] == 3
    assert data_scope["has_coordinate_data"] is False
    assert data_scope["section_trust"]["spatial"] == "未納入：資料缺失"
    assert data_scope["excluded_evidence"] == [
        {
            "id": "spatial",
            "label": "座標值 / 空間映射 / 空間熱圖",
            "reason": "本批資料未提供有效 X/Y 座標欄位",
        }
    ]


def test_chart_evidence_coverage_tracks_three_feature_counts_and_missing_xy() -> None:
    selected_features = ["Volume", "Area", "Height"]
    coverage_with_xy = build_chart_evidence_coverage(
        selected_chart_ids=CHART_ORDER,
        selected_features=selected_features,
        available_features=selected_features,
        has_coordinate_data=True,
    )
    assert coverage_with_xy["summary"]["total"] == 33
    assert coverage_with_xy["summary"]["available"] == 22
    assert coverage_with_xy["summary"]["incompatible"] == 11
    assert coverage_with_xy["summary"]["excluded"] == 0

    coverage_without_xy = build_chart_evidence_coverage(
        selected_chart_ids=CHART_ORDER,
        selected_features=selected_features,
        available_features=selected_features,
        has_coordinate_data=False,
    )
    by_id = {item["chart_id"]: item for item in coverage_without_xy["items"]}
    assert coverage_without_xy["summary"]["available"] == 22
    assert coverage_without_xy["summary"]["incompatible"] == 10
    assert coverage_without_xy["summary"]["excluded"] == 1
    assert by_id["spatial_heatmap"]["status"] == "未納入"
    assert by_id["spatial_heatmap"]["reason"] == "缺座標資料"
