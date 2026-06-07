from __future__ import annotations

from pathlib import Path

from scripts.qt_audit import check_unsupported_qss_properties


def test_qt_audit_flags_unsupported_qss_properties(tmp_path: Path) -> None:
    qss_file = tmp_path / "app" / "ui" / "theme" / "dark_stylesheet.py"
    qss_file.parent.mkdir(parents=True)
    qss_file.write_text(
        '''
def get_stylesheet() -> str:
    return """
    QPushButton {
        outline: none;
        text-transform: uppercase;
    }
    """
''',
        encoding="utf-8",
    )

    issues = check_unsupported_qss_properties(tmp_path / "app")

    assert len(issues) == 1
    assert issues[0]["file"] == str(qss_file)
    assert issues[0]["lines"] == [(5, "outline"), (6, "text-transform")]
