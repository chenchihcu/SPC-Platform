from app.services import report_formatters


def test_format_pptx_evidence_lines_formats_ratio_units() -> None:
    lines = report_formatters.format_pptx_evidence_lines(
        {"variance_ratio": 2.1, "ooc_ratio": 0.125, "cv": 0.2},
        limit=4,
    )
    assert "Variance Ratio: 2.10x" in lines
    assert "OOC Ratio: 12.5%" in lines
    assert "CV: 20.0%" in lines
