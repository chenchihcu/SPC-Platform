from app.services.report_service import _build_component_focus_html


def test_build_component_focus_html_tolerates_non_numeric_counts() -> None:
    html = _build_component_focus_html(
        {
            "Volume": {
                "metadata": {"is_valid": True},
                "data": {
                    "labels": ["R1", "R2"],
                    "counts": ["bad", 5],
                },
            },
            "Area": {
                "metadata": {"is_valid": True},
                "data": {
                    "labels": ["R1", "R2"],
                    "counts": [3, "nan-ish"],
                },
            },
        }
    )

    assert "component-focus" in html
    assert "R1" in html and "R2" in html
    assert "bad" not in html
    assert "nan-ish" not in html
