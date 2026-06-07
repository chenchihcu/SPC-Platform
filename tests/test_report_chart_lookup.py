from app.services import report_chart_lookup


def test_display_name_to_chart_id_handles_cn_en_aliases() -> None:
    assert report_chart_lookup.display_name_to_chart_id("CUSUM 圖") == "cusum"
    assert report_chart_lookup.display_name_to_chart_id("製程能力圖 (Capability)") == "histogram_spec"
    assert report_chart_lookup.display_name_to_chart_id("分布與能力") == "histogram_spec"
    assert report_chart_lookup.display_name_to_chart_id("空間熱圖 (Spatial Heatmap)") == "spatial_heatmap"


def test_normalize_pptx_observable_charts_deduplicates_aliases() -> None:
    titles = report_chart_lookup.normalize_pptx_observable_charts(
        ["製程能力圖 (Capability)", "直方圖 (Histogram)", "常態機率圖 (Normality)"]
    )
    assert titles == ["分布與能力", "常態分析"]
