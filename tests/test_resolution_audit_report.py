from pathlib import Path

from scripts.run_resolution_audit import generate_markdown_report


def _matrix() -> list[tuple[int, int, float, str]]:
    return [
        (1024, 768, 1.0, "1024x768_1.0x_Projector"),
        (1280, 720, 1.0, "1280x720_1.0x_Projector_Wide"),
    ]


def _run_results() -> list[dict[str, str]]:
    return [
        {"environment": "1024x768_1.0x_Projector", "status": "completed"},
        {"environment": "1280x720_1.0x_Projector_Wide", "status": "completed"},
    ]


def test_resolution_report_does_not_emit_high_projector_risk_without_findings(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"

    generate_markdown_report(
        report_path,
        records=[],
        matrix=_matrix(),
        timestamp="20260722_000000",
        run_results=_run_results(),
    )

    text = report_path.read_text(encoding="utf-8")
    assert "- **風險級別**：`HIGH`" not in text
    assert "未發現文字截斷、重疊或溢出" in text
    assert "完全無法看到或點擊 Start Analysis 按鈕" not in text


def test_resolution_report_marks_projector_overflow_as_high(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"

    generate_markdown_report(
        report_path,
        records=[
            {
                "env_name": "1024x768_1.0x_Projector",
                "type": "OVERFLOW",
                "page": "DataSetupPage",
                "widget_name": "start_button",
                "details": "bottom exceeds viewport",
            }
        ],
        matrix=_matrix(),
        timestamp="20260722_000000",
        run_results=_run_results(),
    )

    text = report_path.read_text(encoding="utf-8")
    assert "- **風險級別**：`HIGH`" in text
    assert "投影機情境存在已量測到的 Overflow" in text
