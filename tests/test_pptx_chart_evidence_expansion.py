from app.services.pptx_report_builder import _render_chart_evidence_items


def test_report_gallery_expands_all_single_features_and_pairs() -> None:
    calls: list[tuple[str, tuple[str, ...], str]] = []

    def fake_render(chart_id, _payload, *, features, group_key, context):
        assert context == "report"
        calls.append((chart_id, tuple(features), group_key))
        return b"png"

    coverage = {chart_id: {"status": "待輸出"} for chart_id in ("histogram_spec", "scatter_spec")}
    items = _render_chart_evidence_items(
        selected_chart_ids=["histogram_spec", "scatter_spec"],
        analysis_payload={"selected_features": ["Volume", "Area", "Height"]},
        selected_features=["Volume", "Area", "Height"],
        available_features=["Volume", "Area", "Height"],
        coverage_by_id=coverage,
        render_chart_fn=fake_render,
    )

    assert len(items) == 6
    assert calls == [
        ("histogram_spec", ("Volume",), "default"),
        ("histogram_spec", ("Area",), "default"),
        ("histogram_spec", ("Height",), "default"),
        ("scatter_spec", ("Volume", "Area"), "default"),
        ("scatter_spec", ("Volume", "Height"), "default"),
        ("scatter_spec", ("Area", "Height"), "default"),
    ]
    assert coverage["histogram_spec"]["rendered_outputs"] == 3
    assert coverage["scatter_spec"]["rendered_outputs"] == 3


def test_report_gallery_expands_precomputed_pad_and_image_groups() -> None:
    calls: list[str] = []

    def fake_render(_chart_id, _payload, *, features, group_key, context):
        assert features == ["Volume"]
        assert context == "report"
        calls.append(group_key)
        return b"png"

    valid = {"metadata": {"is_valid": True}, "data": {"labels": ["x"], "arrays": [[1.0]]}}
    payload = {
        "selected_features": ["Volume"],
        "parameters": {
            "Volume": {
                "box": {
                    **valid,
                    "_group_variants": {"pad": dict(valid), "image": dict(valid)},
                }
            }
        },
    }
    items = _render_chart_evidence_items(
        selected_chart_ids=["boxplot"],
        analysis_payload=payload,
        selected_features=["Volume"],
        available_features=["Volume"],
        render_chart_fn=fake_render,
    )

    assert calls == ["default", "pad", "image"]
    assert [item["group_key"] for item in items] == calls
