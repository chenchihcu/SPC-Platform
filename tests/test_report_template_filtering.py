from app.services.report_service import _filter_diagnostics_by_selected_charts


def test_filter_diagnostics_preserves_existing_missing_reason_when_export_excludes_chart() -> None:
    diagnostics = [
        {
            "chart_title": "空間熱圖 (Spatial Heatmap)",
            "chart_bytes": b"fake",
            "chart_missing_reason": "缺乏有效座標映射資料",
            "observable_charts": ["空間熱圖"],
        }
    ]
    filtered = _filter_diagnostics_by_selected_charts(diagnostics, ["imr"])
    assert len(filtered) == 1
    item = filtered[0]
    assert item["chart_bytes"] is None
    assert "缺乏有效座標映射資料" in item["chart_missing_reason"]
    assert "未納入本次匯出勾選的圖表" in item["chart_missing_reason"]


def test_filter_diagnostics_keeps_chart_when_selected() -> None:
    diagnostics = [
        {
            "chart_title": "空間熱圖 (Spatial Heatmap)",
            "chart_bytes": b"fake",
            "chart_missing_reason": "",
            "observable_charts": ["空間熱圖"],
        }
    ]
    filtered = _filter_diagnostics_by_selected_charts(diagnostics, ["spatial_heatmap"])
    assert filtered[0]["chart_bytes"] == b"fake"
    assert filtered[0]["chart_missing_reason"] == ""
